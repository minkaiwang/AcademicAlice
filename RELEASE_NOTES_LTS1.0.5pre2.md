# 爱弥斯 LTS1.0.5pre2

> 稳定性预发布候选，日期：2026-07-26。GitHub 预发布正文应与本文件保持一致。

## 本版定位

本版集中处理数据安全、更新安全、凭据保护、进程退出、离线工作台、安装构建、
依赖供应链和项目治理问题。它不是一次视觉重做，也不把自动化结果表述为真实
账号、音频硬件或长期真人体验已经通过。

## 主要变化

- 科研工作台主状态写入用户共享目录的版本化 JSON，支持原子写入、轮换备份、
  损坏恢复与旧浏览器 `localStorage` 迁移。
- 更新器改为“检查 → 明确资产与 manifest → 大小 / SHA256 校验 → 用户确认
  → 完整备份 → 应用 → 失败回滚”，并阻断路径穿越、符号链接和压缩炸弹。
- 更新检查按版本顺序识别 `pre`、正式版与后续版本；发布日期仅为旧式标签
  兜底，避免同日漏报新版本或因未来日期发生降级。
- API Key 与元宝登录参数使用当前 Windows 用户的 DPAPI 加密；AI shell 默认
  关闭，浏览器工具拒绝本机、私网和危险 URL。
- 元宝服务只监听回环地址并要求 Bearer Key；冻结程序可用独立服务子模式启动，
  空密钥保持 401 且不启动浏览器。
- 正常退出不再直接强杀；GSVmove 只管理本应用创建的进程，后台服务日志可追踪。
- 工作台的 Tailwind、Chart.js 与 Font Awesome 已本地化，并完成桌面、
  390 px 移动端及断网 Chromium 回归。
- 安装器增加安全下载、固定哈希和安全解压；PyInstaller 固定为 6.21.0，
  Python 支持矩阵统一为 3.11–3.13。
- 发行脚本使用受控文件清单和确定性 ZIP，排除构建缓存、日志、用户数据、登录态、
  备份与临时文件，并生成 manifest 与 SHA256。
- 默认依赖移除会锁定受已知漏洞影响 `cryptography` 版本的可选 `musicdl`；
  QQ / 酷狗回到直接接口并在失败时安全降级。
- 新增项目管理、工程修改历史、未来路线图、深度审计报告和第三方组件通知。

完整变化见 [`CHANGELOG.md`](CHANGELOG.md)，工程证据见
[`CHANGE_HISTORY.md`](CHANGE_HISTORY.md) 与
[`AUDIT_REPORT_2026-07-26.md`](AUDIT_REPORT_2026-07-26.md)。

## 兼容与迁移

- 系统：Windows 10 / 11。
- Python：3.11–3.13。
- 新安装默认共享数据根：`%LOCALAPPDATA%\AemeathDeskPet`。
- 若旧版 `{SystemDrive}\AemeathDeskPet` 已存在则继续沿用；也可通过
  `AEMEATH_SHARED_ROOT` 显式指定。
- 旧明文凭据会迁移到 DPAPI 存储；工作台旧浏览器缓存会在首次成功迁移后退出
  主存储职责。

## 候选版验证

截至 2026-07-26，本地验证结果：

- pytest：81 passed、2 skipped、21 subtests passed；跳过项为当前 Windows 账户
  无法创建符号链接的兼容性测试。
- `compileall`、Ruff 关键正确性规则、品牌文字检查与 `git diff --check` 通过。
- `pip check` 通过；开发、服务与可查询的运行依赖未发现已知漏洞。
- 源码包与绿色包清单干跑通过。
- PyInstaller 6.21.0 onedir 构建成功（3,513 个文件、670,962,040 bytes；
  EXE 17,839,711 bytes）；冻结 EXE 启动元宝子服务后，
  `/openapi.json` 返回 200，未授权 `/fsv/status` 返回 401，退出后端口释放。

## 已知边界

- `LICENSE-ASSETS` 限制受限美术 / 音频公开再分发；没有权利人书面授权时不得
  发布含这些素材的公开包。
- `services/yuanbao-free-api/` 的上游尚无可随包提供的独立许可证正文。
- pyncm 1.8.1 原分发入口失效，当前 vendored wheel 已固定 SHA256 并按 RECORD
  验证，但无法通过公开漏洞库查询；后续仍应替换。
- AI、元宝扫码、QQ / 网易 / 酷狗、麦克风、Vosk、GSVmove 与 30–60 分钟常驻
  仍需维护者在真实账号和硬件上验收。

## 下载附件命名

仅在许可关卡通过并完成最终确认后生成或上传：

| 附件 | 适用对象 |
|---|---|
| `AemeathDeskPet-LTS1.0.5pre2.zip` + 同名 `.sha256` | 开发者 / 自带 Python |
| `AemeathDeskPet-LTS1.0.5pre2-green.zip` + 同名 `.sha256` | 无需另装 Python 的终端用户 |

源码分支可以先进入代码评审并创建不含手工附件的 GitHub 预发布；许可未清关时
不上传公开 ZIP、EXE 或其他二进制发行包。
