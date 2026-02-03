"""
Database initialization script for PRISM AI Studio
Creates indexes for optimal performance across all collections
"""

import asyncio
import logging
from pymongo.errors import OperationFailure
from app.db.mongo_client import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def safe_create_index(collection, keys, **kwargs):
    """Create index safely, ignoring if it already exists or has data conflicts"""
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as e:
        if e.code in [85, 11000]:  # IndexOptionsConflict or DuplicateKey
            logger.debug(f"Index skipped (exists or data conflict): {keys}")
        else:
            raise


async def create_indexes():
    """Create all necessary indexes for optimal database performance"""
    
    try:
        # Users Collection Indexes
        users_collection = db.users
        await safe_create_index(users_collection, "email", unique=True)
        await safe_create_index(users_collection, "user_id")
        await safe_create_index(users_collection, "verified")
        await safe_create_index(users_collection, "isFirstLoginCompleted")
        logger.info("✅ Created indexes for users collection")
        
        # Chat Sessions Collection Indexes  
        sessions_collection = db.sessions
        await safe_create_index(sessions_collection, "sessionId", unique=True)
        await safe_create_index(sessions_collection, "user_id")
        await safe_create_index(sessions_collection, [("user_id", 1), ("updatedAt", -1)])
        await safe_create_index(sessions_collection, "isActive")
        await safe_create_index(sessions_collection, "updatedAt")
        logger.info("✅ Created indexes for sessions collection")
        
        # User Tasks Collection Indexes
        tasks_collection = db.user_tasks
        await safe_create_index(tasks_collection, "taskId", unique=True)
        await safe_create_index(tasks_collection, "userId")
        await safe_create_index(tasks_collection, [("userId", 1), ("status", 1)])
        await safe_create_index(tasks_collection, [("userId", 1), ("due_date", 1)])
        await safe_create_index(tasks_collection, [("userId", 1), ("description", 1), ("status", 1), ("due_date", 1)])
        await safe_create_index(tasks_collection, "status")
        await safe_create_index(tasks_collection, "due_date")
        await safe_create_index(tasks_collection, "email_status")
        logger.info("✅ Created indexes for tasks collection")
        
        # User Memory Collection Indexes
        memory_collection = db.memory
        await safe_create_index(memory_collection, "userId")
        await safe_create_index(memory_collection, [("userId", 1), ("importance", -1)])
        await safe_create_index(memory_collection, "type")
        logger.info("✅ Created indexes for memory collection")
        
        # Message Highlights Collection Indexes
        highlights_collection = db.message_highlights
        await safe_create_index(highlights_collection, "highlightId", unique=True)
        await safe_create_index(highlights_collection, "sessionId")
        await safe_create_index(highlights_collection, "messageId")
        await safe_create_index(highlights_collection, [("sessionId", 1), ("userId", 1)])
        await safe_create_index(highlights_collection, "userId")
        logger.info("✅ Created indexes for message_highlights collection")
        
        # Mini-Agent Collection Indexes
        mini_agents_collection = db.mini_agents
        await safe_create_index(mini_agents_collection, "agentId", unique=True)
        await safe_create_index(mini_agents_collection, "messageId")
        await safe_create_index(mini_agents_collection, "sessionId")
        await safe_create_index(mini_agents_collection, [("sessionId", 1), ("userId", 1)])
        await safe_create_index(mini_agents_collection, "userId")
        await safe_create_index(mini_agents_collection, [("userId", 1), ("updatedAt", -1)])
        logger.info("✅ Created indexes for mini_agents collection")
        
        # 🔑 API Keys Collection Indexes (CRITICAL FOR BYOK SPEED)
        api_keys_collection = db.api_keys
        await safe_create_index(api_keys_collection, "user_id")
        await safe_create_index(api_keys_collection, [("user_id", 1), ("is_active", 1), ("priority", 1)])
        await safe_create_index(api_keys_collection, "key_hash", unique=True)
        await safe_create_index(api_keys_collection, [("user_id", 1), ("created_at", -1)])
        logger.info("✅ Created indexes for api_keys collection")
        
        # 📊 Usage Tracking Collection Indexes (CRITICAL FOR FREE LIMIT)
        usage_collection = db.usage_tracking
        await safe_create_index(usage_collection, "user_id", unique=True)
        await safe_create_index(usage_collection, [("user_id", 1), ("date", 1)])
        await safe_create_index(usage_collection, "date")
        logger.info("✅ Created indexes for usage_tracking collection")
        
        # 🔐 Auth Sessions Collection Indexes
        auth_sessions = db.auth_sessions
        await safe_create_index(auth_sessions, "session_id", unique=True)
        await safe_create_index(auth_sessions, "user_id")
        await safe_create_index(auth_sessions, "expires_at")
        await safe_create_index(auth_sessions, [("user_id", 1), ("expires_at", -1)])
        logger.info("✅ Created indexes for auth_sessions collection")
        
        logger.info("🎉 All database indexes created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {str(e)}")
        raise


async def main():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization...")
    await create_indexes()
    logger.info("✨ Database initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
