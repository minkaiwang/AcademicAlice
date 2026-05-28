"""爱弥斯「聊天记录」只读窗口：分页、可拖动、可清空；与 StreamMemory / 控制面板置顶策略一致。"""

from __future__ import annotations

import math
from typing import Optional

from PyQt5.QtCore import QPoint, Qt, QTimer
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.config_ui import COLORS, UI_THEME
from config.font_config import get_ui_font
from config.scale import scale_px
from lib.core.event.center import Event, EventType, get_event_center
from lib.core.logger import get_logger
from lib.core.scene_stays_on_top import apply_tool_window_stays_on_top, read_pet_stays_on_top_setting
from lib.core.topmost_manager import get_topmost_manager
from lib.script.chat.memory import get_stream_memory

_logger = get_logger(__name__)

_dialog_singleton: Optional["AemeathChatHistoryDialog"] = None

_PAGE_SIZE = 80


def _hex(c) -> str:
    return c.name()


def _format_entry(item: dict[str, str]) -> str:
    role = (item.get("role") or "").strip().lower()
    ts = (item.get("timestamp") or "").strip()
    topic = (item.get("topic") or "").strip()
    content = (item.get("content") or "").strip()
    if not content:
        return ""
    if role == "user":
        who = "你"
    elif role in ("you", "assistant"):
        who = "爱弥斯"
    else:
        who = role or "记录"
    head = ""
    if ts or topic:
        head = f"[{ts}]" + (f"[{topic}]" if topic else "") + " "
    return f"{head}{who}：{content}"


class _DragTitleLabel(QLabel):
    """拖动标题栏以移动无边框窗口。"""

    def __init__(self, host: QWidget, text: str) -> None:
        super().__init__(text)
        self._host = host
        self.setObjectName("aemeathHistoryTitle")
        self.setCursor(Qt.SizeAllCursor)
        self._drag_origin: Optional[QPoint] = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPos() - self._host.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            self._host.move(event.globalPos() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)


