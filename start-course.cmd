@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please install the project virtual environment first. See course/README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m scripts.open_course
if errorlevel 1 pause
