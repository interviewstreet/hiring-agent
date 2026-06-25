@echo off
echo Starting Hiring Agent...

:: Activate the virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Make sure you ran 'python -m venv .venv' and installed requirements.
    pause
    exit /b
)

:: Wait a second for the server to be ready before opening the browser
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

:: Run the local web server
python app.py

pause
