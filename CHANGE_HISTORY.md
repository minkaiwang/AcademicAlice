# 工程修改历史

> 本文件记录工程修复、验证与边界。面向用户的版本功能变化仍写
> `CHANGELOG.md`；架构决策写 `PROGRESS.md`。当前候选版本为
> `LTS1.0.5pre2`；源码候选已提交并推送至草稿 PR #1，源代码预发布已获
> 维护者授权；尚未合并或发布二进制附件。

## 2026-07-26

### REL-PUBLISH-001：LTS1.0.5pre2 源代码预发布

- 维护者明确授权沿用既有 GitHub Release 流程发布新版本；
- 标签与预发布标题统一为 `LTS1.0.5pre2` / `爱弥斯 LTS1.0.5pre2`，
  Release 正文使用 `RELEASE_NOTES_LTS1.0.5pre2.md`；
- 目标为已通过 Python 3.11–3.13 CI 的稳定化分支提交，草稿 PR #1 保持
  开启以继续代码评审；
- 预发布建立后，维护者进一步明确授权上传开发者源码包；正式生成的 ZIP 含
  868 个 manifest 文件项，大小 36,480,438 bytes，SHA256 为
  `647ba439c744f2260c6ec5f3d8e4dd3a9f51f4754926113a7adb8e5fd3ad98fb`；
- ZIP 完整性、manifest 路径 / 大小一致性和敏感运行文件排除检查通过；
  `tests/test_packaging.py` 为 7 passed、1 skipped，跳过项仍是本机无符号
  链接权限；
- Release 已上传 ZIP、`.zip.sha256`、manifest 和使用说明；GitHub 将独立
  中文说明文件名显示为 `AA.html`。未上传绿色包或 EXE。

### REL-CI-001：GitHub Actions 远程解析修正

- 源码候选提交 `b3bca1c` 已推送至
  `codex/lts1.0.5pre2-stabilization`，并创建草稿 PR #1；
- 首次远程运行 `30207330138` 在创建 job 前失败：作业级 `env` 不支持
  `runner.temp` 上下文，并非 pytest 或应用代码失败；
- 将 `AEMEATH_SHARED_ROOT` 下移到 pytest 步骤的 `env`；该位置允许读取
  `runner.temp`，同时继续把测试数据隔离在 runner 临时目录；
- 修复运行 `30207506852` 的 Python 3.11、3.12、3.13 三套矩阵全部通过，
  包括编译、Ruff、81 项 pytest、依赖审计、品牌检查和发行清单干跑；
- 按官方当前主版本将 `actions/checkout` 与 `actions/setup-python` 升级至 v7，
  消除 Node.js 20 Action 运行时弃用警告；
- 许可清关前仍不创建 Tag 或公开二进制 Release。

### REL-CANDIDATE-002：LTS1.0.5pre2 版本收口

- 从同步后的 `main@418a4c1` 建立
  `codex/lts1.0.5pre2-stabilization`，工作区修复范围保持不变；
- 将应用、资源、源码包、绿色包、文档门户与发布手册统一到
  `LTS1.0.5pre2` / `2026-07-26`；
- 新增 `RELEASE_NOTES_LTS1.0.5pre2.md`，保留
  `RELEASE_NOTES_LTS1.0.5pre1.md` 作为历史版本记录；
- 版本升级回归发现更新器只按发布日期判断；已改为优先比较 LTS / v 风格
  版本顺序，覆盖 `pre1 < pre2 < 正式版 < 后续版本`、同日升级和防降级；
- 候选版完成自动化、依赖审计、发行清单、冻结构建与冻结服务冒烟后方可
  进入提交 / 推送确认；许可清关前不创建公开二进制 Release。

### REL-CANDIDATE-002：提交前验证结果

- pytest：81 passed、2 skipped、21 subtests passed；两项跳过均为当前 Windows
  账户不能创建符号链接；
- `compileall`、Ruff `E9,F63,F7,F82,F841`、品牌检查、
  `git diff --check`、`pip check` 与 23 个发行模块前置检查通过；
- 源码清单：868 文件 / 42,760,365 bytes；绿色清单：896 文件 /
  181,951,603 bytes；
- PyInstaller 6.21.0：3,513 文件 / 670,962,040 bytes，EXE
  17,839,711 bytes，日志无 `ERROR`；
- 冻结服务：`/openapi.json` 200、未授权 `/fsv/status` 401，且空密钥不启动
  浏览器；结束测试进程后端口释放；
- `pip-audit` 的 CycloneDX 漏洞模型字节码被本机火绒启发式拦截；未设置白名单，
  Git 跟踪文件无删除，后续不重复运行该扫描器。

### PM-BOOTSTRAP-001：深度审计与项目治理

- 深读启动链、配置、插件、AI、音乐、语音、工作台、更新、安装、打包、
  内嵌服务、许可和现有日志；
- 建立 `PROJECT_MANAGEMENT.md`、`CHANGE_HISTORY.md`、`ROADMAP.md` 与
  `AUDIT_REPORT_2026-07-26.md`；
- 记录起始基线 `main@418a4c1`，所有正式文件修改前保留忽略的 `.bak`。

### DATA-001：工作台文件主存储

- 新增 `lib/script/workbench_storage.py`，状态写入共享根
  `workbench/state.json`；
- 增加 schema / 类型 / 大小校验、临时文件 + `os.replace`、备份轮换、损坏
  主文件恢复；
- `workbench_host.py` 增加受限回环 JSON API、Host / Origin / Content-Type /
  请求体检查和安全响应头；
