@echo off
title Local LLM - Architect (easy mode)
cd /d "%~dp0\.."
set "REPO_ROOT=%cd%\.."
if exist "%REPO_ROOT%\.git" (
  echo Syncing latest local-llm scripts...
  cd /d "%REPO_ROOT%"
  git pull origin cursor/local-llm-normalization-4fea 2>nul
  cd /d "%~dp0\.."
)

echo.
echo ============================================
echo   ARCHITECT MODE - Big prompt, easy run
echo ============================================
echo.
echo 1. Make sure Ollama is open (Start menu)
echo 2. Edit your prompt in Notepad (opening next) if needed
echo 3. Save Notepad, close this window's wait, then AI runs automatically
echo.

set PROMPT_FILE=%cd%\prompts\mega_prompt.txt
if not exist "%PROMPT_FILE%" (
  echo Creating prompts\mega_prompt.txt ...
  mkdir prompts 2>nul
  echo Describe your project here.> "%PROMPT_FILE%"
)

echo Opening prompt file for editing...
echo    %PROMPT_FILE%
start /wait notepad "%PROMPT_FILE%"

if not exist ".venv\Scripts\activate.bat" (
  echo Creating Python environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt 2>nul

echo.
echo Checking Ollama...
curl -sf http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Ollama is not running.
  echo Open Ollama from the Start menu, wait 30 seconds, run this script again.
  pause
  exit /b 1
)

echo.
echo Running Architect (this takes several minutes)...
echo Output will be saved to: harvester\generated\
echo.

python run_architect_easy.py
if errorlevel 1 (
  echo.
  echo ============================================
  echo   FAILED - see error above
  echo   If errors persist, in Git Bash: git pull origin cursor/local-llm-normalization-4fea
  echo ============================================
  pause
  exit /b 1
)

echo.
echo ============================================
echo   DONE - check harvester\generated\ folder
echo ============================================
echo.
pause
