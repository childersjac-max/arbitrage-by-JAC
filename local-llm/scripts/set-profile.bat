@echo off
cd /d "%~dp0\.."
if "%1"=="" (
  python scripts\set_profile.py balanced
) else (
  python scripts\set_profile.py %1
)
pause
