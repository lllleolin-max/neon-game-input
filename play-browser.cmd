@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create .venv and install .[browser] first. See README.md.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8765 in your browser.
".venv\Scripts\python.exe" -m neon_game_input.web --mode mouse %*
if errorlevel 1 pause
