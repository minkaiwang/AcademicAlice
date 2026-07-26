# 学术桌面助手 — 设计说明与开发进展

> **2026-07-26 文档分工**：当前状态、问题优先级、风险与验收门禁以 `PROJECT_MANAGEMENT.md` 为入口；本文件继续保存 **产品目标、技术设计、历史里程碑与 ADR**。工程修改流水见 `CHANGE_HISTORY.md`，未来阶段计划见 `ROADMAP.md`，本轮审计证据见 `AUDIT_REPORT_2026-07-26.md`。

本文件是 **产品目标 + 与当前仓库对齐的技术设计 + 历史里程碑与决策记录** 的事实来源。实施前以代码为准；若实现与设计分歧，应更新对应权威文档，或在本文件「决策记录」中写明例外原因。

**维护约定**：合并可交付功能或修复跨模块行为时，更新 `PROJECT_MANAGEMENT.md` 状态与 `CHANGE_HISTORY.md`；架构级取舍仍写入本文件「决策记录」。

---

## 1. 产品愿景与范围

### 1.1 愿景

在保留现有 **PyQt5 桌面宠物**（`lib/core/pet_window.py` 等）的前提下，将应用演进为 **学术桌面助手**：同一常驻进程内，以 **爱弥斯科研工作台**（浏览器内 `resc/workbench`）承载 **论文与项目进度** 等学术流，并保留音乐、语音、AI 聊天等原有能力作为可选模块。

### 1.2 首期范围（应做）

| 域 | 用户价值 | 备注 |
|----|----------|------|
| 论文 / 项目 / 任务 | 进度与记录留在本机工作台页面 | 详细交互以 `resc/workbench` 为准；非「闹钟」装饰对象 |
| （可选后续）Python 侧同步 | 本地 SQLite 与工作台双向同步 | 未实施前仅预留 `deskpet_academic.db` 路径 |

### 1.3 品牌与人设（爱弥斯）

- **产品与对外表述（暂行）**：集中写在 **`PRODUCT.md`**（定位、中文介绍稿、用户触点索引、上游关系口径）。本节的工程约束仍以代码为准。
- **对外显示名**：根目录 `app_brand.py` 中 `APP_DISPLAY_NAME`（默认 **爱弥斯**）、`APP_TAGLINE`（**学术桌面助手**）；`config/version_info.py` 再导出以便与版本号同读。托盘提示、单实例提示框、桌面快捷方式、启动失败弹窗、`install/install_deps.py` 横幅等均应 **`from app_brand import ...`**（或在已加载 `config` 后从 `version_info` 读），避免散落硬编码；**勿**在仅运行 `install/install_deps`、尚未安装 PyQt5 的环境依赖 `config` 包入口。
- **AI 系统人格**：`resc/persona.txt`（聊天 / Ollama 等 system prompt）；离线兜底回复规则见 `lib/script/chat/bot_reply.py`，须与上述人设一致。
- **与原作关系**：仓库仍可基于原「飞行雪绒」代码与资源；`LICENSE-ASSETS` 中对上游名称与素材的声明仍然适用。贡献名单等处保留「爱弥斯」等 **原作资源署名** 不等同于当前产品人设名。

### 1.4 非目标（暂不做或慎做）

- 不做多人协作实时同步（无服务端假设）。
- 不默认把论文全文或科研工作台整页内容发往外部 AI；若以后做「上下文摘要」，须 **显式同意 + 可关闭**。
- 不替代 Zotero / Notion；定位为 **轻量、本地、与桌宠同屏** 的助手。（产品对外名：**爱弥斯**。）

---

## 2. 现有工程地图（与改造相关的真实路径）

### 2.1 启动链

| 环节 | 路径 | 说明 |
|------|------|------|
| 入口 | `lib/core/qt_desktop_pet.py` | 将项目根加入 `sys.path` 后调用 `lib.script.main.main()` |
| 应用状态 | `lib/script/main.py` → `ApplicationState` | 创建 `QApplication`、宠物窗口、事件中心、聊天、托盘等；**第 108 行** `discover_all()`，**第 138 行** `init_all_managers(self._pet)` |
| 依赖安装 | `install/install_deps.py` | 结束时调用 `launch()` **会后台启动主程序**；`--no-launch` 仅安装；根目录 **安装依赖.bat** 转调 `install/安装依赖.bat` |

