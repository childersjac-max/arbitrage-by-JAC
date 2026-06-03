@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -r requirements-app.txt -q
echo.
echo Remote mode: public URL for your phone on cellular or any Wi-Fi.
echo A login password is required. Creating/updating .env if needed...
echo.
python scripts\enable_remote.py --if-missing
if errorlevel 1 exit /b 1
echo.
python doctor.py
if errorlevel 1 (
  echo Fix Ollama first, then run this script again.
  pause
  exit /b 1
)
echo.
echo Starting app — copy the https://....gradio.live URL for your phone.
echo Your PC must stay on. Press Ctrl+C here to stop.
echo.
python web_app.py
pause
