@echo off
SETLOCAL
TITLE ResumeAI_Server

:: Kill existing Python instances associated with this title (except current)
:: Note: This is a bit tricky in batch, but we can at least kill other python processes 
:: matching the uvicorn pattern if we want to be aggressive as requested.
echo [1/3] Cleaning up old instances...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM python3.11.exe /T >nul 2>&1

:: Navigate to backend directory
cd /d "%~dp0backend"

echo [2/3] Starting FastAPI server on http://localhost:8000
echo.
echo Press CTRL+C to stop the server.
echo.

python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0

pause
