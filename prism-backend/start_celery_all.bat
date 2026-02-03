@echo off
REM Start Celery Worker + Beat for PRISM (Combined)
REM This starts both the worker and scheduler in a single process
REM Good for development/testing - for production, run them separately

echo ========================================
echo Starting Celery Worker + Beat for PRISM...
echo ========================================
echo Queues: email, default
echo Periodic Tasks:
echo   - Task recovery every 5 minutes
echo   - Health check every 2 minutes
echo Timezone: Asia/Kolkata (IST)
echo Platform: Windows (using solo pool)
echo ========================================
echo.

REM Windows requires 'solo' pool (prefork doesn't work on Windows)
REM -B flag embeds beat scheduler into worker
celery -A app.core.celery_app worker --loglevel=info --queues=email,default --pool=solo -B

pause
