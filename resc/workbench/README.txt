爱弥斯科研工作台（本目录静态资源）
========================================

- **主页面**：`research_workbench.html`（基于 [AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system) 的改编版本，MIT；许可证与上游核验见 `LICENSE-UPSTREAM-MIT`、`UPSTREAM.md`）
- **上游作者与社交平台（请尊重原作，非本分支维护者）**
  · 原仓库维护者 AugustUp — https://github.com/AugustUp · 仓库 https://github.com/AugustUp/phd_master_system
  · 上游 readme 鸣谢 · 不是黑子是癫子 — 小红书号 61709040774 — https://www.xiaohongshu.com/user/profile/61709040774
  · 上游 readme 鸣谢 · 橘子汽水 — 小红书号 romantic_Ksir — https://www.xiaohongshu.com/user/profile/romantic_Ksir
- **上游 readme 摘录**（致谢与项目性质以原作者为准；全文见该仓库页面）：感谢小红书用户分享的源文件，我在原有基础上完善了桌面端与移动端适配，并新增了坚果云网盘数据同步功能。 衷心鸣谢直接提供源码参考的用户： 「不是黑子是癫子」— 小红书号：61709040774 「橘子汽水」— 小红书号：romantic_Ksir 同时也向为上述源码提供者贡献内容的原始作者们致以谢意。本项目仅用于学习交流，非商业用途、未用于盈利。如涉及侵权，请通过 Issue 联系，我将立即处理删库。
- **样式**：`tailwind.bundle.css`（Tailwind CSS 3.4.17 CLI 扫描 HTML 生成；**勿删**；勿再用 `cdn.tailwindcss.com`；许可证见 `LICENSE-TAILWIND-MIT`）
- **主题**：`data-color-preset="pastel"` + CSS 变量 `--wb-primary|secondary|accent|bg|ink`（JS 写入）。内置 6 套粉彩 + 多巴胺；自定义存 `…__wb_custom_themes_v1` JSON，当前选中存 `…__wb_theme_v2`（含 `custom:<id>`）。旧键 `…__color_preset` 会在首次启动时迁移。
- **图表 / 图标**：固定使用 `vendor/` 内 Chart.js 4.4.8 与 Font Awesome Free 6.5.2；断网可用，版本、许可证、integrity 与 SHA256 见 `vendor/README.md`
- **业务数据**：桌宠宿主模式以稳定 JSON 文件为主、浏览器 `localStorage` 为应急缓存；存储位置、自动备份与旧端口恢复见根目录 `README.md`

── 更新 `research_workbench.html` 后重建 Tailwind ──

```bash
cd resc/workbench
npx --yes tailwindcss@3.4.17 -c tailwind.workbench.config.js -i tailwind.input.css -o tailwind.bundle.css --minify
```

主题色与 Tailwind `theme.extend` 对齐见 `tailwind.workbench.config.js`。

── 打包 exe ──

将 `resc/workbench/` 下 **html + css + sync/ + vendor/ + 许可证/上游记录** 一并列入 PyInstaller `datas`，运行时路径见 `lib/script/workbench_host.py` 的 `_bundle_root()`。

`sync/ui.js`：当前发行明确禁用尚未打包、尚未经凭据安全审计的 WebDAV 控件，避免按钮看似可用但实际无效。不能直接从上游覆盖；恢复云同步前必须同时完成凭据加密、冲突合并、失败回退和端到端测试。
