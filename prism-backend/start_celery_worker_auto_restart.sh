#!/bin/bash
# Auto-Restart Celery Worker Script for Unix/Linux/Mac
# This script automatically restarts the worker if it crashes or encounters errors
# Production-ready with exponential backoff on restart failures

set -e

MAX_RESTARTS=10
RESTART_DELAY=5
RESTART_COUNT=0
BACKOFF_MULTIPLIER=1

echo "========================================"
echo "Celery Worker Auto-Restart Wrapper"
echo "========================================"
echo "Max Restarts: $MAX_RESTARTS"
echo "Initial Delay: $RESTART_DELAY seconds"
echo "========================================"
echo ""

start_worker() {
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    if [ $RESTART_COUNT -gt $MAX_RESTARTS ]; then
        echo ""
        echo "========================================"
        echo "ERROR: Maximum restart attempts reached"
        echo "========================================"
        echo "Worker has been restarted $MAX_RESTARTS times."
        echo "Please check logs and fix the underlying issue."
        echo ""
        exit 1
    fi
    
    if [ $RESTART_COUNT -gt 1 ]; then
        echo ""
        echo "========================================"
        echo "Restarting Worker (Attempt $RESTART_COUNT / $MAX_RESTARTS)"
        echo "========================================"
        DELAY=$((RESTART_DELAY * BACKOFF_MULTIPLIER))
        echo "Waiting $DELAY seconds before restart..."
        sleep $DELAY
        BACKOFF_MULTIPLIER=$((BACKOFF_MULTIPLIER * 2))
        if [ $BACKOFF_MULTIPLIER -gt 32 ]; then
            BACKOFF_MULTIPLIER=32
        fi
    fi
    
    echo ""
    echo "========================================"
    echo "Starting Celery Worker..."
    echo "========================================"
    echo "Queue: email, default"
    echo "Timezone: Asia/Kolkata (IST)"
    echo "Platform: Unix-like (using prefork pool)"
    echo "Restart Count: $RESTART_COUNT"
    echo "========================================"
    echo ""
    
    # Start Celery worker with error handling
    celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=4 || EXIT_CODE=$?
    
    if [ ${EXIT_CODE:-0} -eq 0 ]; then
        echo ""
        echo "Worker exited normally (exit code 0)"
        echo "No restart needed."
        exit 0
    fi
    
    echo ""
    echo "========================================"
    echo "Worker exited with error code: ${EXIT_CODE:-1}"
    echo "========================================"
    echo "Worker will be restarted automatically..."
    echo ""
    
    # Reset backoff if we had a successful run before
    if [ $RESTART_COUNT -eq 1 ]; then
        BACKOFF_MULTIPLIER=1
    fi
    
    start_worker
}

# Trap signals for graceful shutdown
trap 'echo "Received shutdown signal, stopping worker..."; exit 0' SIGTERM SIGINT

# Start the worker loop
start_worker
