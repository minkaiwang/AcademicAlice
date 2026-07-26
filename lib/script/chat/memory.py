"""流式回复记忆模块

职责：
- 订阅 INPUT_CHAT / STREAM_FINAL 事件
- 将用户输入与模型回复写入用户共享数据目录
- 首次运行时从旧版 resc/user/memory.txt 迁移，但不再向仓库目录镜像
- 写入前移除 ###指令### 标记，并解析 ///主题///
- 按“每行独立”落盘，格式：[YYYY-MM-DD HH:MM:SS][主题][user:]内容 / [YYYY-MM-DD HH:MM:SS][主题][you:]内容
"""

import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.shared_storage import ensure_shared_config_ready, get_project_root, get_shared_config_path
from lib.core.event.center import Event, EventType, get_event_center
from lib.core.logger import get_logger

logger = get_logger(__name__)

_TOOL_MARKER_PATTERN = re.compile(r"###.*?###", re.S)
_TOPIC_MARKER_PATTERN = re.compile(r"^\s*///\s*([^/\r\n]{1,32}?)\s*///\s*", re.S)
_MEMORY_LINE_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]*)\]\[(?P<topic>[^\]]*)\]\[(?P<role>[^\]:]*):\](?P<content>.*)$"
)
_DEFAULT_TOPIC = "日常"


