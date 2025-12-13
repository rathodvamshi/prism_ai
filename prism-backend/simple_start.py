#!/usr/bin/env python3
"""
Simple server startup script for development
Runs the server with basic configuration, optional external services
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    print("🚀 Starting PRISM AI Backend Server...")
    print("📍 Mode: Development (Basic Configuration)")
    print("🔗 Backend will be available at: http://127.0.0.1:8000")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    print("⚡ Health Check: http://127.0.0.1:8000/health")
    
    try:
        # Import and run the app
        from app.main import app
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()