### 2.2 扩展点：管理器（桌宠「物体」与逻辑插件）

- **注册表**：`lib/core/plugin_registry.py`  
  - `BaseManager`：`MANAGER_ID`、`create(entity, **kwargs)`、`cleanup()`。  
  - `manager_registry.register(...)` 与装饰器 `@register_manager`。
- **自动发现规则**：`discover_managers()` **仅扫描** `lib/script/` 下 **目录名以 `obj-` 开头** 的子目录，且存在 `manager.py` 时执行 `importlib.import_module(f"lib.script.{文件夹名}.manager")`。  
  - 现有示例：`obj-闹钟/manager.py`（`ClockManager`）、`obj-雪豹`、`obj-沙发` 等。  
  - **新建学术模块建议**：新增 **`lib/script/obj-academic/`**（ASCII 目录名，避免部分工具对中文路径不友好），内含 `manager.py`，由现有 `discover_all()` **零改注册表即可加载**（除非需要改变扫描策略）。  
  - 若希望代码目录名为 `academic/` 而非 `obj-*`，则需改 `discover_managers()` 或在 `main.py` 中 **显式 import** 以完成注册（二选一，见决策记录）。

### 2.3 扩展点：事件总线

- **实现**：`lib/core/event/center.py`  
- **`EventType`**：已含 `APP_*`、`INPUT_HASH`、`TICK`、`INFORMATION` 等。  
- **建议**：  
  - **提醒类通知** 优先用 **应用内信号**（管理器持有 `QObject` + `pyqtSignal`）或 **专用窄事件**；若必须加 `EventType`，应集中文档并避免滥用（所有订阅者都会被调用）。  
  - **到点气泡**：可复用 `EventType.INFORMATION`（与 CmdCenter 行为一致）或托盘 `QSystemTrayIcon.showMessage`（`lib/core/tray_icon.py`）。

### 2.4 扩展点：`#` 命令与命令面板

- **分发**：`lib/core/cmd_center.py` 订阅 `INPUT_HASH`；未知命令会出失败气泡。  
- **注册元数据**：`lib/core/hash_cmd_registry.py` → `get_hash_cmd_registry().register(name, usage, description)`，供命令提示/补全。  
- **处理**：各管理器（如 `ClockManager`）在 `__init__` 中 **自行** `subscribe(EventType.INPUT_HASH, ...)` 并解析文本（参考 `lib/script/obj-闹钟/manager.py`）。  
- **学术助手**：已注册 `#工作台` / `#学术` 打开科研工作台；其余物体命令由各 `obj-*` 管理器注册。

### 2.5 托盘与主窗口 UI

- **托盘**：`lib/core/tray_icon.py` 的 `_create_menu()` 使用 `TrayContextMenu`（`lib/script/ui/tray_menu.py`）组装菜单项。  
- **学术入口**：托盘 **「爱弥斯科研工作台」** 由 `tray_icon` 调用 `workbench_host`（业务逻辑保持简短桥接）。

### 2.6 配置与用户数据路径（设计参考）

- **项目内配置**：`config/`，含 `shared_storage*.py`、`config.py` 等。  
- **跨安装共享目录**（现有约定）：`config/shared_storage_paths.py` 中
  `get_shared_root_dir()` → 显式 `AEMEATH_SHARED_ROOT` 优先；已存在的旧版
  **`{SystemDrive}\AemeathDeskPet`** 继续沿用；新安装默认
  **`%LOCALAPPDATA%\AemeathDeskPet`**，避免普通用户首次写系统盘根目录失败。
