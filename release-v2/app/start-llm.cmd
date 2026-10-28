@echo off
setlocal
cd /d "%~dp0"
tools\llama-b11787-bin-win-cpu-x64\llama-server.exe --model models\Qwen3.5-2B-Q4_K_M.gguf --alias qwen3.5-2b-rag --host 127.0.0.1 --port 8080 --ctx-size 4096 --parallel 1 --n-gpu-layers 0 --reasoning off
pause
