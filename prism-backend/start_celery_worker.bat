@echo off
REM Start Celery Worker for PRISM Email Tasks
REM This worker processes scheduled email reminders
REM Windows-compatible: Uses 'solo' pool (single-threaded)

echo ========================================
echo Starting Celery Worker for PRISM...
echo ========================================
echo Queue: email, default
echo Timezone: Asia/Kolkata (IST)
echo Platform: Windows (using solo pool)
echo ========================================
echo.

REM Windows requires 'solo' pool (prefork doesn't work on Windows)
celery -A app.core.celery_app worker --loglevel=info --queues=email,default --pool=solo

pause