- **学术 SQLite 建议**：  
  - **首选**：`get_shared_root_dir() / "academic" / "deskpet_academic.db"`（与现有「同机多副本共享数据」策略一致），或  
  - **备选**：共享根下单独的 `academic/` 子目录，避免与普通配置混放。
  - **最终路径须在 M0 结束写死一条并在「决策记录」登记**，实现时封装为单一模块（如 `lib/script/obj-academic/store/paths.py`），禁止在 UI 层拼字符串。

---

## 3. 目标架构（分层）

```
┌─────────────────────────────────────────────────────────┐
│  UI：QDialog / QWidget（日历、列表、编辑表单）              │
│  入口：托盘菜单、可选 #命令、后续快捷键                      │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  AcademicManager（obj-academic/manager.py）               │
│  - 生命周期：create(pet_window) / cleanup()             │
│  - 注册 #命令、托盘回调、提醒 QTimer                       │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Service / Repository（同包内 academic_service.py 等）     │
│  - CRUD、查询「某日/某周事件」「逾期论文」                   │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  SQLite + 迁移（单文件；版本号存在 user_version）          │
└─────────────────────────────────────────────────────────┘
```

- **禁止**：在 `lib/script/main.py` 中写长段学术业务逻辑（仅保留必要的单行初始化或 `get_manager('academic')` 类桥接若采用）。

---

## 4. 数据模型（初版建议）

**单一来源**：用户侧的论文、项目、任务与时间相关安排 **一律在 `resc/workbench` 科研工作台**（浏览器）完成。仓库早期实现的 **PyQt 日程窗口 + SQLite `events` / `todos` / `categories` / `event_subtasks`** 已彻底移除（`db.py` `user_version = 4` 迁移时 `DROP`），**不再维护、不再恢复**。

若将来要在 Python 侧做 **备份 / 同步 / 导出**，可单独新增表结构，下表仅为草案，**与已删除的旧日程栈无关**。

### 4.1 `papers`（论文）

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| status | TEXT | 如 `idea` / `draft` / `submitted` / `published` |
| due_at | NULL | 计划完成或投稿截止 |
| tags | TEXT NULL | 逗号分隔或 JSON 数组 |
| link_or_path | TEXT NULL | 可选 |

### 4.2 `projects`（项目）

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| name | TEXT NOT NULL | |
| progress | INTEGER 0–100 | |
| phase | TEXT NULL | 开题/实验/写作等自定义 |
| notes | TEXT NULL | |

### 4.3 关联（可选，M2）

- `project_paper(project_id, paper_id)`  

用于跨论文与项目的跳转或统计（是否实现以工作台与 Python 同步策略为准）。

---

## 5. UI / 交互设计要点

- **学术能力**：托盘 **「爱弥斯科研工作台」** 或 `#工作台` / `#学术` → 本机 `resc/workbench` 静态页（`lib/script/workbench_host.py`）；与桌宠同进程，数据以工作台页面为准。  
- **与桌宠**：可选后续在 M3 做「进度摘要」气泡等，须 **显式不过度打扰**。

### 5.1 原作游戏向 UI 剥离（进行中，与爱弥斯一致）

基线来自桌宠原作；学术向产品逐步去掉 **《鸣潮》** 专属入口与配置。**视觉风格**（粉青像素、边框层次）保留。

| 区域 | 状态 | 主要代码位置 |
|------|------|----------------|
| **右键宠物 · 命令面板** | **已移除**「启动鸣潮」按钮装配；`ChatModeButton` 改锚在穿透按钮上方；`#-` 默认提示改为「快捷命令」 | `lib/core/pet_window_ui_factory.py`、`lib/script/ui/chat_mode_button.py`、`lib/script/ui/command_dialog.py`（`launch_wuwa_button` 恒为 `None`）、`lib/script/ui/command_hint_box.py`；`launch_wuwa_button.py` 仍保留于仓库、主流程不再实例化 |
| **设置 / 控制面板** | **已移除**「鸣潮设置」分节与 `launch_wuwa_path` 表单项与校验 | `lib/script/ui/ai_settings_panel.py`、`config/config_music.py`（键仍可读、注释标明弃用） |
| **音乐调度等非 UI** | **已调整**：搜索排序去掉鸣潮作者加权，仅保留歌名完全匹配优先 | `lib/script/tool_dispatcher/dispatcher.py` |

