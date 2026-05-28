# 致谢与来源说明（Acknowledgments）

**爱弥斯（Aemeath）** 是在他人开源成果之上做 **整合、改编与宿主衔接** 的分支。  
**本仓库当前维护者（靓点迷人 / 皮鼓很痒 等，见 README）是整合与文档维护角色，不是上述两条产品线的原创作者。**

发布、转载或二次开发时，请 **保留本文件与 `LICENSE-CODE` / `LICENSE-ASSETS` 中的归属说明**，并分别遵守各上游许可证。

---

## 一、桌宠与 AI 交互基线（飞行雪绒系）

| 项 | 说明 |
|----|------|
| **性质** | Windows PyQt5 桌宠：音乐、语音、AI 聊天、托盘、命令面板、场景物体（`obj-*`）等 |
| **可溯源名称** | 「飞行雪绒 / FlyingSnowVelvet-Aemeath」类项目 |
| **代码许可** | 见仓库根目录 **`LICENSE-CODE`**（Apache-2.0，以文件正文为准） |
| **美术 / 音频 / 名称等** | 见 **`LICENSE-ASSETS`**；**不得**因本分支改名而视为获得额外素材授权 |
| **贡献记录** | `doc/贡献名单和主播的狗盆/开发贡献*.txt`（含 Mark42 的铁镐 等社区贡献者） |
| **GitHub（历史/上游参考）** | 以 `config/version_info.py` 中 `GITHUB_REPO` 及你 fork 的上游为准 |

**原项目核心开发者（社交平台）**

| 称呼 | 平台 | 主页 |
|------|------|------|
| Mark42 的铁镐 | 哔哩哔哩 | <https://space.bilibili.com/486401719> |

更多贡献者（动画、语音、素材等）见上表「贡献记录」路径中的具名名单与链接。

**向该基线的原创者与贡献者致谢**：没有原项目的模块化架构与社区素材，就不会有本分支的桌宠能力。

---

## 二、爱弥斯科研工作台（博士工作台系）

| 项 | 说明 |
|----|------|
| **性质** | 浏览器内单页：论文、项目、任务等学术进度管理（本机 `localStorage` 为主） |
| **上游仓库** | **[AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system)** |
| **许可** | **MIT**（以该仓库 LICENSE 为准） |
| **本仓实现** | `resc/workbench/research_workbench.html`（及 Tailwind bundle、主题与 PyQt 宿主 `workbench_host.py` 等） |
| **关系** | **改编与嵌入，非** 对上游应用的完整镜像；坚果云等部分能力可能未随包提供，见 `resc/workbench/README.txt` |

**原仓库维护者与 readme 鸣谢来源（社交平台）**

| 角色 | 称呼 | 平台 | 主页 / 账号 |
|------|------|------|-------------|
| 原仓库维护者 | AugustUp | GitHub | 个人 <https://github.com/AugustUp> · 仓库 <https://github.com/AugustUp/phd_master_system> |
| 上游 readme 鸣谢 · 源码/思路来源 | 不是黑子是癫子 | 小红书 | 号 `61709040774` · <https://www.xiaohongshu.com/user/profile/61709040774> |
| 上游 readme 鸣谢 · 源码/思路来源 | 橘子汽水 | 小红书 | 号 `romantic_Ksir` · <https://www.xiaohongshu.com/user/profile/romantic_Ksir> |

**向上游维护者及 readme 中致谢的小红书来源链致谢**（原文摘录见根目录 `README.md`「上游作者与社交平台致谢」与 `resc/workbench/README.txt`）。著作权与「学习交流 / 非盈利」等立场 **归原维护者**。

---

## 三、本分支维护者（整合者）

- 产品显示名 **「爱弥斯」**、人设 `resc/persona.txt`、科研工作台宿主、文档门户、`obj-academic`、打包与安装目录整理等，为 **本 fork 的整合与维护**。
- 维护者署名（文档用）：哔哩哔哩「靓点迷人」、小红书「皮鼓很痒」等 — 见 **`README.md`**。
- 应用内托盘 **「关注作者」** 链接以 **`app_brand.py` → `AUTHOR_BILIBILI_SPACE_URL`** 为准，可与文档署名分别配置。

---

## 四、其他集成组件（节选）

完整名单见 `doc/贡献名单和主播的狗盆/开发贡献.txt`，包括但不限于：

- **chenwr727/yuanbao-free-api** — 元宝 OpenAI 兼容本地中转（`services/bundles/`）
- **jsososo/QQMusicApi**、**listen1/listen1_chrome_extension** — QQ 音乐相关参考与适配
- 启动/关闭动画、语音模型、字体素材等 — 见贡献文件中的具名贡献者

---

## 五、发布时请一并附带

- 本文件 **`ACKNOWLEDGMENTS.md`**
- **`LICENSE-CODE`**、**`LICENSE-ASSETS`**
- **`README.md`**（含上游摘录与 English summary）
- 可选：**`AA使用必读.html`**（由 `python scripts/generate_doc_portal.py` 生成）

若你认为某处署名遗漏或表述不当，请通过 Issue 联系维护者更正。
