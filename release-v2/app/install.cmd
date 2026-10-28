@echo off
setlocal
cd /d "%~dp0"
py -3.11 -c "import struct; assert struct.calcsize('P') == 8, 'Python x64 required'"
if errorlevel 1 goto fail
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 goto fail
if exist "wheelhouse" (
  .venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-lock.txt
) else (
  .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto fail
echo Installation complete. Run start-llm.cmd, then start-app.cmd.
pause
exit /b 0
:fail
echo Installation failed. Install Python 3.11 x64 and check the error above.
pause
exit /b 1
