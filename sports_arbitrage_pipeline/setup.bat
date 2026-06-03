@echo off
cd /d "%~dp0"
if not exist "..\harvester\arbitrage_orchestrator.py" (
  echo ERROR: ..\harvester\ not found.
  echo Clone the FULL repo:
  echo   git clone https://github.com/childersjac-max/arbitrage-by-JAC.git
  echo   cd arbitrage-by-JAC\sports_arbitrage_pipeline
  echo   setup.bat
  exit /b 1
)
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist "..\harvester\.env" if exist ".env.example" copy /Y .env.example ..\harvester\.env
echo.
echo Edit ..\harvester\.env and set ODDS_API_KEY
echo Then:  venv\Scripts\activate.bat
echo        python arbitrage_orchestrator.py
pause
