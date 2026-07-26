"""爱弥斯本机敏感配置存储。

敏感值使用 Windows DPAPI 加密，只能由当前 Windows 用户解密。文件位于
``C:\\AemeathDeskPet\\secrets\\ai_credentials.dpapi``，不写入源码目录。
"""

from __future__ import annotations

import ast
import ctypes
import json
import os
import re
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Any

from config.shared_storage_paths import (
    get_project_config_path,
    get_shared_config_path,
    get_shared_root_dir,
)

_FILE_HEADER = b"AEMEATH-DPAPI-1\n"
_ENTROPY = b"AemeathDeskPet:AISecrets:v1"
_ALLOWED_KEYS = ("api_key", "yuanbao_x_uskey")
_MAX_SECRET_FILE_BYTES = 1024 * 1024
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class SecureStorageError(RuntimeError):
    """凭据无法加密、解密、迁移或写入。"""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def get_ai_secret_path() -> Path:
    return get_shared_root_dir() / "secrets" / "ai_credentials.dpapi"


def _blob_from_bytes(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    blob = _DataBlob(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


def _dpapi_transform(data: bytes, *, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise SecureStorageError("安全凭据存储需要 Windows DPAPI")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL
    input_blob, input_buffer = _blob_from_bytes(data)
    entropy_blob, entropy_buffer = _blob_from_bytes(_ENTROPY)
    output_blob = _DataBlob()

    if protect:
        function = crypt32.CryptProtectData
        arguments = (
            ctypes.byref(input_blob),
            "AemeathDeskPet AI credentials",
            ctypes.byref(entropy_blob),
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output_blob),
        )
    else:
        function = crypt32.CryptUnprotectData
        arguments = (
            ctypes.byref(input_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output_blob),
        )
    if not function(*arguments):
        error_code = ctypes.get_last_error()
        raise SecureStorageError(f"Windows DPAPI 操作失败（错误码 {error_code}）")
    try:
        _ = (input_buffer, entropy_buffer)
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(
            ctypes.cast(output_blob.pbData, wintypes.HLOCAL)
        )


def _normalize_secrets(secrets: object) -> dict[str, str]:
    if not isinstance(secrets, dict):
        raise SecureStorageError("凭据数据格式无效")
    return {
        key: str(secrets.get(key) or "").strip()
        for key in _ALLOWED_KEYS
    }


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_bytes(data)
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def save_ai_secrets(
    secrets: dict[str, object],
    *,
    secret_path: Path | None = None,
) -> Path:
    path = Path(secret_path) if secret_path is not None else get_ai_secret_path()
    normalized = _normalize_secrets(secrets)
    payload = json.dumps(
        {
            "schema_version": 1,
            "secrets": normalized,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    encrypted = _dpapi_transform(payload, protect=True)
    _write_atomic(path, _FILE_HEADER + encrypted)
    return path


def load_ai_secrets(
    *,
    secret_path: Path | None = None,
) -> dict[str, str]:
    path = Path(secret_path) if secret_path is not None else get_ai_secret_path()
    if not path.exists():
        return {key: "" for key in _ALLOWED_KEYS}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SecureStorageError(f"无法读取安全凭据文件：{exc}") from exc
    if len(raw) > _MAX_SECRET_FILE_BYTES:
        raise SecureStorageError("安全凭据文件大小异常")
    if not raw.startswith(_FILE_HEADER):
        raise SecureStorageError("安全凭据文件格式无效")
    decrypted = _dpapi_transform(raw[len(_FILE_HEADER):], protect=False)
    try:
        record = json.loads(decrypted.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecureStorageError("安全凭据内容损坏") from exc
    if not isinstance(record, dict) or int(record.get("schema_version") or 0) != 1:
        raise SecureStorageError("安全凭据版本不受支持")
    return _normalize_secrets(record.get("secrets"))


def clear_ai_secrets(*, secret_path: Path | None = None) -> None:
    path = Path(secret_path) if secret_path is not None else get_ai_secret_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _extract_legacy_secrets(text: str) -> dict[str, str]:
    try:
        module = ast.parse(text)
    except SyntaxError:
        return {key: "" for key in _ALLOWED_KEYS}
    found = {key: "" for key in _ALLOWED_KEYS}
    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "API_KEY":
            try:
                found["api_key"] = str(ast.literal_eval(node.value) or "").strip()
            except Exception:
                pass
        if (
            isinstance(target, ast.Name)
            and target.id == "YUANBAO_FREE_API"
            and isinstance(node.value, ast.Dict)
        ):
            for key_node, value_node in zip(node.value.keys, node.value.values):
                try:
                    key = ast.literal_eval(key_node)
                except Exception:
                    continue
                if key != "x_uskey":
                    continue
                try:
                    found["yuanbao_x_uskey"] = str(
                        ast.literal_eval(value_node) or ""
                    ).strip()
                except Exception:
                    pass
    return found


def _sanitize_legacy_config_text(text: str) -> str:
    sanitized = re.sub(
        r"(?m)^(\s*API_KEY\s*=\s*).*(\s*(?:#.*)?)$",
        r"\1''\2",
        text,
        count=1,
    )
    dict_match = re.search(
        r"(?ms)^YUANBAO_FREE_API\s*=\s*\{.*?^\}",
        sanitized,
    )
    if not dict_match:
        return sanitized
    block = dict_match.group(0)
    clean_block = re.sub(
        r"(?m)^(\s*'x_uskey'\s*:\s*).*(,\s*(?:#.*)?)$",
        r"\1''\2",
        block,
        count=1,
    )
    return sanitized[:dict_match.start()] + clean_block + sanitized[dict_match.end():]


def migrate_legacy_config_secrets(
    *,
    project_config_path: Path | None = None,
    shared_config_path: Path | None = None,
    secret_path: Path | None = None,
) -> dict[str, str]:
    """迁移旧 Python 配置中的明文凭据，并在成功加密后清除原字段。"""
    project_path = (
        Path(project_config_path)
        if project_config_path is not None
        else get_project_config_path("ollama_config.py")
    )
    shared_path = (
        Path(shared_config_path)
        if shared_config_path is not None
        else get_shared_config_path("ollama_config.py")
    )
    secure_values = load_ai_secrets(secret_path=secret_path)
    sources: list[tuple[Path, str, dict[str, str]]] = []
    for path in (project_path, shared_path):
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            continue
        sources.append((path, text, _extract_legacy_secrets(text)))

    merged = dict(secure_values)
    has_legacy_secret = False
    for _, _, legacy in sources:
        for key in _ALLOWED_KEYS:
            value = legacy.get(key, "")
            if value:
                has_legacy_secret = True
                if not merged.get(key):
                    merged[key] = value
    if not has_legacy_secret:
        return merged

    save_ai_secrets(merged, secret_path=secret_path)
    for path, text, _ in sources:
        sanitized = _sanitize_legacy_config_text(text)
        if sanitized != text:
            try:
                _write_atomic(path, sanitized.encode("utf-8"))
            except OSError as exc:
                raise SecureStorageError(
                    f"凭据已加密，但无法清除旧明文配置 {path}: {exc}"
                ) from exc
    return merged
