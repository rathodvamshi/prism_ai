#!/usr/bin/env python3
"""
🚀 Production startup script for Render deployment
Ensures proper initialization and health checks
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'MONGO_URI',
        'CELERY_BROKER_URL',
        'SENDGRID_API_KEY',
        'GROQ_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def main():
    """Main startup function"""
    logger.info("🚀 Starting PRISM Backend API...")
    
    # Change to app directory
    app_dir = Path(__file__).parent
    os.chdir(app_dir)
    logger.info(f"📁 Working directory: {os.getcwd()}")
    
    # Check environment
    if not check_environment():
        logger.error("🔥 Environment check failed. Exiting.")
        sys.exit(1)
    
    # Import and start the app
    try:
        from app.main import app
        logger.info("✅ FastAPI app imported successfully")
        
        # Get port from environment
        port = int(os.getenv('PORT', 8000))
        logger.info(f"🌐 Server will start on port {port}")
        
        return app
        
    except Exception as e:
        logger.error(f"❌ Failed to import app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    app = main()