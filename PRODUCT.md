# 爱弥斯 — 产品与品牌说明（暂行）

> **状态**：暂行稿，随功能迭代更新。对外显示名以代码 **`app_brand.py`** 为准；本文件用于 **产品定位、中文介绍、品牌口径** 的集中记录，避免散落在聊天记录里。

---

## 1. 名称与标语

| 项 | 当前值 | 代码位置 |
|----|--------|----------|
| 产品显示名 | **爱弥斯**（英文 **Aemeath**） | `app_brand.py` → `APP_DISPLAY_NAME` / `APP_DISPLAY_NAME_EN` |
| 一句话标语 | **学术桌面助手** | `app_brand.py` → `APP_TAGLINE` |
| 版本号（与上游标签对齐时） | 见 `config/version_info.py` 的 `APP_VERSION` | 与 README / 发布流程一致即可 |
| 托盘「关注作者」B 站主页 | [space.bilibili.com/10845469](https://space.bilibili.com/10845469?spm_id_from=333.788.0.0) | `app_brand.py` → `AUTHOR_BILIBILI_SPACE_URL`（`lib/core/tray_icon.py` 引用） |

修改显示名或标语时：**先改 `app_brand.py`**，再核对本文表格与 `PROGRESS.md` §1.3 是否需同步。

**外链说明**：原作者已允许本分支自由创作；托盘「关注作者」现指向上述空间（维护者/企划展示用）。若日后更换链接，**只改 `AUTHOR_BILIBILI_SPACE_URL`** 并同步本表。

---

## 2. 产品定位（暂行）

**爱弥斯**是在 Windows 上常驻运行的 **桌面陪伴 + 学术场景助手**：在保留桌宠形态与音乐、语音、AI 聊天等能力的同时，通过 **爱弥斯科研工作台**（浏览器内本地页）管理 **论文、项目与任务进度**（具体能力以 `resc/workbench` 与 `PROGRESS.md` 为准）。

**适合谁**：需要桌边轻量提醒与陪伴、希望进度与任务尽量留在本机、不打算用本应用替代 Zotero / Notion 等专业工具的用户。

**不适合**：多人实时协作、强依赖云端同步的严肃项目管理（当前非目标）。

---

## 3. 中文介绍文案（可摘到 README / 商店页）

以下为 **可自行删减** 的段落，语气与 `resc/persona.txt` 人设一致时可共用。

**短版（一两句）**  
爱弥斯是你的 **学术桌面助手**：陪你盯进度、喘口气，科研工作台上的论文与项目也跟着稳住节奏。

**中版（一段）**  
爱弥斯运行在 Windows 桌面一侧，以桌宠形式常驻；科研工作台在浏览器里陪你整理论文、项目和日常任务，数据以本地为主，界面与操作保持简单。

**说明边界**  
她不会代替导师或审稿人做专业判断；涉及发表、伦理、医疗、法律等问题时，应咨询对应专业人士。

---

## 4. 用户可见触点（已与「爱弥斯」对齐的代码/资源）

以下为实现层索引，便于改文案时全局搜索遗漏。

| 触点 | 路径或说明 |
|------|------------|
| 显示名常量 | `app_brand.py` |
| 版本信息再导出 | `config/version_info.py` |
| 托盘悬停提示 | `lib/core/tray_icon.py` |
| 重复启动提示框 | `lib/script/app/single_instance.py` |
| 桌面快捷方式文件名与描述 | `lib/script/app/desktop_shortcut.py` |
| 依赖缺失 / 启动失败弹窗标题 | `lib/core/qt_desktop_pet.py` |
| 安装器横幅与阶段提示 | `install/install_deps.py` |
| AI 系统人格 | `resc/persona.txt` |
| 离线兜底回复（人设一致） | `lib/script/chat/bot_reply.py` |
| 命令提示默认行、侧标 | `lib/script/ui/command_hint_box.py` |
| 控制面板水印 | `lib/script/ui/ai_settings_panel.py` |
| 主窗口关闭按钮文案 | `lib/script/ui/close_button.py`（当前为「关闭程序」） |
| 用户文档门户 / 必读页 | `AA使用必读.html`（脚本生成：贡献 `开发贡献*.txt` + `doc/*.txt`；不含赞助/打赏区块）、`scripts/generate_doc_portal.py` |

---

## 5. 与原作 / 上游的关系（口径）

- **发布必读**：根目录 **[`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md)** 写明两条上游 lineage 与「本维护者为整合者」；GitHub Release 请一并附上。
- 本仓库 **代码与资源基线** 可溯源至原「飞行雪绒 / FlyingSnowVelvet-Aemeath」类项目；**素材与上游名称的权属** 以 `LICENSE-ASSETS` 为准。
- **「爱弥斯」** 为本分支采用的 **产品显示名与人设名**，用于界面与文档；**不等于** 自动获得上游商标或全部美术资源的再授权。
- 贡献名单中的 **「爱弥斯语音模型」** 等条目为 **原作素材与声线署名**；与本分支桌宠角色名 **爱弥斯（Aemeath）** 一致，均尊重上游《鸣潮》相关素材授权范围（见 `LICENSE-ASSETS`）。
- **上游原作者社交平台（致谢，非本分支维护者）**：桌宠基线核心开发者 **Mark42 的铁镐**（哔哩哔哩 <https://space.bilibili.com/486401719>）；工作台原维护者 **[AugustUp](https://github.com/AugustUp)** / [phd_master_system](https://github.com/AugustUp/phd_master_system)，以及上游 readme 鸣谢的小红书来源 **不是黑子是癫子**（`61709040774`）、**橘子汽水**（`romantic_Ksir`）。完整表格见 **`README.md`「上游作者与社交平台致谢」**。
- **科研工作台** readme 中对来源链、鸣谢及「学习交流 / 非盈利 / Issue 删库」等表述，见 **`README.md`** 与 **`resc/workbench/README.txt`** 中的**摘录**；完整与最新版本以该 GitHub 仓库为准。

---

## 6. 后续 UI 与原作游戏剥离（记录）

爱弥斯 **不依赖** 用户安装《鸣潮》。**粉青像素与边框层次** 保留。

| 范围 | 状态（2026-05-04） |
|------|---------------------|
| 右键宠物 · 命令面板 | **已完成**：不再装配「启动鸣潮」；`ChatModeButton` 锚在穿透按钮上方；默认提示 `#-快捷命令`。`lib/script/ui/launch_wuwa_button.py` 仍存在于仓库，主流程不再 `import` 实例化。 |
| 设置 / 控制面板 | **已完成**：移除「鸣潮设置」分节与 `launch_wuwa_path` 表单项及鸣潮专用文件浏览；`config_music.launch_wuwa_path` 键保留、注释为弃用，避免旧共享配置读盘报错。 |
| 提示与 Tooltip | **未改**：`tooltip_config.py` 仍含 `launch_wuwa_button` 条目（仅遗留模块若被引用时有效，可后续删除）。 |
| 音乐调度逻辑 | **已完成**：音乐搜索结果排序不再对「鸣潮」作者名加权，仅保留歌名完全匹配优先（`lib/script/tool_dispatcher/dispatcher.py`）。 |

详细文件级索引见 **`PROGRESS.md` §5.1** 与里程碑 **UX-1**。

---

## 7. 维护备忘

- **本分支维护者（对外署名，文档用）**：哔哩哔哩用户「靓点迷人」（站内标识 `bili_2719061712`，空间 <https://space.bilibili.com/2719061712>）；小红书用户「皮鼓很痒」（小红书号 `533497202`）。与上游/原作致谢名单无关；**应用内「关注作者」链接仍以 `app_brand.py` → `AUTHOR_BILIBILI_SPACE_URL` 为准**，若需与上述署名一致，请同步修改该常量。
- 新增面向用户的字符串时，优先 **`from app_brand import APP_DISPLAY_NAME, APP_TAGLINE`**，避免硬编码「爱弥斯」四处漂移。
- 若英文 README 仍以仓库原名为标题，可在首段用中文或英文加一行 **Fork 显示名：Aemeath / 爱弥斯**，与根目录 `README.md` 当前做法一致。
- 功能路线图、技术挂点仍以 **`PROGRESS.md`** 为准；本文不重复里程碑细节。

---

*最后更新：与仓库内 `app_brand.py` 及品牌相关提交保持同步；大改产品方向时更新 §2–§3；动 UI 时更新 §6。*

**学术数据路径（与 `PROGRESS.md` 一致）**：`{系统盘}:\AemeathDeskPet\academic\deskpet_academic.db`（由 `get_shared_root_dir()` 决定盘符）；同级 **`attachments/`** 预留。论文、项目与任务进度 **只以 `resc/workbench` 科研工作台（浏览器）为准**；上述 SQLite 仅为路径占位 / 将来扩展；日志中可出现 **`[Academic] 数据库就绪 schema=…`**。
