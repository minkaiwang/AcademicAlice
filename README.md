# 学术爱丽丝（Academic Alice）— 学术桌面助手

**Windows 常驻应用**：在桌面一侧提供 **AI 桌宠陪伴**，并通过浏览器内 **爱丽丝科研工作台** 承载论文、项目与任务进度（本机页面）。对外显示名、标语以根目录 **`app_brand.py`**（`APP_DISPLAY_NAME` / `APP_TAGLINE`）为准；`config/version_info.py` 导出版本号；AI 系统人格见 **`resc/persona.txt`**。

> **重要 · 来源与致谢**  
> 本仓库是在 **两条上游产品线** 上整合而成；**维护者（靓点迷人 / 皮鼓很痒）仅为整合与改编，不是下表所列原作者。**  
> 完整说明与许可边界见 **[`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md)**（发布、转载请务必保留）。

---

## 上游作者与社交平台致谢（必读）

下列链接来自原项目贡献名单或上游仓库公开 readme；**请尊重并支持原作者**，勿将「学术爱丽丝」误认为其官方续作。

### 一、桌宠与 AI 基线 ·「飞行雪绒 / FlyingSnowVelvet-Aemeath」

| 角色 | 称呼 | 平台 | 账号 / 主页 |
|------|------|------|-------------|
| **原项目核心开发者** | Mark42 的铁镐 | 哔哩哔哩 | [space.bilibili.com/486401719](https://space.bilibili.com/486401719) |

- 原项目为 **免费开源** 的模块化 Windows 桌宠（PyQt5、音乐、语音、AI 聊天、托盘与命令系统等）。  
- **代码**许可见 [`LICENSE-CODE`](LICENSE-CODE)；**美术、音频与上游名称**见 [`LICENSE-ASSETS`](LICENSE-ASSETS)。  
- 启动/关闭动画、语音模型、字体素材等其他贡献者见 [`doc/贡献名单和主播的狗盆/开发贡献.txt`](doc/贡献名单和主播的狗盆/开发贡献.txt)（含哔哩哔哩链接）。

### 二、科研工作台 ·「博士工作台 / phd_master_system」

| 角色 | 称呼 | 平台 | 账号 / 主页 |
|------|------|------|-------------|
| **原仓库维护者** | AugustUp | GitHub | 个人：[github.com/AugustUp](https://github.com/AugustUp) · 原仓库：[AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system)（**MIT**） |
| **上游 readme 鸣谢 · 源码/思路来源** | 不是黑子是癫子 | 小红书 | 小红书号 `61709040774` · [用户主页](https://www.xiaohongshu.com/user/profile/61709040774) |
| **上游 readme 鸣谢 · 源码/思路来源** | 橘子汽水 | 小红书 | 小红书号 `romantic_Ksir` · [用户主页](https://www.xiaohongshu.com/user/profile/romantic_Ksir) |

原维护者在 [phd_master_system](https://github.com/AugustUp/phd_master_system) 公开 readme 中的说明（**摘录**，著作权与立场归其本人；若与 GitHub 最新 readme 不一致，以原仓库为准）：

> 感谢小红书用户分享的源文件，我在原有基础上完善了桌面端与移动端适配，并新增了坚果云网盘数据同步功能。 衷心鸣谢直接提供源码参考的用户： 「不是黑子是癫子」— 小红书号：61709040774 「橘子汽水」— 小红书号：romantic_Ksir 同时也向为上述源码提供者贡献内容的原始作者们致以谢意。本项目仅用于学习交流，非商业用途、未用于盈利。如涉及侵权，请通过 Issue 联系，我将立即处理删库。

本仓库内嵌页位于 `resc/workbench/`，为 **改编与 PyQt 宿主衔接**，**不等同于**上游完整应用；坚果云等能力若未随包提供，见 [`resc/workbench/README.txt`](resc/workbench/README.txt)。

### 三、本分支维护者（整合者，非上表原作者）

| 称呼 | 平台 | 账号 / 主页 |
|------|------|-------------|
| 靓点迷人 | 哔哩哔哩 | [space.bilibili.com/2719061712](https://space.bilibili.com/2719061712)（站内标识 `bili_2719061712`） |
| 皮鼓很痒 | 小红书 | 小红书号 `533497202` |

应用内托盘「关注作者」链接以 [`app_brand.py`](app_brand.py) 中 `AUTHOR_BILIBILI_SPACE_URL` 为准，可与上表分别配置。

---

中文产品定位与界面触点索引：**[`PRODUCT.md`](PRODUCT.md)**。里程碑、架构与数据路径约定：**[`PROGRESS.md`](PROGRESS.md)**。

浏览器内汇总 **贡献记录**（`doc/贡献名单和主播的狗盆/开发贡献*.txt`）与 **`doc/*.txt`**：**双击打开 [`AA使用必读.html`](AA使用必读.html)**（由 `python scripts/generate_doc_portal.py` 生成；门户不含赞助/打赏展示区块）。

---

## 本项目合并了什么

| 组成部分 | 说明 |
|----------|------|
| **桌宠与 AI 基线** | 源自「飞行雪绒 / FlyingSnowVelvet-Aemeath」类 PyQt5 桌宠：音乐、语音、聊天、托盘、命令提示等。美术与上游名称权属见 **`LICENSE-ASSETS`**。 |
| **科研工作台** | 静态资源在 **`resc/workbench/`**（主页面 `research_workbench.html`；旧名 `phd_workbench.html` 可作回退）。信息架构与交互参考 [AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system)（**MIT**），本仓已做 Tailwind 本地化、多主题与 PyQt 宿主嵌入，**非**对该上游的完整镜像。构建与存储键见 **`resc/workbench/README.txt`**。 |

源码与可分发组件的修改范围以 **`LICENSE-CODE`**、**`LICENSE-ASSETS`** 及上游许可证为准；**「可免费修改」不构成对受限素材的额外授权**，商用与再分发前请自行核对条款。

---

## 主要差异（概要，相对单独使用桌宠或单独打开工作台）

- **同一进程、同一套托盘与命令面板**：减少在浏览器与桌宠之间来回切换。
- **「学术爱丽丝」人设与 UI 统一**：粉青像素风保留；**专用聊天窗口**（命令里「与学术爱丽丝聊天」）为 **粉色系** 独立窗，发送仍走与桌旁气泡相同的聊天管线。
- **本地优先**：论文、项目与工作台配置等以本机存储为主（具体键名与路径以 `PROGRESS.md` / `workbench` README 为准）。
- **可扩展结构**：管理器 `obj-*` 扫描注册、事件总线等（见 `PROGRESS.md` §2）。

---

## 下载与安装（终端用户）

发布包与历史下载入口以项目主页 / Release 为准（若 README 中外链变更，以仓库最新说明为准）。

1. 下载 Windows 压缩包或安装包。  
2. 解压后 **勿只拷贝单个 exe**：保持目录内资源完整。  
3. 若 SmartScreen 拦截，可选择「更多信息」→「仍要运行」。  
4. 首次运行按界面完成语言、位置、模块开关等设置。

---

## 开发者克隆本仓库

```text
# 建议使用 Python 3.10+，依赖见 install/ 目录说明
python install/install_deps.py
# 或双击根目录「安装依赖.bat」（会调用 install/安装依赖.bat）
# 按 PROGRESS.md 与 resc/workbench/README.txt 构建工作台 CSS（若修改 HTML）
```

**Windows 绿色包（给未装 Python 的好友）**：在已能本地运行的环境下双击 **`打包Windows.bat`**（或 **`install/打包Windows.bat`**），使用 **`install/deskpet.spec`**；产物为 `dist/AcademicAlice/`。将整个 **`AcademicAlice` 文件夹** 压缩为 zip 发送即可。打包用的 Python 必须与运行依赖一致（需已安装 **PyQt5**）。

**安装与依赖文件**集中在 **`install/`**（`install_deps.py`、`requirements.txt`、打包脚本等）；根目录 **`requirements.txt`** 仅一行 `-r install/requirements.txt`，便于 `pip install -r requirements.txt` 习惯不变。

---

## 主要功能一览

- 桌面 AI 宠物、拖拽、设置与托盘  
- AI 聊天（桌旁气泡 + **专用聊天窗**）  
- 音乐 / 语音等模块（以当前分支实现为准）  
- **学术**：事件与论文、项目进度；**科研工作台**内嵌页（导出、主题等）  

---

## 文档地图

| 文件 | 用途 |
|------|------|
| `README.md` | 本页：仓库级介绍与合并说明 |
| `ACKNOWLEDGMENTS.md` | **上游致谢与整合者说明（发布必附）** |
| `PRODUCT.md` | 品牌、中文介绍稿、用户可见文案索引 |
| `PROGRESS.md` | 技术 SSOT、里程碑、决策记录 |
| `AA使用必读.html` | 脚本生成门户：贡献原文、`doc/*.txt`（无赞助/打赏区块） |
| `doc/合并项目与使用入口.txt` | 合并来源、入口、许可提醒（纯文本） |

---

## 隐私与网络

部分 AI 能力需联网；工作台图表等可能依赖公共 CDN（断网时可能降级）。请勿将敏感论文全文默认发往外部服务；具体以各设置项与后续 `PROGRESS.md` 约定为准。

---

## English summary

**Academic Alice** is a Windows desk-pet app merged with an embedded **research workbench** (MIT-inspired UI in `resc/workbench/`, not a full upstream mirror) and **local-first** academic scheduling / papers / project tracking. Persona: `resc/persona.txt`. Assets: see **`LICENSE-ASSETS`**.

**Upstream credit (not the fork maintainer):** (1) Desk-pet baseline — **Mark42 的铁镐**, Bilibili [486401719](https://space.bilibili.com/486401719), FlyingSnowVelvet-Aemeath lineage; (2) Workbench — **[AugustUp](https://github.com/AugustUp)** / [phd_master_system](https://github.com/AugustUp/phd_master_system) (MIT), plus Xiaohongshu sources cited in upstream readme: **不是黑子是癫子** (`61709040774`), **橘子汽水** (`romantic_Ksir`). Full tables: Chinese section **「上游作者与社交平台致谢」** and [`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md).

**Fork integrator (docs):** Bilibili 「靓点迷人」 / [2719061712](https://space.bilibili.com/2719061712); Xiaohongshu 「皮鼓很痒」 / `533497202`. Tray link: `app_brand.py`. Portal: **`AA使用必读.html`**.

---

*本 README 为人工维护；`AA使用必读.html` 由脚本从 `doc/` 等文件生成。若与代码或 `PROGRESS.md` 不一致，以代码与 `PROGRESS.md` 为准。*
