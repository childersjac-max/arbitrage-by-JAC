@echo off
cd /d "%~dp0\.."
echo Switching chat to Balanced (3B) — fixes Quality/7B timeouts on CPU...
call .venv\Scripts\activate.bat 2>nul
python scripts\set_profile.py balanced
echo.
echo Pull the Balanced model if needed:
echo   ollama pull qwen2.5:3b-instruct-q4_K_M
echo.
echo Restart: python web_app.py
echo In the UI select: Balanced (not Quality)
pause
