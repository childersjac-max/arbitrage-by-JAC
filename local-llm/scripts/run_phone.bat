@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -r requirements-app.txt -q
set LOCAL_LLM_UI_LAN=1
echo.
echo Starting chat for PHONE access (same Wi-Fi as this PC)...
echo The app will print a URL like http://192.168.x.x:7860 — open that on your phone.
echo Your PC must stay on with Ollama and this window running.
echo.
python doctor.py
if errorlevel 1 (
  echo Fix Ollama first, then run this script again.
  pause
  exit /b 1
)
python web_app.py
pause
