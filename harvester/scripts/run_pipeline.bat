@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt 2>nul
if not exist ".env" copy .env.example .env
python cli.py %*