class StreamMemory:
    """记录用户输入与模型最终回复到本地 memory 文件。"""

    def __init__(self, memory_file: Path | None = None):
        self._ec = get_event_center()
        self._write_lock = threading.Lock()

        if memory_file is None:
            ensure_shared_config_ready()
            memory_file = get_shared_config_path("chat", "memory.txt")
        self._memory_file = Path(memory_file)
        self._legacy_memory_file = get_project_root() / "resc" / "user" / "memory.txt"
        self._memory_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._memory_file.exists() and self._legacy_memory_file.exists():
            try:
                self._memory_file.write_text(self._legacy_memory_file.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                pass

        self._ec.subscribe(EventType.INPUT_CHAT, self._on_input_chat)
        self._ec.subscribe(EventType.STREAM_FINAL, self._on_stream_final)
        logger.info("[StreamMemory] 已初始化: %s", self._memory_file)

    @staticmethod
    def _extract_topic_and_lines(text: str) -> tuple[str, list[str]]:
        if not text:
            return _DEFAULT_TOPIC, []

        normalized = (
            str(text)
            .replace("＃", "#")
            .replace("／", "/")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
        cleaned = _TOOL_MARKER_PATTERN.sub("", normalized)

        # 流式过程中若出现未闭合尾部 "###..."，直接截断尾部。
        tail_marker = cleaned.rfind("###")
        if tail_marker >= 0:
            cleaned = cleaned[:tail_marker]

        topic = _DEFAULT_TOPIC
        marker_match = _TOPIC_MARKER_PATTERN.match(cleaned)
        if marker_match:
            parsed = (marker_match.group(1) or "").strip()
            if parsed:
                topic = parsed
            cleaned = cleaned[marker_match.end():]
        topic = str(topic).replace("[", "").replace("]", "").strip() or _DEFAULT_TOPIC

        lines: list[str] = []
        for line in cleaned.split("\n"):
            compact = line.strip()
            if compact:
                lines.append(compact)
        return topic, lines

    def _append_lines(self, role: str, topic: str, lines: list[str]) -> None:
        if not lines:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = "".join(f"[{now}][{topic}][{role}:]{line}\n" for line in lines)

        try:
            with self._write_lock:
                self._memory_file.parent.mkdir(parents=True, exist_ok=True)
                with self._memory_file.open("a", encoding="utf-8") as f:
                    f.write(payload)
        except OSError as e:
            logger.error("[StreamMemory] 写入失败: %s", e)

    def _on_input_chat(self, event: Event) -> None:
        # 工具回忆回注不算用户主动输入，避免记忆回放再次写入形成噪声。
        if str(event.data.get("source", "")).strip() == "tool_recall":
            return
        text = event.data.get("text", "")
        topic, lines = self._extract_topic_and_lines(text)
        if not lines:
            return
        self._append_lines("user", topic, lines)

    def _on_stream_final(self, event: Event) -> None:
        text = event.data.get("text", "")
        topic, lines = self._extract_topic_and_lines(text)
        if not lines:
            return
        self._append_lines("you", topic, lines)

    def cleanup(self) -> None:
        self._ec.unsubscribe(EventType.INPUT_CHAT, self._on_input_chat)
        self._ec.unsubscribe(EventType.STREAM_FINAL, self._on_stream_final)
        logger.info("[StreamMemory] 已清理")

    def _read_memory_lines(self) -> list[str]:
        source = self._memory_file if self._memory_file.exists() else self._legacy_memory_file
        if not source.exists():
            return []
        try:
            return source.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as e:
            logger.debug("[StreamMemory] 读取记忆失败: %s", e)
            return []

    @staticmethod
    def _parse_memory_line(line: str) -> dict[str, str] | None:
        text = str(line or "").strip()
        if not text:
            return None
        match = _MEMORY_LINE_PATTERN.match(text)
        if not match:
            return {
                "timestamp": "",
                "topic": "",
                "role": "memory",
                "content": text,
            }
        return {
            "timestamp": str(match.group("timestamp") or "").strip(),
            "topic": str(match.group("topic") or "").strip(),
            "role": str(match.group("role") or "").strip().lower(),
            "content": str(match.group("content") or "").strip(),
        }

    def get_recent_entries(self, count: int = 12) -> list[dict[str, str]]:
        try:
            limit = int(count or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit <= 0:
            return []

        entries: list[dict[str, str]] = []
        for raw_line in reversed(self._read_memory_lines()):
            item = self._parse_memory_line(raw_line)
            if not item or not item.get("content"):
                continue
            entries.append(item)
            if len(entries) >= limit:
                break
        entries.reverse()
        return entries

    def count_parsed_entries(self) -> int:
        """有效记忆行条数（与分页一致）。"""
        n = 0
        for raw_line in self._read_memory_lines():
            item = self._parse_memory_line(raw_line)
            if item and item.get("content"):
                n += 1
        return n

    def get_entries_page(self, page: int, page_size: int) -> tuple[int, list[dict[str, str]]]:
        """
        按时间正序分页读取。
        page 从 1 起；page_size 限制在 1..500。
        返回 (总条数, 当前页条目列表)。
        """
        try:
            ps = int(page_size)
        except (TypeError, ValueError):
            ps = 50
        ps = max(1, min(500, ps))
        try:
            p = int(page)
        except (TypeError, ValueError):
            p = 1
        p = max(1, p)
        all_items: list[dict[str, str]] = []
        for raw_line in self._read_memory_lines():
            item = self._parse_memory_line(raw_line)
            if item and item.get("content"):
                all_items.append(item)
        total = len(all_items)
        start = (p - 1) * ps
        return total, all_items[start : start + ps]

    def clear_all_history(self) -> tuple[bool, str]:
        """清空主路径；若旧版文件仍存在，也同步清空以免旧版本读到历史。"""
        try:
            with self._write_lock:
                self._memory_file.parent.mkdir(parents=True, exist_ok=True)
                self._memory_file.write_text("", encoding="utf-8")
                if self._legacy_memory_file.exists():
                    self._legacy_memory_file.write_text("", encoding="utf-8")
            return True, ""
        except OSError as e:
            return False, str(e)


_instance: Optional[StreamMemory] = None


def get_stream_memory() -> StreamMemory:
    """获取全局 StreamMemory 实例（单例）。"""
    global _instance
    if _instance is None:
        _instance = StreamMemory()
    return _instance


def cleanup_stream_memory() -> None:
    """清理全局 StreamMemory 实例。"""
    global _instance
    if _instance is not None:
        _instance.cleanup()
        _instance = None
