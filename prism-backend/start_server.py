#!/usr/bin/env python3
"""
Simple startup script for the PRISM backend server.
This script adds the current directory to Python path and starts uvicorn.
"""

import sys
import os
import logging

# =============================================================================
# 🔇 SUPPRESS NOISY LIBRARY LOGS FIRST (before any imports)
# =============================================================================
# PyMongo background threads cause WinError 10060 NetworkTimeout on Windows
# These are non-fatal but spam logs - silence them at CRITICAL level only
# =============================================================================
for noisy_logger in [
    'pymongo', 'pymongo.pool', 'pymongo.topology', 'pymongo.connection',
    'pymongo.serverSelection', 'pymongo.command', 'pymongo.monitor', 'motor',
    'httpcore', 'httpx', 'urllib3', 'asyncio', 'watchfiles',
]:
    logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)

import uvicorn

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Added {current_dir} to Python path")
print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries

# Check if we can import sendgrid (should be available in venv)
try:
    import sendgrid
    print("✓ sendgrid module is available")
except ImportError as e:
    print(f"✗ sendgrid not available: {e}")
    print("Make sure you're running from the virtual environment")
    print("Run: .venv\\Scripts\\activate")
    sys.exit(1)

try:
    from app.main import app
    print("Successfully imported app.main")
    
    # Start the server
    print("Starting server on http://127.0.0.1:8002")
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8002, 
        reload=True,
        log_level="info"
    )
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Current working directory:", os.getcwd())
    print("Contents of current directory:", os.listdir("."))
    if os.path.exists("app"):
        print("Contents of app directory:", os.listdir("app"))
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)