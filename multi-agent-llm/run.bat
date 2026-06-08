@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python multi_agent_runner.py %*
pause
