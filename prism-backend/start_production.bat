@echo off
echo ============================================================================
echo   PRISM AI - Production Email System Startup
echo ============================================================================
echo.
echo Starting TWO processes:
echo   1. API Server (FastAPI) - Port 8000
echo   2. Email Worker (Background) - Handles all email sending
echo.
echo ============================================================================
echo.

REM Kill any existing processes
echo Cleaning up existing processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting API Server...
start "PRISM API Server" cmd /k "cd /d %~dp0 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Email Worker...
start "PRISM Email Worker" cmd /k "cd /d %~dp0 && python email_worker.py"

echo.
echo ============================================================================
echo   ✅ Both processes started successfully!
echo ============================================================================
echo.
echo   📊 API Server: http://localhost:8000
echo   📧 Email Worker: Running in background
echo.
echo   Press Ctrl+C in each window to stop
echo ============================================================================
echo.

pause