**实施顺序建议**：右键与鸣潮专页已收敛 → 后续可将 `#` 行与学术功能联动；每步合并后更新 **`PRODUCT.md` §6** 与本文 **§9 变更日志**。

---

## 6. 里程碑与任务分解

### UX-1 — UI 与原作游戏剥离（可与 M0 穿插）

- [x] 右键命令面板：移除「启动鸣潮」按钮装配；`ChatModeButton` 改为相对穿透按钮定位；`command_dialog` 仍兼容 `launch_wuwa_button=None`
- [x] 设置 / 控制面板：移除「鸣潮设置」分节与 `launch_wuwa_path` 配置 UI 及对应校验
- [x] 命令提示 `#-` 默认行改为「快捷命令」（`command_hint_box.py`）
- [x] 评估 `tool_dispatcher` 中鸣潮作者加权是否与学术产品目标冲突（已改为仅歌名完全匹配优先）

### M0 — 基线与骨架

- [x] 本设计文档落地于 `PROGRESS.md`
- [x] 记录原作游戏相关 UI 剥离范围（§5.1、UX-1、`PRODUCT.md` §6）
- [x] 选定 SQLite 最终路径：数据目录 `{共享根}/academic/`，库文件 `deskpet_academic.db`（`lib/script/obj-academic/store_paths.py`；见 **D2**）
- [x] 新增 `lib/script/obj-academic/` + `manager.py`（`AcademicManager` 空壳；`APP_INIT_READY` 时建目录并打日志）
- [x] 数据库模块：建库、`user_version` 迁移（`lib/script/obj-academic/db.py`；v4 起不创建旧日程表）
- [x] `install/install_deps.py`：支持 `--no-launch`

### M1 — 日历与事件（MVP）【已取消】

- 原 PyQt 日程窗（`academic_dialog` 等）与相关 SQLite 表已删除；用户统一使用 **爱弥斯科研工作台**（浏览器）。

### M2 — 论文与项目

- [x] 以 **`resc/workbench`** 单页承载（与托盘 / `#工作台` 入口一致）；Python 侧 `papers` / `projects` 表仍可作为后续本地同步预留
- [ ] （可选）`papers` / `projects` SQLite CRUD 与工作台双向同步

### M3 — 整合与体验

- [x] `#` 命令：`#工作台` / `#学术` → 打开科研工作台（`obj-academic/manager.py`、`workbench_host.py`）；其余物体命令由各 `obj-*` 管理器注册
- [ ] 导出/导入（JSON 或 CSV）— **属路线 B**，在 A 完成后再做
- [ ] 与 AI：仅本地拼接「今日摘要」字符串，默认不调外网 — **属路线 C**，在 B 完成后再做

### 学术后续路线（约定优先级：A → B → C）

与产品约定一致，实施顺序如下（**先把工作台做稳，再谈备份与联动**）。

| 阶段 | 做什么 | 主要落点 | 顺序 |
|------|--------|----------|------|
| **A** | 科研工作台功能走查、修 bug；交互与文案 | `resc/workbench/`（页面与脚本）、`lib/script/workbench_host.py` | **先做（当前优先）** |
| **B** | 备份 / 换机：导出与导入路径对用户说清楚；与应用入口或文档对齐 | 工作台既有导出（如 `research_workspace_backup_*.json` 等）、托盘或 `AA使用必读.html` / `resc/workbench/README.txt` | A 之后 |
| **C** | 桌宠与工作台联动：本地「今日摘要」等，**默认不外连**，须有隐私与开关设计 | 聊天管线、控制面板或设置、`resc/persona.txt` | B 之后 |

**与上表关系**：M3 中未勾选的两条分别对应 **B**（导出/导入）与 **C**（本地摘要）。M2 中「SQLite 与工作台双向同步」**不**列入 A→C 必经顺序；若单独要做，另起决策与排期。

