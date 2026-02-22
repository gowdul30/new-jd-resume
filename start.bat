@echo off
SETLOCAL

echo ==========================================
echo  ResumeAI - Resume Tailor ^& ATS Scorer
echo ==========================================
echo.

:: Check if GROQ_API_KEY is set in .env
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and add your GROQ_API_KEY
    echo Get your free key at: https://console.groq.com
    pause
    exit /b 1
)

:: Navigate to backend directory
cd /d "%~dp0backend"

echo [1/3] Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed. Make sure Python 3.9+ is installed.
    echo Download Python at: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [2/3] Starting FastAPI server on http://localhost:8000
echo.
echo Press CTRL+C to stop the server.
echo.

python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0

pause
