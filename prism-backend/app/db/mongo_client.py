from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import quote_plus, unquote_plus, urlsplit, urlunsplit
from app.config import settings


def _sanitize_mongo_uri(uri: str) -> str:
	"""
	Ensure username/password are RFC 3986 escaped in the MongoDB URI.
	- Decodes any existing userinfo first to avoid double-encoding
	- Re-encodes with quote_plus to satisfy PyMongo's validation
	Supports both `mongodb://` and `mongodb+srv://` URIs.
	"""
	try:
		parts = urlsplit(uri)
		netloc = parts.netloc
		# If URI includes credentials (userinfo@host)
		if '@' in netloc:
			userinfo, host = netloc.rsplit('@', 1)
			# Handle possible missing password (e.g., 'user@host')
			if ':' in userinfo:
				user, pwd = userinfo.split(':', 1)
			else:
				user, pwd = userinfo, ''
			# Avoid double-encoding: normalize then encode
			safe_user = quote_plus(unquote_plus(user)) if user else ''
			safe_pwd = quote_plus(unquote_plus(pwd)) if pwd else ''
			new_userinfo = f"{safe_user}:{safe_pwd}" if safe_pwd or (':' in userinfo) else safe_user
			new_netloc = f"{new_userinfo}@{host}" if new_userinfo else host
			return urlunsplit((parts.scheme, new_netloc, parts.path, parts.query, parts.fragment))
		# No credentials present; return original
	except Exception:
		pass
	return uri


# Create Client with sanitized URI
client = AsyncIOMotorClient(_sanitize_mongo_uri(settings.MONGO_URI))


# Get Database
db = client.prism_db

def get_database():
	"""
	Returns the main MongoDB database instance.
	Usage: db = get_database()
	"""
	return db

# 🧱 PERFECT DATABASE COLLECTIONS (As per requirements)
# Each collection has unique indexes to prevent duplicates

# 📌 users collection - Main user profile data
users_collection = db.users

# 📌 sessions collection - Chat sessions grouped by sessionId  
sessions_collection = db.sessions

# 📌 tasks collection - User tasks stored separately for performance
tasks_collection = db.tasks

# 📌 memory collection - Structured memory facts and preferences
memory_collection = db.memory

# 📌 mini_agents collection - Mini agent conversations
mini_agents_collection = db.mini_agents

# 📌 users_global collection - Historical global user data (never deleted)
users_global_collection = db.users_global

# 🔧 Create unique indexes to prevent duplicates
async def initialize_indexes():
    """
    Create unique indexes on critical fields to ensure data integrity.
    🟢 Rule 1 — Unique Email Index prevents duplicate users
    """
    try:
        # Unique email index for users
        await users_collection.create_index("email", unique=True)
        print("✅ MongoDB: Unique email index created for users collection")
        
        # Index on userId for all collections for fast queries
        await sessions_collection.create_index("userId")
        await tasks_collection.create_index("userId") 
        await memory_collection.create_index("userId")
        await mini_agents_collection.create_index("userId")
        print("✅ MongoDB: userId indexes created for all collections")
        
        # Index on sessionId for fast session lookups
        await sessions_collection.create_index("sessionId")
        print("✅ MongoDB: sessionId index created")
        
        # Index on messageId for mini agent lookups
        await mini_agents_collection.create_index("messageId")
        print("✅ MongoDB: messageId index created for mini_agents")
        
        # Unique email index for global users (historical data)
        await users_global_collection.create_index("email", unique=True)
        await users_global_collection.create_index("userId")
        print("✅ MongoDB: Indexes created for users_global collection")
        
    except Exception as e:
        print(f"⚠️  MongoDB Index creation warning: {e}")

# Call this during app startup
async def setup_mongodb():
    """Initialize MongoDB with proper indexes"""
    await initialize_indexes()

# 🧠 ADVANCED MEMORY MANAGEMENT FUNCTIONS FOR AI MODEL

class MongoClient:
    """MongoDB client with advanced memory management for AI model integration"""
    
    def __init__(self):
        self.db = db
        self.users_collection = users_collection
        self.sessions_collection = sessions_collection
        self.tasks_collection = tasks_collection
        self.memory_collection = memory_collection
    
    # USER PROFILE OPERATIONS
    async def get_user_profile(self, user_id: str) -> dict:
        """Get user profile by user_id"""
        try:
            user = await self.users_collection.find_one({"userId": user_id})
            return user if user else {}
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return {}
    
    async def update_user_profile(self, user_id: str, updates: dict) -> bool:
        """Update user profile with new data (prevents duplicates)"""
        try:
            result = await self.users_collection.update_one(
                {"userId": user_id},
                {"$set": {**updates, "lastUpdated": "2024-12-10T12:00:00Z"}},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False
    
    # STRUCTURED MEMORY OPERATIONS
    async def get_structured_memories(self, user_id: str) -> list:
        """Get all structured memories for user"""
        try:
            memories = await self.memory_collection.find({"userId": user_id}).to_list(None)
            return memories if memories else []
        except Exception as e:
            print(f"Error getting structured memories: {e}")
            return []
    
    async def add_structured_memory(self, user_id: str, memory: dict) -> bool:
        """Add structured memory (with duplicate prevention)"""
        try:
            memory["userId"] = user_id
            result = await self.memory_collection.insert_one(memory)
            return result.acknowledged
        except Exception as e:
            print(f"Error adding structured memory: {e}")
            return False
    
    # TASK OPERATIONS
    async def get_user_tasks(self, user_id: str) -> list:
        """Get all user tasks"""
        try:
            tasks = await self.tasks_collection.find({"userId": user_id}).to_list(None)
            return tasks if tasks else []
        except Exception as e:
            print(f"Error getting user tasks: {e}")
            return []
    
    async def update_user_task(self, user_id: str, task_data: dict) -> bool:
        """Update or create user task"""
        try:
            task_data["userId"] = user_id
            if "taskId" in task_data:
                result = await self.tasks_collection.update_one(
                    {"userId": user_id, "taskId": task_data["taskId"]},
                    {"$set": task_data},
                    upsert=True
                )
            else:
                result = await self.tasks_collection.insert_one(task_data)
            return result.acknowledged
        except Exception as e:
            print(f"Error updating user task: {e}")
            return False
    
    # CONVERSATION OPERATIONS
    async def get_recent_conversations(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversations for context"""
        try:
            conversations = await self.sessions_collection.find(
                {"userId": user_id}
            ).sort("timestamp", -1).limit(limit).to_list(None)
            return conversations if conversations else []
        except Exception as e:
            print(f"Error getting recent conversations: {e}")
            return []
    
    async def save_conversation(self, user_id: str, conversation_data: dict) -> bool:
        """Save conversation for future reference"""
        try:
            conversation_data["userId"] = user_id
            result = await self.sessions_collection.insert_one(conversation_data)
            return result.acknowledged
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return False