**路线 A 进展（摘录）**：`research_workbench.html` 已通过本机
`/api/state` 把规范化状态写入共享根 `workbench/state.json`；服务端采用临时
文件 + `os.replace`、schema / 大小校验、备份轮换与损坏恢复，旧
`localStorage` 在首次成功迁移后退出主存储职责。剪贴板失败会引导导出 JSON；
Tailwind、Chart.js、Font Awesome 均已本地化，并完成桌面、390 px 移动端与
断网真实 Chromium 回归。

---

## 7. 风险与测试注意

- **Python 路径**：运行需 `PYTHONPATH` 含项目根（见 `启动程序.bat`）；单测或脚本同理。  
- **线程**：SQLite 写入集中在 **主线程** 或与 Qt 解耦的 **单写队列**，避免与 Qt UI 跨线程竞争。  
- **编码**：新建源码文件 **UTF-8**；目录名优先 ASCII（`obj-academic`）。  
- **与上游同步**：若需合并上游桌宠更新，学术逻辑应局限在 `obj-academic` 与少量 `tray_icon` 钩子，便于 diff。
- **Windows 绿色包**：`install/deskpet.spec` + 根目录 **`打包Windows.bat`**（转调 `install/打包Windows.bat`）。打包解释器 **必须已安装 PyQt5**（依赖见 `install/requirements.txt`；根目录 `requirements.txt` 为 `-r install/requirements.txt`）。产物为 `dist/AemeathDeskPet/`，分发时 **整夹** zip。冻结模式下资源根为 `sys._MEIPASS`，`main.py` 会 `chdir` 至该目录；日志仍在 **exe 所在目录** 的 `logs/`。

---

## 8. 决策记录（ADR 简版）

| # | 日期 | 决策 | 原因 |
|---|------|------|------|
| D1 | 2026-05-03 | 学术能力以 `lib/script/obj-academic/` 为主载体 | 与 `discover_managers()` 约定一致，免改 `plugin_registry` 即可加载 |
| D2 | 2026-05-03 | 数据层 SQLite 使用 `{共享根}/academic/deskpet_academic.db`（`store_paths.py`） | 与 `shared_storage_paths` 的 `AemeathDeskPet` 根一致，便于备份；表结构随 M1 落地 |
| D3 | 2026-05-03 | 产品显示名与人设统一为「爱弥斯」 | `app_brand.py` 集中配置（避免 `install_deps` 导入 `config` 时强依赖 PyQt5）；`resc/persona.txt` 与 `bot_reply.py` 对齐；单实例 Mutex 名暂不改以免双开旧版 |
| D4 | 2026-05-03 | 农历与法定假展示依赖 `lunar-python` + `chinesecalendar` | 统一经 `calendar_facade.py` 输出 `DayCalendarInfo`；`requirements.txt` 声明版本；无依赖或异常时降级为仅公历格不崩溃 |
| D5 | 2026-05-03 | SQLite `user_version = 3`：`categories`、`event_subtasks`，`events`/`todos` 扩展列 | `db.py` 迁移 + `categories_repo` / `subtasks_repo` / `events_repo` / `todos_repo` 与 UI 字段对齐 |
| D6 | 2026-05-03 | 移除 PyQt 日程栈与 `lunar-python` / `chinesecalendar`；`user_version = 4` 丢弃旧日程表 | 产品以 `resc/workbench` 为学术主界面；`AcademicManager` 仅保留工作台入口与库路径初始化 |
| D7 | 2026-07-26 | 工作台主状态迁移到共享根 `workbench/state.json`，浏览器缓存只作迁移 / 降级 | 随机本机端口不再分割主数据；原子写入、schema 校验与轮换备份支持损坏恢复 |
| D8 | 2026-07-26 | 新安装共享根改为 `%LOCALAPPDATA%\AemeathDeskPet`，已存在旧根继续沿用 | 普通用户不应因无权写系统盘根目录而首次启动失败，同时保持旧数据兼容 |
| D9 | 2026-07-26 | 更新采用 manifest + SHA256 + 明确确认 + 备份 / 回滚；发行 ZIP 由受控清单确定性生成 | 防止“检查更新”直接覆盖、路径穿越、错误附件和脏工作树污染 |
| D10 | 2026-07-26 | 默认依赖移除 `musicdl`，QQ / 酷狗使用直接接口并安全降级 | `musicdl 2.13.3` 强制依赖受 `GHSA-537c-gmf6-5ccf` 影响的 `cryptography<47`，且只是可选兜底 |

