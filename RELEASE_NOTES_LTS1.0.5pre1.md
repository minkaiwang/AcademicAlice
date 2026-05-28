# 爱弥斯 LTS1.0.5pre1

## 来源与致谢（请先读）

本版本为 **整合发行**，维护者负责缝合与文档，**非** 下列两条产品线的原创作者：

1. **桌宠 / AI 基线** — 飞行雪绒 / FlyingSnowVelvet-Aemeath 系（`LICENSE-CODE` + `LICENSE-ASSETS`）
2. **科研工作台** — [AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system)（MIT）

详见仓库 **[ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)** 与 [README.md](README.md)。

---

## 本版要点

- 产品名 **爱弥斯**：桌宠 + 浏览器内爱弥斯科研工作台（`resc/workbench/`）
- 默认 **主桌宠置顶**、**自动漫游**（可在控制面板调整）
- 托盘 **云音乐（音响搜索）**；命令 `#音响 1` 召唤音响后右键打开搜索
- 安装与打包脚本集中在 **`install/`**；Windows 绿色包见 `install/打包Windows.bat` → `dist/AemeathDeskPet/`

完整变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 下载说明

| 附件 | 适用对象 |
|------|----------|
| `FlyingSnowVelvet-LTS1.0.5pre1.zip` | 开发者 / 自带 Python：解压后运行 `安装依赖.bat` → `启动程序.bat` |
| `AemeathDeskPet` 文件夹（若另附） | 终端用户：解压整文件夹后运行 `AemeathDeskPet.exe`，**无需安装 Python** |

文档门户：解压后打开 **`AA使用必读.html`**。

---

## 已知提醒

- 元宝 Web 模式（`FORCE_REPLY_MODE=4` + 本地 8000 端口）需完整依赖；缺包时见气泡提示，可改 `config/ollama_config.py` 或运行 `安装依赖.bat`
- 启动请用 **`调试模式.bat` / `启动程序.bat`**（读 `py.ini`），勿用未装 PyQt5 的 `py -3` 解释器
