"""GitHub 发布检查与受控更新管理器。

“检查更新”只读取发布信息，不修改安装目录。自动安装必须由调用方在用户明确
确认后单独调用 :meth:`install_release`，并且发布必须同时提供精确命名的 ZIP
与独立 SHA256 文件。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
from urllib.parse import urlparse

import requests

from config.version_info import (
    GITHUB_REPO,
    RESOURCE_RELEASE_DATE,
    RESOURCE_VERSION,
)
from lib.core.logger import get_logger

_logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STATE_PATH = _PROJECT_ROOT / "resc" / "user" / "update_state.json"
_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AemeathDeskPet-Updater/2.0",
}
_ASSET_HEADERS = {
    "Accept": "application/octet-stream",
    "User-Agent": "AemeathDeskPet-Updater/2.0",
}
_PROTECTED_ROOTS = ("logs", "resc/user", "resc/models")
_PROTECTED_FILES = ("py.ini",)
_MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
_MAX_EXTRACTED_BYTES = 4 * 1024 * 1024 * 1024
_MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 30_000
_MAX_COMPRESSION_RATIO = 200
_WINDOWS_DEVICE_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_CHECKSUM_RE = re.compile(r"(?i)\b([0-9a-f]{64})\b")
_VERSION_TAG_RE = re.compile(
    r"(?i)^(?:lts|v)?"
    r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:[-._]?(?P<label>dev|a|alpha|b|beta|pre|preview|rc)"
    r"[-._]?(?P<number>\d*))?$"
)
_PRERELEASE_RANK = {
    "dev": 0,
    "a": 1,
    "alpha": 1,
    "b": 2,
    "beta": 2,
    "pre": 3,
    "preview": 3,
    "rc": 4,
}


class UpdateError(RuntimeError):
    """更新流程异常。"""


@dataclass(frozen=True)
class InstalledState:
    version: str
    installed_at: datetime


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    published_at: datetime
    asset_name: str
    download_url: str
    checksum_name: str
    checksum_url: str
    html_url: str = ""
    asset_size: int = 0


@dataclass(frozen=True)
class UpdateResult:
    updated: bool
    installed_state: InstalledState
    release_info: ReleaseInfo
    reason: str = ""


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    value = value.strip()
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(
                tzinfo=timezone.utc,
            )
        except ValueError:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (
        parsed.astimezone(timezone.utc)
        if parsed.tzinfo
        else parsed.replace(tzinfo=timezone.utc)
    )


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _version_key(value: str) -> tuple[int, int, int, int, int] | None:
    """Parse the repository's LTS/v-style tags without adding a dependency."""
    match = _VERSION_TAG_RE.fullmatch(str(value or "").strip())
    if match is None:
        return None
    label = match.group("label")
    prerelease_rank = 5 if label is None else _PRERELEASE_RANK[label.casefold()]
    prerelease_number = int(match.group("number") or 0)
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        prerelease_rank,
        prerelease_number,
    )


def _is_newer_release(
    installed: InstalledState,
    release: ReleaseInfo,
) -> bool:
    """Prefer version order; use dates only for legacy, unparseable tags."""
    installed_key = _version_key(installed.version)
    release_key = _version_key(release.tag)
    if installed_key is not None and release_key is not None:
        return release_key > installed_key
    return release.published_at > installed.installed_at


def _normalize_relative_path(rel_path: Path) -> str:
    if rel_path == Path("."):
        return ""
    return "/".join(part for part in rel_path.parts if part not in (".", ""))


def _is_protected_path(rel_path: Path) -> bool:
    rel = _normalize_relative_path(rel_path).casefold()
    if not rel:
        return False
    protected_files = {path.casefold() for path in _PROTECTED_FILES}
    if rel in protected_files:
        return True
    return any(
        rel == root.casefold() or rel.startswith(root.casefold() + "/")
        for root in _PROTECTED_ROOTS
    )


def expected_update_asset_name(tag: str, variant: str) -> str:
    clean_tag = str(tag or "").strip()
    if not clean_tag or "/" in clean_tag or "\\" in clean_tag:
        raise UpdateError("GitHub Release tag 无效，无法确定更新资产名")
    if variant == "green":
        return f"AemeathDeskPet-{clean_tag}-green.zip"
    if variant == "source":
        return f"AemeathDeskPet-{clean_tag}.zip"
    raise UpdateError(f"未知更新资产类型：{variant}")