（后续行追加，勿删历史。）

---

## 9. 变更日志

### 2026-05-03

- 将 `PROGRESS.md` 扩展为 **结合仓库路径的设计说明**：启动链、插件发现规则、事件/`#` 命令/托盘挂接方式、数据表初稿、分层图、里程碑与 ADR。
- 修正先前草案中「独立 `lib/script/academic/` 包」表述：在未修改 `discover_managers` 的前提下，**默认应使用 `obj-academic` 目录** 才能被自动发现。
- **品牌与人设**：新增根目录 `app_brand.py`（零依赖）与 `version_info` 再导出；重写 `resc/persona.txt` 为爱弥斯；同步托盘/单实例/快捷方式/启动失败弹窗/`install_deps` 文案、`bot_reply.py` 兜底、`command_hint_box` 提示、`AA使用必读.html` 与 `doc/*.txt` 标题、README/CONTRIBUTING 说明。原作语音贡献条仍保留「爱弥斯」署名；单实例 Mutex 仍为 `FeiXingXueRongDesktopPet_SingleInstance`（与旧版互斥，避免同机双开）。
- **产品文档**：新增根目录 **`PRODUCT.md`**，集中记录爱弥斯的定位、中文介绍稿、用户触点与上游口径；`PROGRESS.md` §1.3 已交叉引用。
- **UI 规划**：在 `PROGRESS.md` §5.1、里程碑 **UX-1**、`PRODUCT.md` §6 记录「右键 / 设置 / 控制面板」中《鸣潮》相关入口（如「启动鸣潮」）的后续移除或替换方向，实施时同步更新文档勾选与变更日志。

### 2026-05-04

- **UX-1 实施（第一批）**：主 UI 不再创建 `LaunchWutheringWavesButton`；`ChatModeButton(layout_anchor=clickthrough)`；命令提示 `#-快捷命令`；控制面板去掉「鸣潮设置」与 `launch_wuwa_path` 编辑链；`config_music.launch_wuwa_path` 保留键、注释为弃用。详见 §5.1 与 **UX-1** 勾选。
- **UX-1（收尾）**：`tool_dispatcher._search_music` 去掉「鸣潮」作者名加权，仅保留歌名完全匹配优先。
- **托盘「关注作者」**：原作者授权二创后，链接集中到 `app_brand.AUTHOR_BILIBILI_SPACE_URL` → `https://space.bilibili.com/10845469?spm_id_from=333.788.0.0`；`PRODUCT.md` §1 表格已记录。
- **M0 进展**：新增 `lib/script/obj-academic/`（`store_paths.py`、`AcademicManager` 占位）；`install/install_deps.py` 支持 `--no-launch`；更新 ADR **D2** 为具体 SQLite 路径。

### 2026-05-04（续）

- **学术日志未出现原因**：`AcademicManager` 原订阅 `APP_INIT_READY`，该事件在 `init_all_managers()` **之前**发布，管理器尚未注册，故永不触发。已改为订阅 **`APP_MAIN`**（在管理器创建之后发布）。
- **SQLite**：新增 `obj-academic/db.py`，启动后写入 `{共享根}/academic/deskpet_academic.db` 并建立 `events` 表、`PRAGMA user_version = 1`。日志关键字：**`[Academic] 数据库就绪`**。

### 2026-05-03（日程增强）

