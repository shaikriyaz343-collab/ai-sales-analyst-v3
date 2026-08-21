@echo off
setlocal
cd /d "%~dp0"

echo Installing/updating application dependencies...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo.
echo Starting AI Business Analyst...
py -m streamlit run app.py
pause
