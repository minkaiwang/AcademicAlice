# 第三方组件与许可证记录

本文件记录当前已核实的主要第三方代码与前端资源。它不替代
`ACKNOWLEDGMENTS.md`、`LICENSE-CODE` 或 `LICENSE-ASSETS`。

| 组件 | 本地路径 | 来源与版本 | 许可证与随包文件 | 状态 |
|---|---|---|---|---|
| 博士科研工作台 | `resc/workbench/` | AugustUp/phd_master_system；精确导入 commit 未知 | MIT；`resc/workbench/LICENSE-UPSTREAM-MIT` | 已核实 |
| Tailwind CSS | `resc/workbench/tailwind.bundle.css` | `tailwindcss@3.4.17`（CSS 内版本头及固定构建命令） | MIT；`resc/workbench/LICENSE-TAILWIND-MIT` | 已核实 |
| Chart.js | `resc/workbench/vendor/chart.js/` | npm `chart.js@4.4.8` | MIT；同目录 `LICENSE.md` | 已核实 |
| Font Awesome Free | `resc/workbench/vendor/fontawesome/` | npm `@fortawesome/fontawesome-free@6.5.2` | 图标 CC BY 4.0、字体 SIL OFL 1.1、代码 MIT；同目录 `LICENSE.txt` | 已核实 |
| Vosk 中文小模型 | `resc/models/vosk-model-small-cn-0.22/`（绿色包可选随包） | 官方 `vosk-model-small-cn-0.22.zip`；SHA256 `3af8b0e7e0f835ae9d414ce5df580237a3cfb08d586c9fbbb0f7ff29ad5b14ba` | Apache-2.0；完整条款见根目录 `LICENSE-CODE` | 已核实 |
| Vosk 英文小模型 | `resc/models/vosk-model-small-en-us-0.15/`（绿色包可选随包） | 官方 `vosk-model-small-en-us-0.15.zip`；SHA256 `30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498` | Apache-2.0；完整条款见根目录 `LICENSE-CODE` | 已核实 |
| pyncm | `vendor/pyncm-1.8.1-py3-none-any.whl` | 原 PyPI `pyncm==1.8.1` 安装副本重打；来源断链与逐文件校验见 `vendor/README.md` | Apache-2.0；wheel 内 `dist-info/LICENSE`，SHA256 `a1798e9ff9007723d0a34b4d61b51b385b5bedb6caac6e04ce5572d00193183c` | 已核实、离线固定 |
| PyInstaller（仅构建工具） | `install/deskpet.spec`、`install/打包Windows.bat` | `pyinstaller==6.21.0` | GPL-2.0-or-later WITH Bootloader-exception；上游明确生成包可按应用自身许可证分发、无需随包附 PyInstaller 许可证 | 已核实 |
| yuanbao-free-api | `services/yuanbao-free-api/` | chenwr727/yuanbao-free-api；精确导入 commit 未知 | README 声明 MIT，但无独立许可证文本 | **正式发布前需确认** |

前端资源的 npm integrity 与逐文件 SHA256 见
`resc/workbench/vendor/README.md`；上游定位与不能补猜的边界见各目录
`UPSTREAM.md`。

其他音乐、模型、美术、字体和音频素材继续受 `LICENSE-ASSETS` 与
`doc/贡献名单和主播的狗盆/` 中的来源记录约束。正式发布前必须按
`RELEASING.md` 的许可证关卡逐项确认，不得因为代码测试通过而跳过。
