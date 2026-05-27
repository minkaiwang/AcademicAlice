"""学术助手管理器：学术库路径初始化；`#工作台` / `#学术` 打开爱丽丝科研工作台。"""

from __future__ import annotations

from PyQt5.QtCore import QTimer

from lib.core.event.center import get_event_center, EventType, Event
from lib.core.hash_cmd_registry import get_hash_cmd_registry
from lib.core.logger import get_logger
from lib.core.plugin_registry import BaseManager, manager_registry

from . import db
from . import store_paths

_logger = get_logger(__name__)

_WORKBENCH_HASH_NAMES = ("工作台", "学术")


class AcademicManager(BaseManager):
    """学术相关能力的聚合入口（打开爱丽丝科研工作台网页）。"""

    MANAGER_ID = "academic"
    DISPLAY_NAME = "爱丽丝科研工作台"
    COMMAND_TRIGGER = "工作台"
    COMMAND_HELP = "在浏览器中打开爱丽丝科研工作台（本机页面）"

    def __init__(self, entity=None) -> None:
        self._entity = entity
        self._event_center = get_event_center()
        self._event_center.subscribe(EventType.INPUT_HASH, self._on_hash_command)
        self._event_center.subscribe(EventType.APP_MAIN, self._on_app_main)

    @classmethod
    def create(cls, entity=None, **kwargs) -> "AcademicManager":
        return cls(entity)

    def _on_hash_command(self, event: Event) -> None:
        """#工作台 / #学术：打开爱丽丝科研工作台（与托盘菜单一致）。"""
        text = str(event.data.get("text", "") or "").strip()
        if not text:
            return
        verb = text.split()[0]
        if verb not in _WORKBENCH_HASH_NAMES:
            return

        def _open() -> None:
            try:
                from lib.script.workbench_host import open_workbench_in_browser

                open_workbench_in_browser()
            except Exception as e:
                _logger.warning("[Academic] 打开爱丽丝科研工作台失败: %s", e)

        QTimer.singleShot(0, _open)

    def _on_app_main(self, _event: Event) -> None:
        db_path = store_paths.get_academic_db_path()
        try:
            db.init_database(db_path)
            _logger.info("[Academic] 数据库就绪 schema=%s path=%s", db.SCHEMA_VERSION, db_path)
        except OSError as e:
            _logger.warning("[Academic] 无法访问学术数据路径: %s", e)
        except Exception as e:
            _logger.warning("[Academic] 数据库初始化失败: %s", e)

    def cleanup(self) -> None:
        try:
            self._event_center.unsubscribe(EventType.INPUT_HASH, self._on_hash_command)
        except Exception:
            pass
        try:
            self._event_center.unsubscribe(EventType.APP_MAIN, self._on_app_main)
        except Exception:
            pass


manager_registry.register(AcademicManager.MANAGER_ID, AcademicManager)
