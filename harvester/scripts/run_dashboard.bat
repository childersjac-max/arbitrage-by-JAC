@echo off
title Live Arbitrage Finder
cd /d "%~dp0\.."

if not exist ".venv\Scripts\activate.bat" (
  echo Creating Python environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt 2>nul

if not exist ".env" (
  echo Copying .env.example to .env — add your ODDS_API_KEY
  copy .env.example .env
)

echo.
echo  Live Arbitrage Finder
echo  Open in browser: http://127.0.0.1:8765
echo  Press Ctrl+C to stop
echo.

python web_app.py
pause
