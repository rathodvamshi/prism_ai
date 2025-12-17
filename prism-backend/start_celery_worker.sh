#!/bin/bash
# Start Celery Worker for PRISM Email Tasks
# This worker processes scheduled email reminders
# Unix/Linux/Mac compatible: Uses 'prefork' pool (multi-process)

echo "========================================"
echo "Starting Celery Worker for PRISM..."
echo "========================================"
echo "Queue: email, default"
echo "Timezone: Asia/Kolkata (IST)"
echo "Platform: Unix-like (using prefork pool)"
echo "========================================"
echo ""

# Unix-like systems can use prefork (multi-process)
celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=4