- 前端迁移旧 `localStorage` 后以文件 API 为主，提供
  `scripts/recover_workbench_browser_data.py`；
- 单测覆盖读写、恢复、并发宿主、越界、Host 欺骗和请求限制。

### UPD-001：更新事务重建

- “检查更新”与实际应用分离，应用前展示并确认；
- 只接受明确版本资产和 HTTPS manifest，校验名称、大小、SHA256；
- ZIP 解压拒绝父目录、绝对路径、NTFS ADS、设备名、大小写碰撞、符号链接、
  压缩炸弹和受保护路径；
- 应用前完整备份，失败自动回滚并保存状态；下载、提取、复制和状态写入均有
  超时 / 原子性 / 回退测试。

### REL-001：发行包可复核

- 源码包和绿色包改为受控清单，排除 `build/`、`dist/`、用户数据、日志、
  密钥、二维码、浏览器状态、备份与临时文件；
- 正式模式拒绝脏工作树；审查未提交变更需显式 `--allow-dirty`；
- 校验版本字符串、符号链接、工作区逃逸、非普通文件、大小写冲突和打包时
  文件变化；
- ZIP 使用固定时间戳 / 属性，先写 `.tmp` 再原子替换，并生成 manifest 与
  SHA256。

### SEC-001：凭据与本机能力

- 新增 `config/secure_secrets.py`，API Key / 元宝敏感值由 Windows DPAPI
  加密，旧源码明文一次性迁移并可清除；
- 设置页不再把敏感值写回 `config/ollama_config.py`；
- `/` shell 默认关闭，显式启用时使用参数化 argv、超时和摘要审计日志；
- AI 浏览器工具只允许公网 HTTP(S)，拒绝本机 / 私网 / 保留地址、凭据、
  非法端口和危险 scheme；
- 聊天记忆只写用户共享目录，项目内旧文件只作一次迁移源。

### SHUT-001 / SVC-001：生命周期与服务

- 正常退出改走 Qt 事件循环和统一 finalize，`os._exit` 只保留为超时看门狗；
- GSVmove 仅结束本应用创建的进程，等待线程有界，启动日志可诊断；
- 元宝服务只监听 `127.0.0.1`，所有控制 / 聊天 / 上传端点均需 Bearer Key；
- 空密钥时保持 401 且不启动浏览器，登录 / 未登录返回结构化状态，不刷内部
  traceback；
- 冻结 EXE 增加 `--yuanbao-service` 子模式、后台文件日志流与
  Playwright 异步子模块收集，避免无控制台日志初始化失败或隐藏弹窗挂起。

### WEB-001：离线工作台

- Tailwind、Chart.js、Font Awesome 全部本地化；
- 增加相应许可证、上游版本 / 来源记录与发行清单门禁；
- 真实 Chromium 完成 1440×900、390×844、移动菜单与断网回归，无外部
  CDN 请求。

### DEP-001：安装、构建与供应链

- Python 支持矩阵统一为 3.11–3.13；PyInstaller 固定为 6.21.0；
- 新增 `scripts/check_build_environment.py`，构建前检查 23 个发行模块；
- 安装器下载保持 TLS 校验，所有归档安全提取；Vosk 模型固定大小与 SHA256，
  不再执行远程 `get-pip.py` 或下载浮动服务源码；
- 因 pyncm PyPI / 上游入口失效，从本机原安装按 RECORD 逐文件验证后重封装
  最小 wheel，固定 SHA256
  `a1798e9ff9007723d0a34b4d61b51b385b5bedb6caac6e04ce5572d00193183c`；
- 依赖审计发现 `musicdl 2.13.3` 强制 `cryptography<47`，命中
  `GHSA-537c-gmf6-5ccf`；其仅为可选兜底，已从默认安装 / 构建移除，QQ /
  酷狗回到直接接口和安全降级；
- 内嵌服务和开发依赖按准确版本固定，运行依赖审计无已知漏洞；pyncm 因项目
  不可查询只能记录为审计例外。

### QA-001：自动化与回归

- 新增 Windows GitHub Actions，覆盖 Python 3.11、3.12、3.13；
- CI 执行 `compileall`、Ruff 关键正确性规则、pytest、服务 / 运行依赖审计、
  品牌检查和两类发行清单干跑；
- 测试覆盖工作台、更新、打包、凭据、安装器、服务鉴权 / 生命周期、共享
  路径、URL 工具、记忆、插件发现、文字完整性和构建前置；
- 完整运行依赖安装后 `pip check` 通过；服务 / 开发依赖审计通过。

### DOC-001 / LIC-001：文档与许可

- 更新 README、贡献指南、发布手册、安装说明、版本说明和服务说明；
- 补齐工作台上游 MIT、Tailwind、Chart.js、Font Awesome、Vosk、
  PyInstaller 与 pyncm 的来源 / 许可记录；
- `LICENSE-ASSETS` 的受限素材再分发授权和元宝上游许可证正文仍需维护者
  提供，因此未创建正式发行包或 Release。

## 验证记录

最终命令与具体数量以本轮结束时的 `AUDIT_REPORT_2026-07-26.md` 修复对照为
准。这里的“通过”只代表自动化 / 受控冒烟，不代表真实账号、音频硬件和真人
长时间体验已经完成。

## 记录规则

- 后续条目写日期、问题 ID、修改文件、验证证据和已知边界；
- 不把计划写成完成，不把测试通过写成视觉或真人体验通过；
- 提交、推送、Tag、Release、删除历史和公开上传单独记录。
