@echo off
cd /d "%~dp0"
echo === Multi-agent LLM setup ===
where ollama >nul 2>&1
if errorlevel 1 (
  echo Install Ollama from https://ollama.com first.
  pause
  exit /b 1
)
if not exist .env if exist .env.example copy /Y .env.example .env
py -3.14 -m venv .venv 2>nul || python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Pull models manually in Git Bash:
echo   ollama pull qwen2.5-coder:7b-instruct-q4_K_M
echo   ollama pull qwen2.5:3b-instruct-q4_K_M
echo.
echo Then run:  run.bat
pause
