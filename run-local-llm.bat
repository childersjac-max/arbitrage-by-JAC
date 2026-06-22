@echo off
REM Launch the Ollama CHAT app (Gradio :7860) — NOT the harvester dashboard (:8765).
cd /d "%~dp0local-llm"
if not exist "web_app.py" (
  echo ERROR: local-llm folder not found at %~dp0local-llm
  pause
  exit /b 1
)
call scripts\run_app.bat
