@echo off
REM Auto-Restart Celery Worker Script for Windows
REM This script automatically restarts the worker if it crashes or encounters errors
REM Production-ready with exponential backoff on restart failures

setlocal enabledelayedexpansion

set MAX_RESTARTS=10
set RESTART_DELAY=5
set RESTART_COUNT=0
set BACKOFF_MULTIPLIER=1

echo ========================================
echo Celery Worker Auto-Restart Wrapper
echo ========================================
echo Max Restarts: %MAX_RESTARTS%
echo Initial Delay: %RESTART_DELAY% seconds
echo ========================================
echo.

:start_worker
set /a RESTART_COUNT+=1

if !RESTART_COUNT! GTR %MAX_RESTARTS% (
    echo.
    echo ========================================
    echo ERROR: Maximum restart attempts reached
    echo ========================================
    echo Worker has been restarted %MAX_RESTARTS% times.
    echo Please check logs and fix the underlying issue.
    echo.
    pause
    exit /b 1
)

if !RESTART_COUNT! GTR 1 (
    echo.
    echo ========================================
    echo Restarting Worker (Attempt !RESTART_COUNT! / %MAX_RESTARTS%)
    echo ========================================
    set /a DELAY=!RESTART_DELAY! * !BACKOFF_MULTIPLIER!
    echo Waiting !DELAY! seconds before restart...
    timeout /t !DELAY! /nobreak >nul
    set /a BACKOFF_MULTIPLIER*=2
    if !BACKOFF_MULTIPLIER! GTR 32 set BACKOFF_MULTIPLIER=32
)

echo.
echo ========================================
echo Starting Celery Worker...
echo ========================================
echo Queue: email, default
echo Timezone: Asia/Kolkata (IST)
echo Platform: Windows (using solo pool)
echo Restart Count: !RESTART_COUNT!
echo ========================================
echo.

REM Start Celery worker with error handling
celery -A app.core.celery_app worker --loglevel=info --queues=email,default --pool=solo

REM Check exit code
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% EQU 0 (
    echo.
    echo Worker exited normally (exit code 0)
    echo No restart needed.
    pause
    exit /b 0
)

echo.
echo ========================================
echo Worker exited with error code: %EXIT_CODE%
echo ========================================
echo Worker will be restarted automatically...
echo.

REM Reset backoff if we had a successful run before
if !RESTART_COUNT! EQU 1 (
    set BACKOFF_MULTIPLIER=1
)

goto start_worker
