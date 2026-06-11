@echo off
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set INJECT_FILE_MAP=0
python run_phases.py %*
