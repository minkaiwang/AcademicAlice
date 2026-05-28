# Release Playbook

> Applies to the LTS1.0.5 beta series. Adjust version strings and artifact names as needed.

## 1. Pre-flight checklist

1. **Set the version**  
   - Update user-facing text (`README.md`, `CHANGELOG.md`, installer banner if required).  
   - Bump default tag in `scripts/package_release.py` if the marketing codename changes.
2. **License sanity check**  
   - Confirm code changes remain under Apache-2.0 (no third-party files with incompatible licenses).  
   - Ensure any new fonts/audio/images have distribution rights per [LICENSE-ASSETS](LICENSE-ASSETS) and are documented if restrictions apply.
3. **Regenerate docs**  
   ```powershell
   python scripts/generate_doc_portal.py
   ```
   Validate `AA使用必读.html`，确保贡献列表与 DOC 区卡片已随 `doc/` 刷新。
4. **Static checks**  
   ```powershell
   python -m compileall config lib install/install_deps.py scripts
   python scripts/package_release.py --dry-run
   ```
   The dry-run prints the final manifest and ensures runtime-only files (logs, resc/user, models) are excluded.
5. **Runtime smoke**  
   Launch `python lib/core/qt_desktop_pet.py` once, verify：  
   - AI 模式（OpenAI/Ollama）能初始化；  
   - 音乐（任选 `netease/qq/kugou`）能搜索/播放；  
   - 粒子与对象命令（`#雪豹/#沙发/...`）可生成并清理；  
   - GSVmove / STT（若启用）可以启动且不会阻塞退出。

## 2. Build artifacts

```powershell
python scripts/package_release.py --version LTS1.0.5beta9
```

- 输出位置：`dist/FlyingSnowVelvet-LTS1.0.5beta9.zip`
- 附带 `dist/FlyingSnowVelvet-LTS1.0.5beta9-manifest.json`，列出所有文件与大小，便于校验
- zip 会排除 `logs/`、`resc/models/`、`resc/user/`、`.git/`、`.github/`、`__pycache__/`、安装脚本产生的临时文件，并写入占位 `.keep` 以确保必要目录存在

可选：运行 `Get-FileHash dist/FlyingSnowVelvet-LTS1.0.5beta9.zip -Algorithm SHA256` 生成校验值。

## 3. GitHub release

**仓库：** <https://github.com/minkaiwang/AemeathDeskPet>（`config/version_info.py` → `GITHUB_REPO = "minkaiwang/AemeathDeskPet"`）

发布前运行品牌检查：

```powershell
python scripts/check_brand_strings.py
python scripts/generate_doc_portal.py
```

1. 创建 Tag（例如 `git tag -a LTS1.0.5pre1 -m "爱弥斯 LTS1.0.5pre1"`，`git push origin LTS1.0.5pre1`）
2. 新建 Release：**标题** 使用 **爱弥斯**（勿用旧名「学术爱丽丝」），与 `app_brand.py` 一致
3. Release Notes：**全文复制** 根目录 [`RELEASE_NOTES_LTS1.0.5pre1.md`](RELEASE_NOTES_LTS1.0.5pre1.md)（或 `CHANGELOG.md` 对应段落），并核对绿色包名为 **`AemeathDeskPet`** / **`AemeathDeskPet.exe`**
4. 若已发布的 `LTS1.0.5pre1` 仍为旧文案，在 GitHub → Releases → Edit 更新标题与正文（附件 zip 可保留）
5. 附件：
   - `dist/FlyingSnowVelvet-LTS1.0.5pre1.zip`（源码树）
   - 可选：`dist/AemeathDeskPet/` 整夹 zip（PyInstaller 绿色包）
   - `AA使用必读.html`（方便在线查看文档）

## 4. Post-release

- 在 `doc/迁移清单任务.txt` 更新阶段进度
- 如涉及 API key / 配置变更，通知群内粉丝重新生成 `config/ollama_config.py`
- 观察 GitHub Actions CI（`CI` workflow）结果，确保依赖安装 + `compileall` + 打包干跑全部通过
- 若出现热补丁，务必在 `CHANGELOG.md` 补充 `hotfix` 记录

---

Happy shipping!