- **Schema v3**：`categories`、`event_subtasks`；`events` / `todos` 增加 `category_id`、`repeat_rule`、`priority`、`color_hex`、`image_path`；`PRAGMA user_version = 3`（`db.py` 增量迁移）。
- **后端**：`calendar_facade.py`（农历 + 节气 + 法定假中文映射）、`categories_repo.py`、`subtasks_repo.py`；`events_repo` / `todos_repo` 支持分类筛选与更新；`store_paths.get_academic_attachments_dir()`。
- **前端**：`academic_dialog.py` 清单侧月历 + 分类列表 +「分类管理」；视图侧分类下拉；月历格展示农历与标签；周列头 / 日标题补充农历信息；`EventEditorDialog`（`academic_event_editor.py`）覆盖参考图中的分类、提醒、重复、优先级、颜色、描述、图片、子任务等字段并与 DB 一致。
- **依赖**：根目录 `requirements.txt` 增加 `lunar-python`、`chinesecalendar`（安装：`pip install -r requirements.txt`）。

---

*PR / 讨论可引用章节号，例如「按 §4.1 `papers` 草案」。*

### 2026-05-03（#命令 · 日程 → 工作台）

- **当前行为**：`#工作台` / `#学术` 与托盘 **「爱弥斯科研工作台」** 一致，打开本机 `resc/workbench/research_workbench.html`（`lib/script/workbench_host.py`）。`#日程` 命令与 PyQt 日程窗已随后续精简移除（见下 **「移除内置日程」**）。

### 2026-05-03（移除内置日程）

- 删除 `academic_dialog.py`、`academic_event_editor.py`、`academic_win_chrome.py` 与 `events_repo` / `todos_repo` / `categories_repo` / `subtasks_repo` / `calendar_facade.py`；`requirements.txt` 去掉 `lunar-python`、`chinesecalendar`。
- `db.py`：`user_version = 4` 迁移时 `DROP` 旧日程相关表；`AcademicManager` 不再轮询 `remind_at`。
- `hash_cmd_registry` 仅保留 **工作台**、**学术** 两个词条（`#日程` 不再注册）。
- 右键命令提示区含 `#工作台` 快捷说明；`hash_cmd_registry` 由 `AcademicManager` 注册。

### 2026-05-03（爱弥斯科研工作台 · 页面）

- **上游署名**：页面信息架构与交互参考 [AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system)（MIT，博士工作台原仓库）；原维护者在 readme 中对小红书来源与用户等的致谢及项目性质说明，以 **摘录** 形式写在根目录 `README.md`、`resc/workbench/README.txt` 与 `scripts/generate_doc_portal.py` 生成的 `AA使用必读.html` 中，**全文以原仓库为准**。
- **资源**：`resc/workbench/`（`research_workbench.html`、`tailwind.bundle.css`、`tailwind.workbench.config.js`、`tailwind.input.css`、`sync/ui.js`）。
- **品牌与主题**：页面标题与侧栏为「爱弥斯科研工作台」；侧栏 **「外观设置」** 内置 6 套粉彩（爱弥斯粉 / 粉紫 / 雾青 / 薄荷 / 鼠尾草 / 蜂蜜抹茶）+ **高饱和多巴胺**；支持 **我的配色** 自定义五档 HEX 的增删改（`…__wb_custom_themes_v1`），当前主题 `…__wb_theme_v2`（可为 `custom:<id>`）；粉彩走 `data-color-preset="pastel"` 与 `--wb-*` 变量。
- **构建**：本地 Tailwind 产物替代 CDN，消除生产环境 Tailwind CDN 告警；更新 HTML 后需按 `resc/workbench/README.txt` 重建 CSS。
- **浏览器兼容**：粉彩层使用 `color-mix()`，需较新 Chromium / Safari；过旧内核可改用「多巴胺」主题。
- **入口与文案**：静态页主文件名为 **`research_workbench.html`**（`workbench_host` 优先加载，旧 `phd_workbench.html` 可作回退）；页面内「博士论文」等已改为「学术论文」等表述；导出文件名 `research_daily_review_*.md`、`research_workspace_backup_*.json`。
- **聊天 / 聊天记录**：命令提示区「聊天-在命令行输入…」点击后仅 **`UI_HINT_PICK` + `focus_only`** 聚焦命令行；「聊天记录-…」发布 **`UI_OPEN_AEMEATH_CHAT_HISTORY`**，由 `CommandDialog` 打开 **`aemeath_chat_dialog.AemeathChatHistoryDialog`**（只读，数据来自 `StreamMemory` / 本地 memory）；对话与 **`INPUT_CHAT`** 仍在命令行 + 气泡。

