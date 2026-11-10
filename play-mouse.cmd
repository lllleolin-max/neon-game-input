@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create .venv and install .[demo] first. See README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m neon_game_input.demo --mode mouse %*
if errorlevel 1 pause
