@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create .venv and install .[neon,demo] first. See README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m neon_game_input.demo --mode neon --fullscreen %*
if errorlevel 1 pause