def _asset_map(assets: object) -> dict[str, dict]:
    if not isinstance(assets, list):
        return {}
    result: dict[str, dict] = {}
    for entry in assets:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if name and name not in result:
            result[name] = entry
    return result


def select_release_assets(
    release_data: dict,
    *,
    variant: str,
) -> tuple[dict, dict]:
    tag = str(
        release_data.get("tag_name")
        or release_data.get("name")
        or ""
    ).strip()
    archive_name = expected_update_asset_name(tag, variant)
    assets = _asset_map(release_data.get("assets"))
    archive = assets.get(archive_name)
    if archive is None:
        raise UpdateError(
            f"发布缺少精确命名的更新包 {archive_name}；不会回退到源码快照或其他 ZIP"
        )
    checksum_names = (
        f"{archive_name}.sha256",
        f"{archive_name[:-4]}.sha256",
    )
    checksum = next((assets.get(name) for name in checksum_names if assets.get(name)), None)
    if checksum is None:
        raise UpdateError(
            f"发布缺少 {checksum_names[0]} 校验文件，已拒绝自动安装"
        )
    return archive, checksum


def _validate_https_download_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise UpdateError("更新资产下载地址不是有效的 HTTPS URL")
    return value


class UpdateManager:
    """检查 GitHub Release，并在明确授权时执行可回滚更新。"""

    def __init__(
        self,
        *,
        repo: str = GITHUB_REPO,
        state_path: Path | None = None,
        project_root: Path | None = None,
        asset_variant: str | None = None,
        info_callback: Callable[[str], None] | None = None,
    ):
        self._repo = repo
        self._project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else _PROJECT_ROOT
        )
        self._state_path = (
            Path(state_path)
            if state_path is not None
            else self._project_root / "resc" / "user" / "update_state.json"
        )
        self._asset_variant = asset_variant or (
            "green" if getattr(sys, "frozen", False) else "source"
        )
        self._info_callback = info_callback

    def check_for_update(self) -> UpdateResult:
        """只检查最新发布；不下载、不覆盖、不写状态。"""
        installed = self._load_installed_state()
        release = self._fetch_latest_release()
        available = _is_newer_release(installed, release)
        reason = "update_available" if available else "up_to_date"
        if available:
            self._info(
                f"检测到新版本 {release.tag}（{release.published_at.date()}）。"
                "当前仅完成检查，尚未下载或修改任何文件。"
            )
        else:
            self._info(
                f"当前已为最新版本 {installed.version}"
                f"（{installed.installed_at.date()}）。"
            )
        return UpdateResult(False, installed, release, reason=reason)

    def check_and_update(self) -> UpdateResult:
        """兼容旧调用名，但安全语义已改为只检查。"""
        return self.check_for_update()

    def install_release(self, release: ReleaseInfo) -> UpdateResult:
        """下载、校验、暂存并应用一个已由用户确认的发布。"""
        self._info(f"正在下载 {release.asset_name} 到临时目录...")
        with tempfile.TemporaryDirectory(prefix="aemeath-update-") as tmp_dir:
            temp_root = Path(tmp_dir)
            archive_path = temp_root / release.asset_name
            checksum_path = temp_root / release.checksum_name
            self._download_file(
                release.download_url,
                archive_path,
                expected_size=release.asset_size,
            )
            self._download_file(
                release.checksum_url,
                checksum_path,
                max_bytes=256 * 1024,
            )
            expected_sha256 = self._read_expected_sha256(
                checksum_path,
                release.asset_name,
            )
            actual_sha256 = self._sha256_file(archive_path)
            if actual_sha256.lower() != expected_sha256.lower():
                raise UpdateError(
                    "更新包 SHA256 不匹配，已停止安装且未修改现有文件"
                )
            self._info("SHA256 校验通过，正在安全解压到临时目录...")
            extract_root = temp_root / "extracted"
            self._safe_extract(archive_path, extract_root)
            content_root = self._resolve_content_root(extract_root)
            self._validate_content_root(content_root)
            self._info("暂存内容检查通过，正在备份并应用更新...")
            backup_root = self._apply_with_rollback(content_root, release)

        try:
            self._write_installed_state(release)
        except Exception as exc:
            rollback_errors = self._rollback_applied_update(backup_root)
            detail = (
                "；回滚也有失败：" + " | ".join(rollback_errors)
                if rollback_errors
                else "；已恢复更新前文件"
            )
            raise UpdateError(
                f"更新状态写入失败，安装未提交：{exc}{detail}"
            ) from exc
        new_state = InstalledState(release.tag, release.published_at)
        self._info(
            f"更新已应用；旧文件备份位于 {backup_root}。请重启程序完成加载。"
        )
        return UpdateResult(True, new_state, release, reason="updated")

    def _info(self, message: str) -> None:
        if self._info_callback:
            try:
                self._info_callback(message)
                return
            except Exception:
                _logger.debug("update info callback failed", exc_info=True)
        _logger.info("[Update] %s", message)

    def _load_installed_state(self) -> InstalledState:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return InstalledState(
                    str(data.get("version") or RESOURCE_VERSION),
                    _parse_datetime(data.get("installed_at")),
                )
            except Exception as exc:
                _logger.warning("failed to parse update state: %s", exc)
        return InstalledState(
            RESOURCE_VERSION,
            _parse_datetime(RESOURCE_RELEASE_DATE),
        )

    def _write_installed_state(self, release: ReleaseInfo) -> None:
        payload = {
            "version": release.tag,
            "installed_at": _isoformat(release.published_at),
            "asset_name": release.asset_name,
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._state_path.with_name(f".{self._state_path.name}.tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(temp_path, self._state_path)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    def _fetch_latest_release(self) -> ReleaseInfo:
        url = f"https://api.github.com/repos/{self._repo}/releases/latest"
        try:
            response = requests.get(
                url,
                timeout=(10, 20),
                headers=_API_HEADERS,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise UpdateError(f"无法访问 GitHub：{exc}") from exc
        except ValueError as exc:
            raise UpdateError("GitHub 返回格式异常") from exc
        if not isinstance(data, dict):
            raise UpdateError("GitHub Release 数据格式异常")

        tag = str(data.get("tag_name") or data.get("name") or "").strip()
        published = _parse_datetime(
            data.get("published_at") or data.get("created_at")
        )
        archive, checksum = select_release_assets(
            data,
            variant=self._asset_variant,
        )
        archive_url = _validate_https_download_url(
            archive.get("browser_download_url")
        )
        checksum_url = _validate_https_download_url(
            checksum.get("browser_download_url")
        )
        try:
            asset_size = int(archive.get("size") or 0)
        except (TypeError, ValueError):
            asset_size = 0
        if asset_size < 0 or asset_size > _MAX_ARCHIVE_BYTES:
            raise UpdateError("更新包声明大小超过安全限制")
        return ReleaseInfo(
            tag=tag,
            published_at=published,
            asset_name=str(archive.get("name") or "").strip(),
            download_url=archive_url,
            checksum_name=str(checksum.get("name") or "").strip(),
            checksum_url=checksum_url,
            html_url=str(data.get("html_url") or "").strip(),
            asset_size=asset_size,
        )

    def _download_file(
        self,
        url: str,
        destination: Path,
        *,
        expected_size: int = 0,
        max_bytes: int = _MAX_ARCHIVE_BYTES,
    ) -> None:
        _validate_https_download_url(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with requests.get(
                url,
                timeout=(10, 120),
                stream=True,
                headers=_ASSET_HEADERS,
            ) as response:
                response.raise_for_status()
                _validate_https_download_url(str(response.url))
                header_size = int(response.headers.get("Content-Length") or 0)
                if header_size > max_bytes:
                    raise UpdateError("下载内容超过安全大小限制")
                with destination.open("wb") as file_obj:
                    for chunk in response.iter_content(chunk_size=512 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            raise UpdateError("下载内容超过安全大小限制")
                        file_obj.write(chunk)
        except requests.RequestException as exc:
            raise UpdateError(f"下载更新资产失败：{exc}") from exc
        except (OSError, ValueError) as exc:
            raise UpdateError(f"保存更新资产失败：{exc}") from exc
        if expected_size and total != expected_size:
            raise UpdateError(
                f"更新包下载不完整：实际 {total} bytes，预期 {expected_size} bytes"
            )

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _read_expected_sha256(path: Path, asset_name: str) -> str:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise UpdateError(f"无法读取 SHA256 文件：{exc}") from exc
        match = _CHECKSUM_RE.search(text)
        if not match:
            raise UpdateError("SHA256 文件没有有效的 64 位摘要")
        mentioned_names = [
            token.strip("* ")
            for token in re.split(r"\s+", text.strip())
            if token.lower().endswith(".zip")
        ]
        if mentioned_names and asset_name not in mentioned_names:
            raise UpdateError("SHA256 文件指向的资产名与更新包不一致")
        return match.group(1).lower()

    @staticmethod
    def _safe_member_path(name: str) -> Path:
        posix = PurePosixPath(str(name).replace("\\", "/"))
        unsafe_part = False
        for part in posix.parts:
            stem = part.split(".", 1)[0].casefold()
            if (
                part in ("", ".", "..")
                or ":" in part
                or part != part.rstrip(" .")
                or any(ord(char) < 32 for char in part)
                or stem in _WINDOWS_DEVICE_NAMES
            ):
                unsafe_part = True
                break
        if (
            posix.is_absolute()
            or not posix.parts
            or unsafe_part
        ):
            raise UpdateError(f"更新包包含不安全路径：{name}")
        return Path(*posix.parts)

    def _safe_extract(self, archive_path: Path, destination: Path) -> None:
        try:
            archive = zipfile.ZipFile(archive_path, "r")
        except zipfile.BadZipFile as exc:
            raise UpdateError(f"更新包损坏：{exc}") from exc
        with archive:
            entries = archive.infolist()
            if len(entries) > _MAX_ARCHIVE_ENTRIES:
                raise UpdateError("更新包文件数量超过安全限制")
            total_size = 0
            seen_paths: set[str] = set()
            for info in entries:
                rel_path = self._safe_member_path(info.filename)
                path_key = rel_path.as_posix().casefold()
                if path_key in seen_paths:
                    raise UpdateError(
                        f"更新包包含重复或仅大小写不同的路径：{info.filename}"
                    )
                seen_paths.add(path_key)
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    raise UpdateError(f"更新包不允许符号链接：{info.filename}")
                if info.flag_bits & 0x1:
                    raise UpdateError(f"更新包不允许加密条目：{info.filename}")
                file_size = max(0, int(info.file_size))
                compressed_size = max(0, int(info.compress_size))
                if file_size > _MAX_SINGLE_FILE_BYTES:
                    raise UpdateError(
                        f"更新包单个文件解压后超过安全限制：{info.filename}"
                    )
                if file_size and (
                    compressed_size == 0
                    or file_size > compressed_size * _MAX_COMPRESSION_RATIO
                ):
                    raise UpdateError(
                        f"更新包条目压缩比异常：{info.filename}"
                    )
                total_size += file_size
                if total_size > _MAX_EXTRACTED_BYTES:
                    raise UpdateError("更新包解压后大小超过安全限制")
                target = destination / rel_path
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = 0
                try:
                    with archive.open(info, "r") as source, target.open("wb") as output:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            extracted += len(chunk)
                            if extracted > file_size:
                                raise UpdateError(
                                    f"更新包条目实际大小超过声明：{info.filename}"
                                )
                            output.write(chunk)
                except (NotImplementedError, RuntimeError, zipfile.BadZipFile) as exc:
                    raise UpdateError(
                        f"无法安全解压更新包条目 {info.filename}：{exc}"
                    ) from exc
                if extracted != file_size:
                    raise UpdateError(
                        f"更新包条目大小不一致：{info.filename}"
                    )

    def _project_destination(self, rel_path: Path) -> Path:
        relative = self._safe_member_path(rel_path.as_posix())
        project_root = self._project_root.resolve()
        current = project_root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise UpdateError(
                    f"更新目标路径包含符号链接，已拒绝覆盖：{relative.as_posix()}"
                )
        try:
            current.resolve(strict=False).relative_to(project_root)
        except ValueError as exc:
            raise UpdateError(
                f"更新目标超出项目目录：{relative.as_posix()}"
            ) from exc
        return current

    @staticmethod
    def _resolve_content_root(extracted_root: Path) -> Path:
        if (extracted_root / "app_brand.py").is_file():
            return extracted_root
        children = [
            child
            for child in extracted_root.iterdir()
            if child.name != "__MACOSX"
        ]
        if len(children) == 1 and children[0].is_dir():
            return children[0]
        return extracted_root

    @staticmethod
    def _validate_content_root(content_root: Path) -> None:
        required = (
            Path("app_brand.py"),
            Path("config/version_info.py"),
            Path("lib/core/qt_desktop_pet.py"),
        )
        missing = [path.as_posix() for path in required if not (content_root / path).is_file()]
        if missing:
            raise UpdateError(
                "更新包结构无效，缺少：" + ", ".join(missing)
            )

    @staticmethod
    def _iter_content_files(content_root: Path) -> Iterable[tuple[Path, Path]]:
        for source in sorted(content_root.rglob("*")):
            if not source.is_file() or source.is_symlink():
                continue
            relative = source.relative_to(content_root)
            if _is_protected_path(relative):
                continue
            yield relative, source

    def _restore_paths(
        self,
        *,
        created: Iterable[Path],
        replaced: Iterable[Path],
        backup_files: Path,
    ) -> list[str]:
        rollback_errors: list[str] = []
        for relative in reversed(list(created)):
            try:
                self._project_destination(relative).unlink()
            except FileNotFoundError:
                pass
            except (OSError, UpdateError) as rollback_exc:
                rollback_errors.append(f"{relative}: {rollback_exc}")
        for relative in reversed(list(replaced)):
            source = backup_files / relative
            temp_path: Path | None = None
            try:
                destination = self._project_destination(relative)
                temp_path = destination.with_name(
                    f".{destination.name}.aemeath-rollback.tmp"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, temp_path)
                os.replace(temp_path, destination)
            except (OSError, UpdateError) as rollback_exc:
                rollback_errors.append(f"{relative}: {rollback_exc}")
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink()
                    except FileNotFoundError:
                        pass
        return rollback_errors

    def _rollback_applied_update(self, backup_root: Path) -> list[str]:
        manifest_path = backup_root / "update-manifest.json"
        try:
            metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = metadata.get("files")
            if not isinstance(files, list):
                raise ValueError("files 不是列表")
            created: list[Path] = []
            replaced: list[Path] = []
            for entry in files:
                if not isinstance(entry, dict):
                    raise ValueError("files 包含无效记录")
                relative = self._safe_member_path(str(entry.get("path") or ""))
                if _is_protected_path(relative):
                    raise ValueError(f"回滚清单包含受保护路径：{relative}")
                if bool(entry.get("replaced")):
                    replaced.append(relative)
                else:
                    created.append(relative)
        except (OSError, ValueError, json.JSONDecodeError, UpdateError) as exc:
            return [f"无法读取回滚清单：{exc}"]

        rollback_errors = self._restore_paths(
            created=created,
            replaced=replaced,
            backup_files=backup_root / "files",
        )
        rollback_status = {
            "rolled_back_at": _isoformat(datetime.now(timezone.utc)),
            "complete": not rollback_errors,
            "errors": rollback_errors,
        }
        try:
            (backup_root / "rollback-status.json").write_text(
                json.dumps(rollback_status, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            rollback_errors.append(f"无法写入回滚状态：{exc}")
        return rollback_errors

    def _apply_with_rollback(
        self,
        content_root: Path,
        release: ReleaseInfo,
    ) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "_", release.tag)
        backup_root = (
            self._project_root
            / "resc"
            / "user"
            / "update_backups"
            / f"{safe_tag}-{timestamp}"
        )
        backup_files = backup_root / "files"
        created: list[Path] = []
        replaced: list[Path] = []
        manifest: list[dict[str, object]] = []
        backup_root.mkdir(parents=True, exist_ok=False)
        try:
            for relative, source in self._iter_content_files(content_root):
                destination = self._project_destination(relative)
                existed = destination.is_file()
                if existed:
                    backup_path = backup_files / relative
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup_path)
                    replaced.append(relative)
                else:
                    created.append(relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                temp_path = destination.with_name(
                    f".{destination.name}.aemeath-update.tmp"
                )
                try:
                    shutil.copy2(source, temp_path)
                    os.replace(temp_path, destination)
                finally:
                    try:
                        temp_path.unlink()
                    except FileNotFoundError:
                        pass
                manifest.append(
                    {
                        "path": relative.as_posix(),
                        "replaced": existed,
                        "sha256": self._sha256_file(destination),
                    }
                )
            metadata = {
                "version": release.tag,
                "asset_name": release.asset_name,
                "applied_at": _isoformat(datetime.now(timezone.utc)),
                "files": manifest,
            }
            (backup_root / "update-manifest.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            rollback_errors = self._restore_paths(
                created=created,
                replaced=replaced,
                backup_files=backup_files,
            )
            detail = (
                "；回滚也有失败：" + " | ".join(rollback_errors)
                if rollback_errors
                else "；已恢复原文件"
            )
            raise UpdateError(f"应用更新失败：{exc}{detail}") from exc

        return backup_root
