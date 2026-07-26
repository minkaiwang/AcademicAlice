# Changelog

All notable changes to this project will be documented in this file. This project follows semantic-style tags (`LTS1.0.5pre2`, etc.) and dates use ISO format.

## [1.0.5-pre2] - 2026-07-26

### Added
- 科研工作台改用共享数据目录中的版本化 JSON 主存储，支持原子写入、轮换备份、损坏恢复和旧浏览器缓存迁移。
- 新增带版本清单、大小与 SHA256 校验、用户确认、备份和失败回滚的更新事务。
- 新增 Windows DPAPI 凭据存储、本机元宝服务 Bearer 鉴权、构建环境检查、Windows CI、pytest 回归与确定性发行清单。
- 新增 `PROJECT_MANAGEMENT.md`、`CHANGE_HISTORY.md`、`ROADMAP.md`、审计报告和第三方组件通知。

### Fixed
- 修复工作台因随机端口或浏览器缓存隔离造成的数据丢失风险。
- 修复正常退出强杀进程、GSVmove 误结束非本应用进程、冻结版元宝服务隐藏失败和空密钥仍可能触发浏览器的问题。
- 修复更新包路径穿越、错误附件、无完整性校验、直接覆盖以及失败后无法恢复等高风险路径。
- 修复更新检查只比较发布日期的问题；现在按 `pre` / 正式版与主次修订号排序，同日新版本可更新，未来日期也不能触发降级。
- 修复构建包夹带日志、用户数据、备份、浏览器状态或临时文件的风险。
- 修复工作台依赖公共 CDN 导致断网界面降级的问题，并完成桌面、移动视口和离线 Chromium 回归。

### Changed
- Python 支持矩阵统一为 3.11–3.13；PyInstaller 固定为 6.21.0。
- 新安装的共享数据根默认改为 `%LOCALAPPDATA%\AemeathDeskPet`，已存在的旧系统盘数据目录继续兼容。
- 默认依赖移除会锁定已知受影响 `cryptography` 版本的可选 `musicdl` 兜底；QQ / 酷狗改回直接接口并安全降级。
- pyncm 1.8.1 改用仓库内固定 SHA256、逐文件 RECORD 校验的最小 wheel，以应对原分发入口失效。

### Release status
- 本条目对应 `LTS1.0.5pre2` 稳定性预发布候选。
- 在受限美术 / 音频的再分发授权和内嵌元宝服务许可证正文完成清关前，不发布公开二进制附件或 GitHub Release。
- 自动化通过不代表真实账号、音乐接口、麦克风、GSVmove 与长时间真人运行已经验收。

## [1.0.5-pre1] - 2026-03-18

### Added
- 支持 **语音播报模块**（GSVmove 桥接）并开放麦克风语音识别默认开关，语音控制流程可在 AI 面板中配置。
- 新增 Vosk 语音识别（测试默认开启 `V` 热键），补齐 Push-to-Talk/状态指示。
- Ollama 模块现在可以自动探测已安装模型，缺失时会触发后台下载与提示。
- 桌宠与 UI 面板支持透明度调节，匹配桌面主题。
- 可自定义启动《鸣潮》的可执行路径。
- 与“小爱” 实时语音对话，并允许它直接打开浏览器执行指令。
- AI 面板新增 `YuanBao-Free-API` 预设与 Playwright 登录态抓取，可自动回填 `hy_user` / `hy_token` / `x_uskey` / `agent_id`。

### Fixed
- 尝试修复 QQ VIP 歌曲无法完整播放的问题（仍受版权限制）。
- 修复酷狗歌单获取失败的问题。
- 修复 Gemini 多模态 API 兼容问题。
- 修复自适应缩放逻辑失效的问题。
- 修复物理物体（雪豹/沙发/摩托等）的惯性计算。
- 修复控制面板右键后画面变黑的问题。

### Changed
- 闹钟命令现在统一采用 `[时,分,秒]` 调用形式。
- 内置加密密钥由于成本原因移除，粉丝可自行在群内申请专属 API KEY；加强配置信息的持久化。
- 增补 `#音响` / `#闹钟` / `#雪豹` 等对象管理器的粒子与特效联动。
- 重构大量底层代码（事件、音乐、聊天、UI、安装脚本）并完成多轮性能优化，继续推动迁移清单 Phase 8。
- 仓库默认配置改为不再内置 API Key 与 YuanBao 登录态参数，发布版本号同步更新为 `LTS1.0.5pre1`。

### Disclaimer
- `YuanBao-Free-API` 相关能力仅用于个人学习、研究与兼容性测试，请遵守腾讯元宝及相关平台的服务条款、使用规范和适用法律法规。
- 登录态参数（如 `hy_token`、`hy_user`、`x_uskey`）由用户自行获取、自行保管、自行承担使用风险；请勿传播、售卖、共享或用于未授权用途。
- 上游项目近期已提示 `X-Uskey` 与平台策略可能变化；该类能力可能随时失效，也可能触发风控、告警、限流、功能受限甚至账号处罚，风险需由使用者自行评估并承担。
- 本项目不保证该能力长期可用，也不对第三方平台策略变更、接口失效、账号异常、数据丢失或由此产生的间接损失承担责任。

> Earlier changes are tracked in internal docs; future releases will continue using this Markdown changelog.
