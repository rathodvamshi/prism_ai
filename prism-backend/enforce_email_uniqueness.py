"""
🔒 ENFORCE EMAIL UNIQUENESS - DATABASE LEVEL
============================================

This script ensures MongoDB unique index on email field.

🎯 PURPOSE:
- Add unique constraint to users.email field
- Prevent duplicate user creation at database level
- Validate no existing duplicates

⚠️ RUN THIS ONCE during system setup/migration
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def enforce_email_uniqueness():
    """
    Enforce unique index on users.email field
    """
    try:
        # Connect to MongoDB
        logger.info("🔌 Connecting to MongoDB...")
        mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
        db = mongo_client["prism_ai"]
        users_collection = db["users"]
        
        # Check for existing duplicates BEFORE creating index
        logger.info("🔍 Checking for existing duplicate emails...")
        pipeline = [
            {
                "$group": {
                    "_id": "$email",
                    "count": {"$sum": 1},
                    "ids": {"$push": "$_id"}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            }
        ]
        
        duplicates_cursor = users_collection.aggregate(pipeline)
        duplicates = await duplicates_cursor.to_list(length=None)
        
        if duplicates:
            logger.error(f"🚨 FOUND {len(duplicates)} DUPLICATE EMAILS!")
            logger.error("❌ Cannot create unique index until duplicates are resolved")
            logger.error("\nDuplicate emails:")
            for dup in duplicates:
                logger.error(f"  📧 Email: {dup['_id']}")
                logger.error(f"     Count: {dup['count']}")
                logger.error(f"     IDs: {dup['ids']}")
            
            logger.error("\n⚠️ ACTION REQUIRED:")
            logger.error("1. Manually review duplicate users")
            logger.error("2. Merge or delete duplicate records")
            logger.error("3. Re-run this script")
            
            mongo_client.close()
            return False
        
        logger.info("✅ No duplicate emails found")
        
        # Create unique index
        logger.info("🔒 Creating unique index on 'email' field...")
        try:
            result = await users_collection.create_index(
                "email",
                unique=True,
                name="email_unique_idx"
            )
            logger.info(f"✅ Unique index created: {result}")
        except Exception as idx_error:
            if "already exists" in str(idx_error).lower():
                logger.info("ℹ️ Unique index already exists")
            else:
                raise idx_error
        
        # Verify index
        logger.info("🔍 Verifying indexes...")
        indexes = await users_collection.list_indexes().to_list(length=None)
        
        email_index_found = False
        for idx in indexes:
            logger.info(f"  📋 Index: {idx['name']}")
            if idx['name'] == 'email_unique_idx':
                email_index_found = True
                logger.info(f"     ✅ UNIQUE: {idx.get('unique', False)}")
                logger.info(f"     Keys: {idx['key']}")
        
        if email_index_found:
            logger.info("\n✅ EMAIL UNIQUENESS ENFORCED AT DATABASE LEVEL")
            logger.info("🛡️ System will now prevent duplicate users automatically")
        else:
            logger.error("\n❌ Unique index not found after creation")
            return False
        
        # Count total users
        total_users = await users_collection.count_documents({})
        logger.info(f"\n📊 Total unique users in system: {total_users}")
        
        mongo_client.close()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error enforcing uniqueness: {e}")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("🔒 EMAIL UNIQUENESS ENFORCEMENT")
    print("=" * 80)
    
    result = asyncio.run(enforce_email_uniqueness())
    
    if result:
        print("\n" + "=" * 80)
        print("✅ SUCCESS: Email uniqueness enforced")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ FAILED: See errors above")
        print("=" * 80)
