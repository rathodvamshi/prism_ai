"""
Database initialization script for PRISM AI Studio
Creates indexes for optimal performance across all collections
"""

import asyncio
import logging
from app.db.mongo_client import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """Create all necessary indexes for optimal database performance"""
    
    try:
        # Users Collection Indexes
        users_collection = db.users
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("user_id")
        await users_collection.create_index("verified")
        await users_collection.create_index("isFirstLoginCompleted")
        logger.info("✅ Created indexes for users collection")
        
        # Chat Sessions Collection Indexes  
        sessions_collection = db.chat_sessions
        await sessions_collection.create_index("sessionId", unique=True)
        await sessions_collection.create_index("user_id")
        await sessions_collection.create_index([("user_id", 1), ("updatedAt", -1)])
        await sessions_collection.create_index("isActive")
        await sessions_collection.create_index("updatedAt")
        logger.info("✅ Created indexes for chat_sessions collection")
        
        # User Tasks Collection Indexes
        tasks_collection = db.user_tasks
        await tasks_collection.create_index("taskId", unique=True)
        await tasks_collection.create_index("user_id")
        await tasks_collection.create_index([("user_id", 1), ("status", 1)])
        await tasks_collection.create_index([("user_id", 1), ("createdAt", -1)])
        await tasks_collection.create_index("status")
        await tasks_collection.create_index("dueDate")
        logger.info("✅ Created indexes for user_tasks collection")
        
        # User Memory Collection Indexes
        memory_collection = db.user_memory
        await memory_collection.create_index("id", unique=True)
        await memory_collection.create_index("user_id")
        await memory_collection.create_index([("user_id", 1), ("importance", -1), ("timestamp", -1)])
        await memory_collection.create_index("type")
        await memory_collection.create_index("importance")
        await memory_collection.create_index("timestamp")
        logger.info("✅ Created indexes for user_memory collection")
        
        # Message Highlights Collection Indexes
        highlights_collection = db.message_highlights
        await highlights_collection.create_index("highlightId", unique=True)
        await highlights_collection.create_index("uniqueKey", unique=True)
        await highlights_collection.create_index("sessionId")
        await highlights_collection.create_index("messageId")
        # Compound indexes for faster queries
        await highlights_collection.create_index([("sessionId", 1), ("user_id", 1)])
        await highlights_collection.create_index([("sessionId", 1), ("userId", 1)])  # Alternative field name
        await highlights_collection.create_index([("messageId", 1), ("sessionId", 1)])
        await highlights_collection.create_index("user_id")
        await highlights_collection.create_index("userId")
        logger.info("✅ Created indexes for message_highlights collection")
        
        # Mini-Agent Threads Collection Indexes
        miniagent_collection = db.miniagent_threads
        # Using mini_agents collection which is the actual collection name
        mini_agents_collection = db.mini_agents
        await mini_agents_collection.create_index("agentId", unique=True)
        await mini_agents_collection.create_index("messageId")
        await mini_agents_collection.create_index("sessionId")
        # Compound indexes for fastest query performance
        await mini_agents_collection.create_index([("sessionId", 1), ("user_id", 1)])
        await mini_agents_collection.create_index([("sessionId", 1), ("userId", 1)])  # Alternative field name
        await mini_agents_collection.create_index([("messageId", 1), ("sessionId", 1)])
        await mini_agents_collection.create_index([("agentId", 1), ("user_id", 1)])
        await mini_agents_collection.create_index([("agentId", 1), ("userId", 1)])
        await mini_agents_collection.create_index("user_id")
        await mini_agents_collection.create_index("userId")
        await mini_agents_collection.create_index([("user_id", 1), ("updatedAt", -1)])
        await mini_agents_collection.create_index([("userId", 1), ("updatedAt", -1)])
        await mini_agents_collection.create_index("updatedAt")
        logger.info("✅ Created indexes for mini_agents collection")
        
        # Shared Conversations Collection Indexes
        shares_collection = db.shared_conversations
        await shares_collection.create_index("shareId", unique=True)
        await shares_collection.create_index("user_id")
        await shares_collection.create_index("createdAt")
        await shares_collection.create_index("accessCount")
        logger.info("✅ Created indexes for shared_conversations collection")
        
        logger.info("🎉 All database indexes created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {str(e)}")
        raise


async def verify_indexes():
    """Verify all indexes were created correctly"""
    
    collections = [
        "users",
        "chat_sessions", 
        "user_tasks",
        "user_memory",
        "message_highlights",
        "miniagent_threads",
        "shared_conversations"
    ]
    
    for collection_name in collections:
        collection = db[collection_name]
        indexes = await collection.list_indexes().to_list(length=None)
        
        logger.info(f"📊 {collection_name} has {len(indexes)} indexes:")
        for index in indexes:
            logger.info(f"   - {index['name']}: {index.get('key', 'N/A')}")
    
    logger.info("✅ Index verification complete")


async def main():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization...")
    
    await create_indexes()
    await verify_indexes()
    
    logger.info("✨ Database initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
