@echo off
setlocal EnableDelayedExpansion
REM UTF-8 BOM + chcp 65001 breaks cmd line parsing on many setups; keep this file ASCII-only.
cd /d "%~dp0.."

echo.
echo === AcademicAlice / deskpet - Windows pack (PyInstaller onedir) ===
echo Uses python_executable from py.ini when present; else py -3 or python from PATH.
echo.

set "PY_EXE="

REM Read python_executable from UTF-8 py.ini via read_py_exe.ps1 (avoids nested FOR / paths with ") / Base64 ending == breaking cmd).
if exist py.ini (
  for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0read_py_exe.ps1" -ProjectRoot "%CD%"`) do set "PY_EXE=%%I"
)

if defined PY_EXE (
  if exist "!PY_EXE!" (
    "!PY_EXE!" -c "import PyQt5.QtWidgets" 2>nul
    if not errorlevel 1 goto :have_py
  )
  set "PY_EXE="
)

where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 -c "import PyQt5.QtWidgets" 2>nul
  if not errorlevel 1 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%I"
    goto :have_py
  )
)

python -c "import PyQt5.QtWidgets" 2>nul
if not errorlevel 1 (
  for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%I"
  goto :have_py
)

echo [ERROR] PyQt5 not found for any interpreter.
echo Run install_deps / pin python in py.ini, then:
echo   "path\to\python.exe" -m pip install -r requirements.txt
pause
exit /b 1

:have_py
echo [INFO] Using Python: !PY_EXE!
echo.

"!PY_EXE!" -m pip install "pyinstaller>=6" -q
if errorlevel 1 (
  echo [ERROR] pip install pyinstaller failed.
  pause
  exit /b 1
)

"!PY_EXE!" -m PyInstaller --noconfirm "%~dp0deskpet.spec"
if errorlevel 1 (
  echo [ERROR] PyInstaller failed. See log above.
  pause
  exit /b 1
)

echo.
echo [DONE] Zip folder dist\AcademicAlice and share. Run AcademicAlice.exe inside it.
echo Logs go to logs\ next to the exe after first successful run.
echo.
pause
