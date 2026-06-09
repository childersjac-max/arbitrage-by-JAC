@echo off
cd /d "%~dp0\.."
echo Installing local-llm into %CD%

if not exist ".venv\Scripts\activate.bat" (
  echo Creating .venv ...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-app.txt
echo.
echo Done. Start chat with: scripts\run_app.bat
echo Or: .venv\Scripts\activate ^&^& python web_app.py
pause
