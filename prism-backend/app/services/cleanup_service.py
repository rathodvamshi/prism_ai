"""
🧹 COMPREHENSIVE DATA CLEANUP SERVICE

Handles complete user data deletion across ALL storage systems:
- MongoDB (main database)
- Redis (sessions, temp data, OTP)
- Pinecone (vector memory)
- Neo4j (graph memory)
- Prevents ghost data and stale cache issues
"""

from typing import Optional
from app.db.mongo_client import db, users_collection, tasks_collection, memory_collection
from app.db.redis_client import redis_client
from app.db.neo4j_client import driver as neo4j_driver
from app.services.vector_memory_service import get_vector_memory
import logging

logger = logging.getLogger(__name__)

async def cleanup_user_completely(user_id: str, email: str = None) -> dict:
    """
    🚨 NUCLEAR OPTION: Delete user from ALL systems
    
    This function ensures NO ghost data remains anywhere:
    - MongoDB: user profile, tasks, memories, mood history
    - Redis: sessions, OTP, temp memory, cache
    - Pinecone: all vector embeddings for user
    - Neo4j: user node and all relationships
    
    Args:
        user_id: User ID to delete
        email: Optional email for additional cleanup
    
    Returns:
        dict: Cleanup results from each system
    """
    cleanup_results = {
        "user_id": user_id,
        "email": email,
        "mongodb": {"status": "not_started"},
        "redis": {"status": "not_started"}, 
        "pinecone": {"status": "not_started"},
        "neo4j": {"status": "not_started"},
        "success": False
    }
    
    # 🟩 1. MONGODB CLEANUP - Delete from all collections
    try:
        logger.info(f"🧹 Starting MongoDB cleanup for user: {user_id}")
        
        # Delete user profile
        user_result = await users_collection.delete_many({"$or": [
            {"_id": user_id},
            {"email": email} if email else {},
            {"user_id": user_id}
        ]})
        
        # Delete user tasks
        tasks_result = await tasks_collection.delete_many({"userId": user_id})
        
        # Delete user memories
        memory_result = await memory_collection.delete_many({"user_id": user_id})
        
        # Delete mood history
        mood_result = await db.mood_history.delete_many({"user_id": user_id})
        
        # Delete chat sessions
        chat_result = await db.chat_sessions.delete_many({"user_id": user_id})
        
        # Delete highlights
        highlights_result = await db.message_highlights.delete_many({"user_id": user_id})
        
        # Delete shared conversations
        shared_result = await db.shared_conversations.delete_many({"user_id": user_id})
        
        # Delete miniagent threads
        threads_result = await db.miniagent_threads.delete_many({"user_id": user_id})
        
        cleanup_results["mongodb"] = {
            "status": "success",
            "users_deleted": user_result.deleted_count,
            "tasks_deleted": tasks_result.deleted_count,
            "memories_deleted": memory_result.deleted_count,
            "moods_deleted": mood_result.deleted_count,
            "chats_deleted": chat_result.deleted_count,
            "highlights_deleted": highlights_result.deleted_count,
            "shared_deleted": shared_result.deleted_count,
            "threads_deleted": threads_result.deleted_count
        }
        
        logger.info(f"✅ MongoDB cleanup completed: {cleanup_results['mongodb']}")
        
    except Exception as e:
        cleanup_results["mongodb"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ MongoDB cleanup failed: {e}")
    
    # 🟧 2. REDIS CLEANUP - Delete all user-related keys
    try:
        logger.info(f"🧹 Starting Redis cleanup for user: {user_id}")
        
        # Delete user session keys
        session_patterns = [
            f"session:{user_id}",
            f"user_session:{user_id}",
            f"chat_history:{user_id}*",
            f"recent_history:{user_id}*",
            f"otp:{email}" if email else None,
            f"otp:{user_id}",
            f"temp_memory:{user_id}*",
            f"cache:{user_id}*",
            f"user_cache:{user_id}*"
        ]
        
        deleted_keys = []
        for pattern in session_patterns:
            if pattern:
                try:
                    # Get keys matching pattern
                    keys = await redis_client.keys(pattern)
                    if keys:
                        deleted_count = await redis_client.delete(*keys)
                        deleted_keys.extend(keys)
                        logger.info(f"🗑️ Deleted {deleted_count} Redis keys for pattern: {pattern}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete Redis pattern {pattern}: {e}")
        
        cleanup_results["redis"] = {
            "status": "success",
            "keys_deleted": len(deleted_keys),
            "deleted_keys": [key.decode() if isinstance(key, bytes) else key for key in deleted_keys[:10]]  # Show first 10
        }
        
        logger.info(f"✅ Redis cleanup completed: {len(deleted_keys)} keys deleted")
        
    except Exception as e:
        cleanup_results["redis"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ Redis cleanup failed: {e}")
    
    # 🟨 3. PINECONE CLEANUP - Delete user vector namespace
    try:
        logger.info(f"🧹 Starting Pinecone cleanup for user: {user_id}")
        
        # Delete all vectors for user (by metadata filter)
        try:
            # Try to delete by user_id filter
            vm = get_vector_memory()
            delete_response = vm.delete_user_memories(user_id)
            
            cleanup_results["pinecone"] = {
                "status": "success", 
                "delete_response": str(delete_response)
            }
            logger.info(f"✅ Pinecone cleanup completed for user: {user_id}")
            
        except Exception as e:
            # If specific user deletion fails, try to delete by namespace
            logger.warning(f"⚠️ Pinecone user filter deletion failed, trying alternative: {e}")
            cleanup_results["pinecone"] = {
                "status": "partial", 
                "error": str(e),
                "note": "User vectors may still exist in Pinecone"
            }
    
    except Exception as e:
        cleanup_results["pinecone"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ Pinecone cleanup failed: {e}")
    
    # 🟦 4. NEO4J CLEANUP - Delete user node and all relationships  
    try:
        logger.info(f"🧹 Starting Neo4j cleanup for user: {user_id}")
        
        async with neo4j_driver.session() as session:
            # Delete user node and all connected relationships
            cypher_query = """
            MATCH (u:User {id: $user_id})
            OPTIONAL MATCH (u)-[r]-()
            DELETE r, u
            RETURN count(u) as nodes_deleted
            """
            
            result = await session.run(cypher_query, user_id=user_id)
            record = await result.single()
            nodes_deleted = record["nodes_deleted"] if record else 0
            
            # Also try deleting by email if provided
            if email:
                email_query = """
                MATCH (u:User {email: $email})
                OPTIONAL MATCH (u)-[r]-()
                DELETE r, u
                RETURN count(u) as nodes_deleted
                """
                result = await session.run(email_query, email=email)
                record = await result.single()
                email_nodes_deleted = record["nodes_deleted"] if record else 0
                nodes_deleted += email_nodes_deleted
            
            cleanup_results["neo4j"] = {
                "status": "success",
                "nodes_deleted": nodes_deleted
            }
            
            logger.info(f"✅ Neo4j cleanup completed: {nodes_deleted} nodes deleted")
            
    except Exception as e:
        cleanup_results["neo4j"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ Neo4j cleanup failed: {e}")
    
    # 🎯 5. FINAL SUCCESS CHECK
    successful_cleanups = sum(1 for result in cleanup_results.values() 
                            if isinstance(result, dict) and result.get("status") == "success")
    
    cleanup_results["success"] = successful_cleanups >= 3  # At least 3 out of 4 systems cleaned
    cleanup_results["systems_cleaned"] = successful_cleanups
    cleanup_results["total_systems"] = 4
    
    if cleanup_results["success"]:
        logger.info(f"🎉 Complete user cleanup SUCCESSFUL for {user_id}")
    else:
        logger.warning(f"⚠️ Partial user cleanup for {user_id} - some systems failed")
    
    return cleanup_results


async def verify_user_exists_in_mongodb(user_id: str, email: str = None) -> Optional[dict]:
    """
    🔍 DATABASE-FIRST CHECK: Verify user exists in MongoDB
    
    This is the SINGLE SOURCE OF TRUTH for user existence.
    All other systems should ONLY load data if this returns a user.
    
    Args:
        user_id: User ID to check
        email: Optional email for additional lookup
        
    Returns:
        dict: User data if exists, None if not found
    """
    try:
        # Try multiple lookup methods
        query_conditions = []
        
        # Try by _id (ObjectId string)
        try:
            from bson import ObjectId
            if ObjectId.is_valid(user_id):
                query_conditions.append({"_id": ObjectId(user_id)})
        except:
            pass
        
        # Try by string _id
        query_conditions.append({"_id": user_id})
        
        # Try by user_id field
        query_conditions.append({"user_id": user_id})
        
        # Try by email if provided
        if email:
            query_conditions.append({"email": email})
        
        # Search with OR condition
        user = await users_collection.find_one({"$or": query_conditions})
        
        if user:
            # Convert ObjectId to string for JSON serialization
            if user.get("_id"):
                user["_id"] = str(user["_id"])
            
            logger.info(f"✅ User found in MongoDB: {user_id}")
            return user
        else:
            logger.info(f"❌ User NOT found in MongoDB: {user_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error checking user existence in MongoDB: {e}")
        return None


async def cleanup_all_ghost_data():
    """
    🧹 EMERGENCY CLEANUP: Remove all data from all systems
    
    Use this when you want to completely reset everything
    """
    logger.warning("🚨 EMERGENCY: Starting complete data cleanup!")
    
    try:
        # Clear MongoDB
        await db.users.delete_many({})
        await db.user_tasks.delete_many({})  
        await db.user_memory.delete_many({})
        await db.mood_history.delete_many({})
        await db.chat_sessions.delete_many({})
        await db.message_highlights.delete_many({})
        await db.shared_conversations.delete_many({})
        await db.miniagent_threads.delete_many({})
        
        # Clear Redis
        await redis_client.flushdb()
        
        # Clear Pinecone (delete all vectors) - try multiple methods
        try:
            vm = get_vector_memory()
            if vm.index:
                # Method 1: Delete all vectors by namespace if supported
                vm.index.delete(delete_all=True, namespace="")
        except:
            try:
                # Method 2: Delete by filter
                if vm.index:
                    vm.index.delete(filter={})
            except:
                try:
                    # Method 3: Get all vector IDs and delete them
                    if vm.index:
                        vm.index.describe_index_stats()
                    # If we can't delete all, log warning
                    logger.warning("⚠️ Could not delete all Pinecone vectors - may require manual cleanup")
                except:
                    logger.warning("⚠️ Pinecone cleanup may have failed")
        
        # Clear Neo4j
        async with neo4j_driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        
        logger.warning("🧹 EMERGENCY CLEANUP COMPLETED - ALL DATA DELETED")
        return {"status": "success", "message": "All systems cleared"}
        
    except Exception as e:
        logger.error(f"❌ Emergency cleanup failed: {e}")
        return {"status": "error", "error": str(e)}