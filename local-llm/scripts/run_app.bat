@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -r requirements-app.txt
echo.
echo For BIG prompts: double-click scripts\run_architect_easy.bat instead.
echo If Ollama is not running, start scripts\start_ollama.bat first.
echo.
echo Running doctor (Ollama check)...
python doctor.py
if errorlevel 1 (
  echo.
  echo Fix Ollama first: scripts\start_ollama.bat  then  ollama pull YOUR_MODEL
  pause
  exit /b 1
)
echo.
echo Starting Private Local LLM CHAT app...
echo Open http://127.0.0.1:7860  (NOT harvester :8765)
echo.
python web_app.py
pause
