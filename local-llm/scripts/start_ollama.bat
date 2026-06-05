@echo off
echo Starting Ollama...
if exist "%LOCALAPPDATA%\Programs\Ollama\Ollama.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\Ollama.exe"
) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
) else (
  echo Ollama not found. Install from https://ollama.com/download
  pause
  exit /b 1
)
echo Wait 5 seconds, then test: curl http://127.0.0.1:11434/api/tags
timeout /t 5 /nobreak >nul
pause
