"""主桌宠与场景道具共享的置顶策略（与控制面板 UI['pet_stays_on_top'] 及穿透态一致）。"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from config.config import UI
from lib.core.topmost_manager import get_topmost_manager

# 沙发 / 音响 / 雪豹等与 GameObject 相同的无边框工具窗基底（不含置顶位）
SCENE_WIDGET_BASE_FLAGS = (
    Qt.FramelessWindowHint | Qt.Tool | Qt.X11BypassWindowManagerHint
)


def read_pet_stays_on_top_setting() -> bool:
    """与控制面板「主桌宠始终置顶在前」同一配置项。"""
    return bool(UI.get("pet_stays_on_top", True))


def apply_scene_widget_stays_on_top(widget: QWidget, stays_on_top: bool) -> None:
    """
    重建窗口标志并同步 TopmostManager。
    调用前应先设置好 WA_TranslucentBackground 等属性；本函数会 hide → setWindowFlags → 按需 show。
    """
    was_visible = widget.isVisible()
    widget.hide()
    flags = SCENE_WIDGET_BASE_FLAGS
    if stays_on_top:
        flags |= Qt.WindowStaysOnTopHint
    widget.setWindowFlags(flags)
    if was_visible:
        widget.show()
    if stays_on_top:
        get_topmost_manager().register(widget)
    else:
        get_topmost_manager().unregister(widget)


def apply_tool_window_stays_on_top(widget: QWidget, stays_on_top: bool) -> None:
    """无边框 Tool 窗（如聊天记录）：基底为 Tool|Frameless，可选置顶。"""
    was_visible = widget.isVisible()
    widget.hide()
    flags = Qt.Tool | Qt.FramelessWindowHint
    if stays_on_top:
        flags |= Qt.WindowStaysOnTopHint
    widget.setWindowFlags(flags)
    if was_visible:
        widget.show()
    if stays_on_top:
        get_topmost_manager().register(widget)
    else:
        get_topmost_manager().unregister(widget)
