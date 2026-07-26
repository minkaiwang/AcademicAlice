# Release Playbook

> 当前版本以 `config/version_info.py` 为准。正式打 Tag、上传附件和发布 Release
> 都是外部不可逆动作，必须在完成本清单后由维护者最终确认。

## 1. Pre-flight checklist

1. **Set the version**  
   - Update user-facing text (`README.md`, `CHANGELOG.md`, installer banner if required).  
   - Bump default tag in `scripts/package_release.py` if the marketing codename changes.
2. **许可证关卡**
   - 核对 `THIRD_PARTY_NOTICES.md`、`ACKNOWLEDGMENTS.md` 与所有随包许可证。
   - `LICENSE-ASSETS` 当前限制公开再分发；没有权利人书面授权时不得发布含受限素材的公开包。
   - `services/yuanbao-free-api/` 的上游缺少独立许可证正文；取得完整许可/版权通知前不得把它当作已清关组件。
3. **Regenerate docs**  
   ```powershell
   python scripts/generate_doc_portal.py
   ```
   Validate `AA使用必读.html`，确保贡献列表与 DOC 区卡片已随 `doc/` 刷新。
4. **自动检查**
   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   .venv\Scripts\python.exe -m compileall -q config lib install scripts services tests
   .venv\Scripts\python.exe -m ruff check --select E9,F63,F7,F82,F841 config lib install scripts services tests
   .venv\Scripts\python.exe -m pytest
   .venv\Scripts\python.exe -m pip_audit -r services/yuanbao-free-api/requirements.txt --progress-spinner off --strict
   # pyncm 的 PyPI 项目当前不可查询；本地 wheel SHA256 由 pytest 验证
   .venv\Scripts\python.exe -m pip_audit -r install/requirements.txt --progress-spinner off
   .venv\Scripts\python.exe scripts/check_build_environment.py
   .venv\Scripts\python.exe scripts/check_brand_strings.py
   # 正式干跑要求 Git 工作树干净
   python scripts/package_release.py --dry-run
   python scripts/package_green_release.py --dry-run
   ```
   本地审查尚未提交的改动时可显式加 `--allow-dirty`；正式发布禁止使用该参数。
5. **Runtime smoke**  
   Launch `python lib/core/qt_desktop_pet.py` once, verify：  
   - AI 模式（OpenAI/Ollama）能初始化；  
   - 音乐（任选 `netease/qq/kugou`）能搜索/播放；  
   - 粒子与对象命令（`#雪豹/#沙发/...`）可生成并清理；  
   - GSVmove / STT（若启用）可以启动且不会阻塞退出。

## 2. Build artifacts

```powershell
python scripts/package_release.py --version LTS1.0.5pre2
python scripts/package_green_release.py --version LTS1.0.5pre2
```

- 源码包：`dist/AemeathDeskPet-LTS1.0.5pre2.zip`
- 绿色包：`dist/AemeathDeskPet-LTS1.0.5pre2-green.zip`
- 两者各自生成 `*-manifest.json` 和与 ZIP 同名的 `*.zip.sha256`
- 清单排除 `build/`、`dist/`、日志、用户数据、备份和临时文件；源码包还排除模型/浏览器运行时
- ZIP 使用固定时间戳与文件属性，输入文件一致时可得到稳定字节

## 3. GitHub release

**仓库：** <https://github.com/minkaiwang/AemeathDeskPet>（`config/version_info.py` → `GITHUB_REPO = "minkaiwang/AemeathDeskPet"`）

发布前运行品牌检查：

```powershell
python scripts/check_brand_strings.py
python scripts/generate_doc_portal.py
```

1. 创建 Tag（例如 `git tag -a LTS1.0.5pre2 -m "爱弥斯 LTS1.0.5pre2"`，`git push origin LTS1.0.5pre2`）
2. 新建 Release：**标题** 使用 **爱弥斯**（勿用旧名「学术爱丽丝」），与 `app_brand.py` 一致
3. Release Notes：**全文复制** 根目录 [`RELEASE_NOTES_LTS1.0.5pre2.md`](RELEASE_NOTES_LTS1.0.5pre2.md)（或 `CHANGELOG.md` 对应段落），并核对绿色包名为 **`AemeathDeskPet`** / **`AemeathDeskPet.exe`**
4. 确认 `LTS1.0.5pre2` 仍标记为预发布，并再次核对本手册中的许可关卡；未清关时只合并源代码，不创建公开 Release
5. 附件必须精确命名，否则应用内更新器会拒绝：
   - `dist/AemeathDeskPet-LTS1.0.5pre2.zip`
   - `dist/AemeathDeskPet-LTS1.0.5pre2.zip.sha256`
   - 可选 `dist/AemeathDeskPet-LTS1.0.5pre2-green.zip`
   - 对应 `dist/AemeathDeskPet-LTS1.0.5pre2-green.zip.sha256`
   - 对应 manifest 与 `AA使用必读.html`

## 4. Post-release

- 在 `doc/迁移清单任务.txt` 更新阶段进度
- 如涉及凭据变更，说明 Windows DPAPI 迁移/清除路径；不得要求用户把密钥写回 Python 源码
- 观察 GitHub Actions CI（`CI` workflow）结果，确保依赖安装 + `compileall` + 打包干跑全部通过
- 若出现热补丁，务必在 `CHANGELOG.md` 补充 `hotfix` 记录

---

Happy shipping!
