@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run install.cmd first.
  pause
  exit /b 1
)
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
.venv\Scripts\python.exe -m streamlit run confluence-rag\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
pause
