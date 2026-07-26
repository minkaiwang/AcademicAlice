本目录：安装与 Windows 打包
========================

- **install_deps.py** — 依赖安装与（可选）启动主程序；`--no-launch` 仅安装。
- **requirements.txt** — pip 依赖列表；仓库根目录的 `requirements.txt` 通过 `-r install/requirements.txt` 引用。
- **安装依赖.bat** — 在仓库根目录下调用上述脚本。
- **deskpet.spec** + **打包Windows.bat** + **read_py_exe.ps1** — 固定使用 PyInstaller 6.21.0 生成 `dist/AemeathDeskPet/`。spec 对 PyQt5 使用 `collect_all`，打包机须已 `pip install PyQt5`；正式包使用 CI 覆盖的 Python 3.11–3.13。发给他人时需 **整个 `AemeathDeskPet` 文件夹** zip 解压后运行其中 exe，对方 **无需安装 Python**。
- 打包脚本通过 PowerShell 读取仓库根目录 UTF-8 `py.ini` 中的 `python_executable`（与「安装依赖」写入的一致），避免 CMD 嵌套 `for` / 路径含 `)` / 编码问题；勿单独删掉 `read_py_exe.ps1`。

根目录仍提供 **安装依赖.bat**、**打包Windows.bat** 快捷方式，内部会 `call` 本目录下同名脚本。