class AemeathChatHistoryDialog(QDialog):
    """只读聊天记录：分页浏览、标题栏拖动、清空本地 memory。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setModal(False)
        self.setFont(get_ui_font())
        self.setWindowTitle("聊天记录 · 爱弥斯")
        self._event_center = get_event_center()

        pink = _hex(COLORS["pink"])
        black = _hex(COLORS["black"])
        hi = _hex(UI_THEME["highlight"])
        shell = "#FFF5FA"
        field = "#FFFAFC"

        self.setStyleSheet(
            f"""
            AemeathChatHistoryDialog {{
                background: {shell};
                border: 2px solid {black};
            }}
            QLabel#aemeathHistoryTitle {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {pink}, stop:1 {hi});
                color: {black};
                font-weight: bold;
                padding: {scale_px(8, min_abs=6)}px;
                border-bottom: 2px solid {black};
            }}
            QTextEdit {{
                background: {field};
                color: {black};
                border: 2px solid {pink};
                padding: 6px;
                font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QPushButton {{
                background: {pink};
                color: {black};
                font-weight: bold;
                border: 2px solid {black};
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background: {hi}; }}
            QSpinBox {{
                background: {field};
                border: 2px solid {pink};
                padding: 2px 4px;
            }}
            """
        )

        apply_tool_window_stays_on_top(self, read_pet_stays_on_top_setting())

        root = QVBoxLayout(self)
        root.setContentsMargins(scale_px(6, min_abs=4), scale_px(6, min_abs=4), scale_px(6, min_abs=4), scale_px(6, min_abs=4))
        root.setSpacing(scale_px(8, min_abs=6))

        self._title = _DragTitleLabel(self, "聊天记录 · 爱弥斯（拖动标题栏移动窗口）")
        root.addWidget(self._title)

        hint = QLabel(
            "在下方命令行输入可与爱弥斯对话，回复以桌旁气泡为主；本窗口按页浏览本地 memory。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: #6b4a55; font-size: {scale_px(11, min_abs=9)}px; background: transparent;"
        )
        root.addWidget(hint)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(scale_px(200, min_abs=140))
        self._log.setPlaceholderText("暂无记录…")
        root.addWidget(self._log, 1)

        self._page = 1
        self._page_info = QLabel()
        self._page_info.setStyleSheet("color: #333; font-size: 12px;")
        root.addWidget(self._page_info)

        nav = QHBoxLayout()
        self._btn_first = QPushButton("首页")
        self._btn_first.clicked.connect(self._go_first_page)
        nav.addWidget(self._btn_first)
        self._btn_prev = QPushButton("上一页")
        self._btn_prev.clicked.connect(self._go_prev_page)
        nav.addWidget(self._btn_prev)
        self._btn_next = QPushButton("下一页")
        self._btn_next.clicked.connect(self._go_next_page)
        nav.addWidget(self._btn_next)
        self._btn_last = QPushButton("末页")
        self._btn_last.clicked.connect(self._go_last_page)
        nav.addWidget(self._btn_last)
        nav.addStretch(1)
        root.addLayout(nav)

        jump_row = QHBoxLayout()
        jump_row.addWidget(QLabel("跳至第"))
        self._spin_page = QSpinBox()
        self._spin_page.setMinimum(1)
        self._spin_page.setMaximum(1)
        self._spin_page.setFixedWidth(scale_px(72, min_abs=56))
        jump_row.addWidget(self._spin_page)
        jump_row.addWidget(QLabel("页"))
        btn_go = QPushButton("跳转")
        btn_go.clicked.connect(self._go_spin_page)
        jump_row.addWidget(btn_go)
        jump_row.addStretch(1)
        root.addLayout(jump_row)

        row = QHBoxLayout()
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._load_current_page)
        row.addWidget(btn_refresh)
        btn_clear = QPushButton("清除记录")
        btn_clear.clicked.connect(self._on_clear_history)
        row.addWidget(btn_clear)
        row.addStretch(1)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        row.addWidget(btn_close)
        root.addLayout(row)

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(120)
        self._reload_timer.timeout.connect(self._load_current_page)

        self.resize(scale_px(480, min_abs=380), scale_px(480, min_abs=340))
        self._live_subscribed = False
        self._top_flag_subscribed = False

    def _max_page(self, total: int) -> int:
        if total <= 0:
            return 1
        return max(1, int(math.ceil(total / float(_PAGE_SIZE))))

    def _load_current_page(self) -> None:
        if not self.isVisible():
            return
        try:
            sm = get_stream_memory()
            total, entries = sm.get_entries_page(self._page, _PAGE_SIZE)
        except Exception as e:
            self._log.setPlainText(f"（读取记忆失败：{e}）")
            return
        mp = self._max_page(total)
        if self._page > mp:
            self._page = mp
            total, entries = sm.get_entries_page(self._page, _PAGE_SIZE)
        lines = [_format_entry(e) for e in entries]
        lines = [ln for ln in lines if ln]
        self._log.setPlainText("\n\n".join(lines) if lines else "（本页无内容）")
        self._log.moveCursor(QTextCursor.Start)
        self._page_info.setText(
            f"第 {self._page} / {mp} 页 · 每页 {_PAGE_SIZE} 条 · 共 {total} 条记录"
        )
        self._spin_page.blockSignals(True)
        self._spin_page.setMaximum(mp)
        self._spin_page.setValue(self._page)
        self._spin_page.blockSignals(False)
        self._btn_prev.setEnabled(self._page > 1)
        self._btn_next.setEnabled(self._page < mp)
        self._btn_first.setEnabled(self._page > 1)
        self._btn_last.setEnabled(self._page < mp)

    def _go_first_page(self) -> None:
        self._page = 1
        self._load_current_page()

    def _go_last_page(self) -> None:
        total = get_stream_memory().count_parsed_entries()
        self._page = self._max_page(total)
        self._load_current_page()

    def _go_prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load_current_page()

    def _go_next_page(self) -> None:
        total = get_stream_memory().count_parsed_entries()
        mp = self._max_page(total)
        if self._page < mp:
            self._page += 1
            self._load_current_page()

    def _go_spin_page(self) -> None:
        total = get_stream_memory().count_parsed_entries()
        mp = self._max_page(total)
        self._page = max(1, min(int(self._spin_page.value()), mp))
        self._load_current_page()

    def _on_clear_history(self) -> None:
        r = QMessageBox.question(
            self,
            "清除聊天记录",
            "将清空本地已保存的与爱弥斯的对话记录（不可撤销）。确定吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        ok, err = get_stream_memory().clear_all_history()
        if not ok:
            QMessageBox.warning(self, "清除失败", err or "未知错误")
            return
        self._page = 1
        self._load_current_page()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._subscribe_live()
        self._subscribe_top_flags()
        self._load_current_page()

    def hideEvent(self, event) -> None:
        self._unsubscribe_live()
        self._unsubscribe_top_flags()
        super().hideEvent(event)

    def _subscribe_live(self) -> None:
        if self._live_subscribed:
            return
        try:
            self._event_center.subscribe(EventType.INPUT_CHAT, self._on_chat_event)
            self._event_center.subscribe(EventType.STREAM_FINAL, self._on_chat_event)
            self._live_subscribed = True
        except Exception as e:
            _logger.debug("聊天记录订阅事件失败: %s", e)

    def _unsubscribe_live(self) -> None:
        if not self._live_subscribed:
            return
        try:
            self._event_center.unsubscribe(EventType.INPUT_CHAT, self._on_chat_event)
            self._event_center.unsubscribe(EventType.STREAM_FINAL, self._on_chat_event)
        except Exception:
            pass
        self._live_subscribed = False

    def _subscribe_top_flags(self) -> None:
        if self._top_flag_subscribed:
            return
        try:
            self._event_center.subscribe(EventType.UI_SCENE_STAYS_ON_TOP_CHANGED, self._on_scene_top_changed)
            self._top_flag_subscribed = True
        except Exception as e:
            _logger.debug("聊天记录订阅置顶事件失败: %s", e)

    def _unsubscribe_top_flags(self) -> None:
        if not self._top_flag_subscribed:
            return
        try:
            self._event_center.unsubscribe(EventType.UI_SCENE_STAYS_ON_TOP_CHANGED, self._on_scene_top_changed)
        except Exception:
            pass
        self._top_flag_subscribed = False

    def _on_scene_top_changed(self, event: Event) -> None:
        on = bool(event.data.get("stays_on_top", True))
        apply_tool_window_stays_on_top(self, on)

    def _on_chat_event(self, _event: Event) -> None:
        if not self.isVisible():
            return
        self._reload_timer.stop()
        self._reload_timer.start()

    def closeEvent(self, event) -> None:
        global _dialog_singleton
        self._unsubscribe_live()
        self._unsubscribe_top_flags()
        get_topmost_manager().unregister(self)
        if _dialog_singleton is self:
            _dialog_singleton = None
        super().closeEvent(event)


def open_aemeath_chat_history_dialog(parent: Optional[QWidget] = None) -> None:
    """显示或前置聊天记录窗口。"""
    global _dialog_singleton
    if _dialog_singleton is not None:
        try:
            apply_tool_window_stays_on_top(_dialog_singleton, read_pet_stays_on_top_setting())
            _dialog_singleton.show()
            _dialog_singleton.raise_()
            _dialog_singleton.activateWindow()
            _dialog_singleton._load_current_page()
        except RuntimeError:
            _dialog_singleton = None
    if _dialog_singleton is None:
        _dialog_singleton = AemeathChatHistoryDialog(parent)
        _dialog_singleton.show()
    _dialog_singleton.raise_()
    _dialog_singleton.activateWindow()
