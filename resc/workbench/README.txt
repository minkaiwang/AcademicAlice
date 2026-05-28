爱丽丝科研工作台（本目录静态资源）
========================================

- **主页面**：`research_workbench.html`（旧名 `phd_workbench.html` 仍可作为回退；基于 [AugustUp/phd_master_system](https://github.com/AugustUp/phd_master_system) 单文件，MIT）
- **上游作者与社交平台（请尊重原作，非本分支维护者）**
  · 原仓库维护者 AugustUp — https://github.com/AugustUp · 仓库 https://github.com/AugustUp/phd_master_system
  · 上游 readme 鸣谢 · 不是黑子是癫子 — 小红书号 61709040774 — https://www.xiaohongshu.com/user/profile/61709040774
  · 上游 readme 鸣谢 · 橘子汽水 — 小红书号 romantic_Ksir — https://www.xiaohongshu.com/user/profile/romantic_Ksir
- **上游 readme 摘录**（致谢与项目性质以原作者为准；全文见该仓库页面）：感谢小红书用户分享的源文件，我在原有基础上完善了桌面端与移动端适配，并新增了坚果云网盘数据同步功能。 衷心鸣谢直接提供源码参考的用户： 「不是黑子是癫子」— 小红书号：61709040774 「橘子汽水」— 小红书号：romantic_Ksir 同时也向为上述源码提供者贡献内容的原始作者们致以谢意。本项目仅用于学习交流，非商业用途、未用于盈利。如涉及侵权，请通过 Issue 联系，我将立即处理删库。
- **样式**：`tailwind.bundle.css`（Tailwind CLI 扫描 HTML 生成；**勿删**；勿再用 `cdn.tailwindcss.com`）
- **主题**：`data-color-preset="pastel"` + CSS 变量 `--wb-primary|secondary|accent|bg|ink`（JS 写入）。内置 6 套粉彩 + 多巴胺；自定义存 `…__wb_custom_themes_v1` JSON，当前选中存 `…__wb_theme_v2`（含 `custom:<id>`）。旧键 `…__color_preset` 会在首次启动时迁移。
- **图表 / 图标**：仍依赖 jsDelivr、cdnjs 外链（断网时图表或图标可能异常）

── 更新 `research_workbench.html` 后重建 Tailwind ──

```bash
cd resc/workbench
npx --yes tailwindcss@3.4.17 -c tailwind.workbench.config.js -i tailwind.input.css -o tailwind.bundle.css --minify
```

主题色与 Tailwind `theme.extend` 对齐见 `tailwind.workbench.config.js`。

── 打包 exe ──

将 `resc/workbench/` 下 **html + css + sync/** 一并列入 PyInstaller `datas`，运行时路径见 `lib/script/workbench_host.py` 的 `_bundle_root()`。

`sync/ui.js`：坚果云 UI 占位；完整同步需从上游拷贝。
