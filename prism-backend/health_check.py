#!/usr/bin/env python3
"""
🔍 Health check script for Render deployment
Tests all critical system components
"""
import asyncio
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_database_connections():
    """Check MongoDB and Redis connections"""
    try:
        # Test MongoDB
        from app.db.mongo_client import db
        await db.command("ping")
        logger.info("✅ MongoDB connection: OK")
        
        # Test Redis/Celery
        from app.core.celery_app import celery_app
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        if stats:
            logger.info("✅ Celery/Redis connection: OK")
        else:
            logger.warning("⚠️ Celery broker connection: No workers found")
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    
    return True

async def check_external_services():
    """Check external API connections"""
    try:
        import os
        
        # Check environment variables
        required_apis = ['GROQ_API_KEY', 'SENDGRID_API_KEY', 'PINECONE_API_KEY']
        for api in required_apis:
            if os.getenv(api):
                logger.info(f"✅ {api}: Configured")
            else:
                logger.warning(f"⚠️ {api}: Not configured")
        
    except Exception as e:
        logger.error(f"❌ External services check failed: {e}")
        return False
    
    return True

async def main():
    """Run all health checks"""
    logger.info(f"🔍 Starting health check at {datetime.now()}")
    
    checks = [
        ("Database Connections", check_database_connections()),
        ("External Services", check_external_services())
    ]
    
    all_passed = True
    for name, check in checks:
        try:
            result = await check
            if not result:
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {name} check failed: {e}")
            all_passed = False
    
    if all_passed:
        logger.info("🎉 All health checks passed!")
        return 0
    else:
        logger.error("🚨 Some health checks failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)