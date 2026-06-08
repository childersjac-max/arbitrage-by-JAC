@echo off
cd /d "%~dp0"
if exist "sports_arbitrage_pipeline\arbitrage_orchestrator.py" (
  cd sports_arbitrage_pipeline
  if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat
  python arbitrage_orchestrator.py %*
) else (
  python arbitrage_orchestrator.py %*
)