### 2026-05-03（M1 · 日程提醒）【历史，已随「移除内置日程」下线】

- 曾实现 `remind_at` 轮询与 `academic_event_editor` 提醒字段；已删除，不再适用。

### 2026-05-04（文档 · 本分支维护者署名）

- **合并与文档维护者（对外展示）**：哔哩哔哩「靓点迷人」（`bili_2719061712`，空间 <https://space.bilibili.com/2719061712>）；小红书「皮鼓很痒」（小红书号 `533497202`）。已写入 `README.md`、`PRODUCT.md` §7、`doc/合并项目与使用入口.txt`、`scripts/generate_doc_portal.py`（生成 `AA使用必读.html` 的合并必读区块）。**托盘「关注作者」**仍以 `app_brand.py` → `AUTHOR_BILIBILI_SPACE_URL` 为准，与文档署名可分别配置。

### 2026-05-04（命令行占位 · 主桌宠置顶）

- **命令框**：占位符由 `cmd` 改为「`/ 命令 · # 快捷 · 或直接输入与爱弥斯聊天`」（`command_dialog.py`）。
- **主桌宠置顶**：`config_ui.UI['pet_stays_on_top']`（默认 `True`）；控制面板「界面与动画 → 界面」增加布尔项 **主桌宠与场景道具始终置顶在前**；`PetWindow` 每 30 帧与保存后配置对齐，关闭时去掉 `WindowStaysOnTopHint` 并从 `TopmostManager` **unregister**，避免 Win32 周期性强置顶；**鼠标穿透**开启时仍强制置顶以保证可操作恢复流程（`pet_window_setup.finalize_pet_window_startup` 仅在需要时 register）。

### 2026-05-04（学术路线：先 A 再 B 再 C）

- 约定实施顺序：**A** 爱弥斯科研工作台功能检视与修 bug（`resc/workbench`）→ **B** 备份 / 导出 / 换机路径做清楚（对齐工作台导出与托盘或文档入口）→ **C** 桌宠与工作台联动（本地「今日摘要」等，默认不外连）。详见 **§6「学术后续路线（约定优先级：A → B → C）」**；M3 未勾选项对应 B 与 C。

### 2026-05-04（路线 A · 工作台健壮性）

- **`research_workbench.html`**：`persistStateToLocal` 捕获存储配额异常并提示导出备份；`hydrateStateFromJson` 对桌面 JSON 内容 `JSON.parse` 失败时保留内存/缓存状态；`copyJson` 剪贴板失败时引导使用导出；`renderSettingsRangeStats` 对缺失 DOM 安全返回。详见 §6「路线 A 进展」。

### 2026-05-05（Windows 绿色包 · PyInstaller）

- 新增 **`install/deskpet.spec`**（onedir → `dist/AemeathDeskPet/`）、**`install/打包Windows.bat`**；根目录 **`打包Windows.bat`** 为快捷转调。
- **冻结资源路径**：`main.py` 在存在 `sys._MEIPASS` 时 `chdir` 至该目录；`config/shared_storage_paths.get_project_root()` 在 `frozen` 时返回 `_MEIPASS`，与 `workbench_host._bundle_root()` 一致。
- **README.md** §开发者、`PROGRESS.md` §7 补充分发说明。

### 2026-05-05（安装资源归集到 install/）

- **`install/`**：`install_deps.py`、`requirements.txt`、`deskpet.spec`、`安装依赖.bat`、`打包Windows.bat`、`README.txt`。
- 根目录 **`requirements.txt`** 仅 `-r install/requirements.txt`；**`安装依赖.bat`** / **`打包Windows.bat`** 转调 `install/` 内脚本。
- **`install/install_deps.py`** 中 `PROJECT_ROOT` 改为仓库根（`Path(__file__).resolve().parent.parent`）。
