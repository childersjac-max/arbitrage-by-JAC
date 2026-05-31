@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements-app.txt
echo.
echo If Ollama is not running, start scripts\start_ollama.bat first.
echo.
echo Starting Private Local LLM app...
echo Open http://127.0.0.1:7860 in your browser if it does not open automatically.
echo.
python web_app.py
pause
