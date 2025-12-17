#!/bin/bash
# Production start script for Render
# This script ensures proper startup in cloud environment

echo "🚀 Starting PRISM Backend..."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run database migrations/initialization if needed
if [ "$RUN_DB_INIT" = "true" ]; then
    echo "🗄️ Initializing database..."
    python db_init.py
fi

# Start the application with Gunicorn (production WSGI server)
echo "🔥 Starting Gunicorn server..."
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
