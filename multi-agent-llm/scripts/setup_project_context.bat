@echo off
cd /d "%~dp0\.."
if not exist .env copy /Y .env.example .env
echo.
echo 1. Start local-llm once:  cd ..\local-llm ^& python web_app.py
echo 2. Copy lines from ..\local-llm\data\app_urls.txt into multi-agent-llm\.env
echo 3. Set PROJECT_ROOT to your repo path in .env
echo.
echo See SETUP_PROJECT_CONTEXT.md
pause
