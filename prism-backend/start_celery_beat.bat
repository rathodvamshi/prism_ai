@echo off
REM Start Celery Beat Scheduler for PRISM Periodic Tasks
REM This scheduler triggers periodic recovery and health check tasks
REM Run this ALONGSIDE the Celery worker (in separate terminal)

echo ========================================
echo Starting Celery Beat for PRISM...
echo ========================================
echo Periodic Tasks:
echo   - Task recovery every 5 minutes
echo   - Health check every 2 minutes
echo Timezone: Asia/Kolkata (IST)
echo ========================================
echo.

celery -A app.core.celery_app beat --loglevel=info

pause
