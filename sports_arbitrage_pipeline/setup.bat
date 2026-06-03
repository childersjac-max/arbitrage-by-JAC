@echo off
cd /d "%~dp0"
echo Creating venv and installing dependencies...
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo On Git Bash, activate with:
echo   source venv/Scripts/activate
echo   OR:  source activate_venv.sh
echo.
echo Run bootstrap for harvester clone:
echo   bash bootstrap.sh
pause
