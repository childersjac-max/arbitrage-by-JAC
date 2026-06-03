@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
  echo Run bootstrap first:  bash bootstrap.sh
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
echo Installing Playwright...
pip install -r requirements-playwright.txt
echo.
echo Downloading Chromium (headless browser)...
python -m playwright install chromium
echo.
python -m playwright --version
echo Done.
pause
