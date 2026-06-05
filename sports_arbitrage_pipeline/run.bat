@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
  echo Run bootstrap first:  bash bootstrap.sh
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
python arbitrage_orchestrator.py %*
pause
