"""
👤 PERFECT USER MANAGEMENT ROUTES

Implements the exact user management system you specified:
- MongoDB for main user data (account, profile, tasks, sessions) 
- Redis for caching and temporary data
- Pinecone for vector memory
- Neo4j for relationship graphs
- Complete user separation with email as primary identifier
- No duplicates allowed anywhere
"""

from fastapi import APIRouter, HTTPException, Body, Depends, status
from app.db.mongo_client import users_collection, tasks_collection, memory_collection, sessions_collection
from app.models.perfect_models import (
    UserModel, CreateUserRequest, TaskModel, CreateTaskRequest, 
    AddMemoryRequest, UserSummary
)
from app.services.perfect_memory_pipeline import get_user_summary, delete_user_data
from app.db.redis_client import (
    store_otp, verify_otp, clear_user_cache, get_redis_stats
)
from app.services.vector_memory_service import (
    get_memory_analytics, get_vector_memory
)
from app.db.neo4j_client import (
    graph_memory, create_user_in_graph, add_interest_to_user, add_task_to_user
)
from app.utils.auth import get_current_user, get_verified_user, AuthUtils, SecurityUtils
from app.services.user_memory_manager import get_user_memory_statistics, delete_all_user_memories
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
from datetime import datetime
from bson import ObjectId
import uuid

router = APIRouter(
    prefix="/users",
    tags=["Perfect User Management"]
)

# 🏥 HEALTH CHECK
@router.get("/health")
async def health_check():
    """Health check endpoint for perfect user service"""
    return {"status": "healthy", "service": "perfect_user_management", "version": "1.0"}

# 🔐 PROTECTED USER ENDPOINTS (JWT Required)

@router.get("/profile")
async def get_current_user_profile(current_user: dict = Depends(get_verified_user)):
    """Get current user's complete profile information from database"""
    try:
        safe_user = AuthUtils.create_user_response(current_user)
        
        # Get complete profile data
        profile_data = current_user.get("profile", {})
        
        # Get task and session counts
        user_id = str(current_user["_id"])
        task_count = await tasks_collection.count_documents({"userId": user_id})
        session_count = await sessions_collection.count_documents({"userId": user_id})
        
        return {
            "user": safe_user,
            "profile": {
                "name": profile_data.get("name", current_user.get("name", "")),
                "email": current_user.get("email", ""),
                "bio": profile_data.get("bio", ""),
                "location": profile_data.get("location", ""),
                "website": profile_data.get("website", ""),
                "avatarUrl": profile_data.get("avatarUrl", ""),
                "interests": profile_data.get("interests", []),
                "hobbies": profile_data.get("hobbies", [])
            },
            "stats": {
                "member_since": current_user.get("created_at"),
                "last_login": current_user.get("last_login"),
                "verified": current_user.get("verified", False),
                "total_tasks": task_count,
                "total_sessions": session_count
            }
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )

@router.put("/profile")
async def update_user_profile(
    profile_data: dict,
    current_user: dict = Depends(get_verified_user)
):
    """Update current user's profile information and sync to global collection"""
    try:
        from app.services.global_user_service import update_global_user_profile
        
        # Sanitize input data
        sanitized_data = {}
        for key, value in profile_data.items():
            if key in ["name", "bio", "location", "website", "avatarUrl"]:
                sanitized_data[key] = SecurityUtils.sanitize_user_input(str(value), 500) if value else ""
            elif key in ["interests", "hobbies"]:
                if isinstance(value, list):
                    sanitized_data[key] = [SecurityUtils.sanitize_user_input(str(item), 100) for item in value[:10]]
        
        user_id = str(current_user["_id"])
        email = current_user.get("email")
        
        # Update user profile in main collection
        update_data = {
            "profile": sanitized_data,
            "updated_at": datetime.now()
        }
        
        # If name is being updated, also update it at top level
        if "name" in sanitized_data:
            update_data["name"] = sanitized_data["name"]
        
        result = await users_collection.update_one(
            {"_id": current_user["_id"]},
            {"$set": update_data}
        )
        
        # Sync to global collection
        if email:
            try:
                await update_global_user_profile(email, sanitized_data)
            except Exception as e:
                logger.warning(f"Failed to sync to global collection: {e}")
        
        return {
            "message": "Profile updated successfully",
            "profile": sanitized_data,
            "synced_to_global": email is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_verified_user)):
    """Get user statistics and usage information"""
    try:
        user_id = str(current_user["_id"])
        
        # Get task count
        task_count = await tasks_collection.count_documents({"user_id": user_id})
        
        # Get memory count
        memory_count = await memory_collection.count_documents({"user_id": user_id})
        
        # Get vector memory stats
        vm = get_vector_memory()
        vector_stats = {"available": False, "count": 0}
        if vm and vm.index:
            try:
                stats = vm.index.describe_index_stats()
                vector_stats = {"available": True, "count": stats.total_vector_count}
            except:
                pass
        
        return {
            "tasks": task_count,
            "memories": memory_count,
            "vector_memories": vector_stats,
            "account_created": current_user.get("created_at"),
            "last_login": current_user.get("last_login")
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )

@router.delete("/account")
async def delete_user_account(
    confirmation: dict,
    current_user: dict = Depends(get_verified_user)
):
    """
    Delete user account and all associated data from all databases
    Mark as deleted in global collection (preserved for history)
    """
    try:
        from app.services.global_user_service import mark_user_deleted_in_global
        from app.db.mongo_client import sessions_collection
        
        # Require confirmation
        if confirmation.get("confirm_delete") != "DELETE_MY_ACCOUNT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account deletion requires confirmation text: 'DELETE_MY_ACCOUNT'"
            )
        
        user_id = str(current_user["_id"])
        email = current_user["email"]
        
        logger.info(f"Starting account deletion for user: {email}")
        
        # Delete from all collections
        deleted_counts = {}
        
        # 1. Delete user sessions
        sessions_result = await sessions_collection.delete_many({"userId": user_id})
        deleted_counts["sessions"] = sessions_result.deleted_count
        
        # 2. Delete user tasks
        tasks_result = await tasks_collection.delete_many({"userId": user_id})
        deleted_counts["tasks"] = tasks_result.deleted_count
        
        # 3. Delete user memories
        memory_result = await memory_collection.delete_many({"userId": user_id})
        deleted_counts["memories"] = memory_result.deleted_count
        
        # 4. Delete mini agents
        from app.db.mongo_client import mini_agents_collection
        mini_agents_result = await mini_agents_collection.delete_many({"userId": user_id})
        deleted_counts["mini_agents"] = mini_agents_result.deleted_count
        
        # 5. Delete from vector database (Pinecone)
        try:
            vm = get_vector_memory()
            if vm and vm.index:
                vm.index.delete(filter={"userId": user_id})
                deleted_counts["vector_memories"] = "cleaned"
        except Exception as e:
            logger.warning(f"Vector memory cleanup warning: {e}")
            deleted_counts["vector_memories"] = "skipped"
        
        # 6. Delete from graph database (Neo4j)
        try:
            from app.db.neo4j_client import graph_memory
            if graph_memory and graph_memory.graph:
                graph_memory.graph.run(
                    "MATCH (u:User {userId: $userId}) DETACH DELETE u",
                    userId=user_id
                )
                deleted_counts["graph_data"] = "cleaned"
        except Exception as e:
            logger.warning(f"Graph cleanup warning: {e}")
            deleted_counts["graph_data"] = "skipped"
        
        # 7. Clear Redis cache
        try:
            await clear_user_cache(user_id)
            deleted_counts["redis_cache"] = "cleared"
        except Exception as e:
            logger.warning(f"Redis cleanup warning: {e}")
            deleted_counts["redis_cache"] = "skipped"
        
        # 8. Mark as deleted in global collection (PRESERVED - NOT DELETED)
        # This keeps user profile data for historical purposes and analytics
        # If user signs up again with same email, global collection won't duplicate
        await mark_user_deleted_in_global(user_id, email, "user_requested")
        
        # 9. Finally, delete main user record from active users collection
        await users_collection.delete_one({"_id": current_user["_id"]})
        deleted_counts["user_account"] = "deleted"
        
        logger.info(f"Account deletion completed for: {email}")
        
        return {
            "message": "Account successfully deleted from all systems",
            "email": email,
            "preserved_in_global": True,
            "cleanup_summary": deleted_counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )

@router.get("/memory/stats")
async def get_memory_statistics(current_user: dict = Depends(get_verified_user)):
    """Get user's memory usage statistics"""
    try:
        user_id = str(current_user["_id"])
        stats = await get_user_memory_statistics(user_id)
        
        return {
            "user_id": user_id,
            "memory_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get memory statistics"
        )

@router.delete("/memory")
async def clear_user_memories(
    confirmation: dict,
    current_user: dict = Depends(get_verified_user)
):
    """Clear all user memories with proper confirmation"""
    try:
        # Require confirmation
        if confirmation.get("confirm_clear") != "CLEAR_MY_MEMORIES":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Memory clearing requires proper confirmation"
            )
        
        user_id = str(current_user["_id"])
        deletion_results = await delete_all_user_memories(user_id)
        
        return {
            "message": "All memories cleared successfully",
            "user_id": user_id,
            "deletion_summary": deletion_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing user memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear memories"
        )

# 👤 PERFECT USER CREATION - EXACTLY AS SPECIFIED  
@router.post("/create")
async def create_user_perfect(request: CreateUserRequest):
    """
    📌 Create new user in all databases
    
    🟢 Rule 1: Every user → use their email as primary unique identifier  
    🟢 Rule 2: Create user in all databases (Mongo, Neo4j)
    🟢 Rule 3: No duplicates allowed (unique email index)
    """
    try:
        # Check if user already exists (prevent duplicates)
        existing_user = await users_collection.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(status_code=400, detail=f"User already exists: {request.email}")
        
        # Create user model
        new_user = UserModel(
            email=request.email,
            name=request.name,
            role=request.role,
            hobbies=request.hobbies,
            interests=request.interests,
            responseStyle=request.responseStyle
        )
        
        # Insert into MongoDB
        result = await users_collection.insert_one(new_user.dict(by_alias=True))
        user_id = str(result.inserted_id)
        
        # Create user in Neo4j graph
        await create_user_in_graph(user_id, request.email, request.name)
        
        # Add interests to graph
        for interest in request.interests:
            await add_interest_to_user(user_id, interest, "interest")
        
        # Add hobbies to graph  
        for hobby in request.hobbies:
            await add_interest_to_user(user_id, hobby, "hobby")
        
        print(f"✅ Perfect user created: {request.email} (ID: {user_id})")
        
        return {
            "success": True,
            "userId": user_id,
            "email": request.email,
            "message": "User created in all databases successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    Get complete user profile from all databases.
    🎯 Perfect for user profile display.
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Get comprehensive user summary from all databases
        summary = await get_user_summary(user_id)
        
        if summary.get("error"):
            raise HTTPException(status_code=404, detail=summary["error"])
        
        return {
            "success": True,
            "profile": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/by-email/{email}")
async def get_user_by_email(email: str):
    """
    Find user by email (primary unique identifier).
    🟢 Rule: Email is the primary way to identify users.
    """
    try:
        user = await users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {email}")
        
        # Convert ObjectId to string for JSON serialization
        user["_id"] = str(user["_id"])
        
        return {
            "success": True,
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

# 📋 PERFECT TASK MANAGEMENT
@router.post("/tasks/create")
async def create_task_perfect(request: CreateTaskRequest):
    """
    📌 Create task in MongoDB and Neo4j
    🟢 Rule: Tasks always linked to userId - no orphaned tasks
    """
    try:
        if not ObjectId.is_valid(request.userId):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Verify user exists
        user = await users_collection.find_one({"_id": ObjectId(request.userId)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check for duplicate task (same title + userId)
        existing_task = await tasks_collection.find_one({
            "userId": ObjectId(request.userId),
            "title": request.title
        })
        
        if existing_task:
            raise HTTPException(status_code=400, detail="Task with same title already exists")
        
        # Generate unique task ID
        task_id = f"T_{int(datetime.utcnow().timestamp())}_{hash(request.title) % 1000}"
        
        # Create task in MongoDB
        new_task = TaskModel(
            taskId=task_id,
            userId=ObjectId(request.userId),
            title=request.title,
            description=request.description
        )
        
        await tasks_collection.insert_one(new_task.dict(by_alias=True))
        
        # Add task to Neo4j graph  
        await add_task_to_user(request.userId, task_id, request.title)
        
        print(f"✅ Task created: {request.title} for user {request.userId}")
        
        return {
            "success": True,
            "taskId": task_id,
            "message": "Task created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/tasks/{user_id}")
async def get_user_tasks(user_id: str, status: Optional[str] = None):
    """
    Get all tasks for a user.
    🟢 Rule: Only return tasks for the specified userId
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Build query
        query = {"userId": ObjectId(user_id)}
        if status:
            query["status"] = status
        
        # Get tasks from MongoDB
        tasks = await tasks_collection.find(query).sort("createdAt", -1).to_list(length=100)
        
        # Format tasks for frontend
        formatted_tasks = []
        for task in tasks:
            formatted_task = {
                "taskId": task["taskId"],
                "title": task["title"],
                "description": task.get("description", ""),
                "status": task["status"],
                "createdAt": task["createdAt"],
                "completedAt": task.get("completedAt"),
                "updatedAt": task["updatedAt"]
            }
            formatted_tasks.append(formatted_task)
        
        return {
            "success": True,
            "tasks": formatted_tasks,
            "total": len(formatted_tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, user_id: str, status: str):
    """
    Update task status in both MongoDB and Neo4j.
    🟢 Rule: Verify task belongs to user before updating
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Update in MongoDB with user verification
        update_data = {
            "status": status,
            "updatedAt": datetime.utcnow()
        }
        
        if status == "completed":
            update_data["completedAt"] = datetime.utcnow()
        
        result = await tasks_collection.update_one(
            {"taskId": task_id, "userId": ObjectId(user_id)},  # CRITICAL: Verify ownership
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Task not found or access denied")
        
        # Update in Neo4j graph
        await graph_memory.update_task_status(user_id, task_id, status)
        
        return {
            "success": True,
            "message": "Task status updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

# 🧠 PERFECT MEMORY MANAGEMENT
@router.post("/memory/add")
async def add_memory_fact(request: AddMemoryRequest):
    """
    Add structured memory fact for user.
    🟢 Rule: Check before inserting to avoid duplicates
    """
    try:
        if not ObjectId.is_valid(request.userId):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Check if memory document exists
        memory_doc = await memory_collection.find_one({"userId": ObjectId(request.userId)})
        
        # Check for duplicate fact
        if memory_doc:
            existing_values = {fact.get("value", "") for fact in memory_doc.get("facts", [])}
            if request.value in existing_values:
                return {
                    "success": False,
                    "message": "Memory fact already exists"
                }
        
        # Create memory fact
        from app.models.perfect_models import MemoryFact
        new_fact = MemoryFact(
            type=request.type,
            value=request.value,
            confidence=request.confidence
        )
        
        if memory_doc:
            # Add to existing memory
            await memory_collection.update_one(
                {"userId": ObjectId(request.userId)},
                {
                    "$push": {"facts": new_fact.dict()},
                    "$set": {"updatedAt": datetime.utcnow()}
                }
            )
        else:
            # Create new memory document
            from app.models.perfect_models import MemoryModel
            new_memory = MemoryModel(
                userId=ObjectId(request.userId),
                facts=[new_fact]
            )
            await memory_collection.insert_one(new_memory.dict(by_alias=True))
        
        return {
            "success": True,
            "message": "Memory fact added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/memory/{user_id}")
async def get_user_memories(user_id: str):
    """
    Get all structured memories for user.
    🟢 Rule: Only return memories for specified userId
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Get from MongoDB
        memory_doc = await memory_collection.find_one({"userId": ObjectId(user_id)})
        
        if not memory_doc:
            return {
                "success": True,
                "memories": {
                    "facts": [],
                    "preferences": {},
                    "total_facts": 0
                }
            }
        
        return {
            "success": True,
            "memories": {
                "facts": memory_doc.get("facts", []),
                "preferences": memory_doc.get("preferences", {}),
                "total_facts": len(memory_doc.get("facts", [])),
                "updatedAt": memory_doc.get("updatedAt")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

# 🗑️ PERFECT USER DELETION 
@router.delete("/delete/{user_id}")
async def delete_user_completely(user_id: str):
    """
    🚨 COMPLETE USER DELETION from all databases
    
    Deletes from:
    - MongoDB (users, sessions, tasks, memory)
    - Pinecone (vector memories)
    - Neo4j (graph relationships)
    - Redis (cache data)
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Verify user exists
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete completely using pipeline
        success = await delete_user_data(user_id)
        
        if success:
            # Also clear Redis cache
            await clear_user_cache(user_id)
            
            return {
                "success": True,
                "message": f"User {user['email']} completely deleted from all databases"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete user completely")
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

# 📊 PERFECT ANALYTICS & STATS
@router.get("/analytics/overview")
async def get_system_overview():
    """Get overview statistics from all databases"""
    try:
        # Get stats from all systems
        import asyncio
        
        # MongoDB stats
        mongo_stats_task = asyncio.create_task(get_mongo_stats())
        
        # Redis stats  
        redis_stats_task = asyncio.create_task(get_redis_stats())
        
        # Pinecone stats
        pinecone_stats_task = asyncio.create_task(get_memory_analytics())
        
        # Neo4j stats
        neo4j_stats_task = asyncio.create_task(graph_memory.get_graph_stats())
        
        # Wait for all stats
        mongo_stats, redis_stats, pinecone_stats, neo4j_stats = await asyncio.gather(
            mongo_stats_task, redis_stats_task, pinecone_stats_task, neo4j_stats_task,
            return_exceptions=True
        )
        
        overview = {
            "mongodb": mongo_stats if not isinstance(mongo_stats, Exception) else {"error": str(mongo_stats)},
            "redis": redis_stats if not isinstance(redis_stats, Exception) else {"error": str(redis_stats)}, 
            "pinecone": pinecone_stats if not isinstance(pinecone_stats, Exception) else {"error": str(pinecone_stats)},
            "neo4j": neo4j_stats if not isinstance(neo4j_stats, Exception) else {"error": str(neo4j_stats)},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "analytics": overview
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}

async def get_mongo_stats():
    """Get MongoDB statistics"""
    try:
        user_count = await users_collection.count_documents({})
        session_count = await users_collection.database.sessions.count_documents({})
        task_count = await tasks_collection.count_documents({})
        memory_count = await memory_collection.count_documents({})
        
        return {
            "users": user_count,
            "sessions": session_count,  
            "tasks": task_count,
            "memories": memory_count
        }
    except Exception as e:
        return {"error": str(e)}
    return {"status": "ok", "message": "User routes are working"}

@router.get("/profile")
async def get_user_profile(email: str):
    """
    Returns user profile fields stored in MongoDB users collection.
    """
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # convert ObjectId if present
    if user.get("_id"):
        user["_id"] = str(user["_id"])
    # limit to safe fields
    safe = {
        "_id": user.get("_id"),
        "email": user.get("email"),
        "user_id": user.get("user_id", user.get("email")),  # Fallback to email if no user_id
        "username": user.get("username", ""),
        "hobby": user.get("hobby", []),
        "role": user.get("role", ""),
        "interests": user.get("interests", []),
        "responseStyle": user.get("responseStyle", ""),
        "verified": user.get("verified", False),
        "isFirstLoginCompleted": user.get("isFirstLoginCompleted", False),
        "profileComplete": user.get("profileComplete", False),
        "createdAt": user.get("createdAt"),
        "onboardedAt": user.get("onboardedAt")
    }
    return safe


class ProfileUpdate(BaseModel):
    email: EmailStr
    username: str | None = None
    hobby: list[str] | None = None
    role: str | None = None
    interests: list[str] | None = None
    responseStyle: str | None = None

class MemoryItem(BaseModel):
    id: str
    type: str  # "profile", "preference", "fact", "behavior"
    content: str
    timestamp: datetime
    importance: int = 1  # 1-5 scale

class TaskItem(BaseModel):
    taskId: str
    title: str
    description: str = ""
    status: str = "pending"  # "pending", "completed", "cancelled"
    createdAt: datetime
    dueDate: datetime | None = None
    completedAt: datetime | None = None

class MessageHighlight(BaseModel):
    highlightId: str
    messageId: str
    sessionId: str
    text: str
    color: str
    startIndex: int
    endIndex: int
    createdAt: datetime

class MiniAgentThread(BaseModel):
    threadId: str
    messageId: str  # Original message that spawned the mini-agent
    sessionId: str
    selectedText: str
    messages: list[dict]  # [{"role": "user/assistant", "content": "", "timestamp": ""}]
    createdAt: datetime
    updatedAt: datetime

class OnboardingRequest(BaseModel):
    email: EmailStr
    username: str
    hobby: list[str] | None = None
    role: str | None = None
    interests: list[str] | None = None
    responseStyle: str | None = None
    isFirstLoginCompleted: bool = True

# Internal helper: upsert memory item to avoid duplicates
async def _upsert_memory_item(user_id: str, content: str, memory_type: str = "fact", importance: int = 1):
    """Upsert a memory entry uniquely by (user_id, type, content).
    Updates timestamp and increases importance if higher.
    Returns the upsert status and id.
    """
    mem_id = f"{memory_type}_{user_id}_{datetime.utcnow().timestamp()}"
    result = await memory_collection.update_one(
        {"user_id": user_id, "type": memory_type, "content": content},
        {
            "$set": {"timestamp": datetime.utcnow()},
            "$setOnInsert": {
                "id": mem_id,
                "user_id": user_id,
                "type": memory_type,
                "content": content,
            },
            "$max": {"importance": importance}
        },
        upsert=True
    )
    # Try to fetch the id if it existed
    doc = await memory_collection.find_one({"user_id": user_id, "type": memory_type, "content": content})
    return {"upserted": result.upserted_id is not None, "id": doc.get("id") if doc else None}

@router.post("/onboarding")
async def complete_onboarding(payload: OnboardingRequest):
    """Complete user onboarding after successful signup"""
    # Validate required fields
    if not payload.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    
    # Verify user exists and is verified
    user = await users_collection.find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("verified"):
        raise HTTPException(status_code=403, detail="Email not verified")
    
    # Create user_id for memory systems (using email as unique identifier)
    user_id = payload.email
    
    # Update user with onboarding data
    update_data = {
        "user_id": user_id,
        "username": payload.username,
        "hobby": payload.hobby or [],
        "role": payload.role or "",
        "interests": payload.interests or [],
        "responseStyle": payload.responseStyle or "",
        "isFirstLoginCompleted": payload.isFirstLoginCompleted,
        "onboardedAt": datetime.utcnow(),
        "profileComplete": True
    }
    
    try:
        result = await users_collection.update_one(
            {"email": payload.email},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize user memory with profile information
        memory_items = []
        
        # Core profile memory
        memory_items.append({
            "id": f"profile_{user_id}_{datetime.utcnow().timestamp()}",
            "type": "profile",
            "content": f"Username: {payload.username}",
            "timestamp": datetime.utcnow(),
            "importance": 5
        })
        
        # Hobbies memory
        if payload.hobby and len(payload.hobby) > 0:
            hobbies_str = ", ".join(payload.hobby)
            memory_items.append({
                "id": f"hobby_{user_id}_{datetime.utcnow().timestamp()}",
                "type": "preference",
                "content": f"Enjoys: {hobbies_str}",
                "timestamp": datetime.utcnow(),
                "importance": 4
            })
        
        # Role memory
        if payload.role:
            memory_items.append({
                "id": f"role_{user_id}_{datetime.utcnow().timestamp()}",
                "type": "profile",
                "content": f"Professional role: {payload.role}",
                "timestamp": datetime.utcnow(),
                "importance": 4
            })
        
        # Interests memory
        if payload.interests:
            interests_str = ", ".join(payload.interests)
            memory_items.append({
                "id": f"interests_{user_id}_{datetime.utcnow().timestamp()}",
                "type": "preference",
                "content": f"Interested in: {interests_str}",
                "timestamp": datetime.utcnow(),
                "importance": 3
            })
        
        # Response style memory
        if payload.responseStyle:
            memory_items.append({
                "id": f"style_{user_id}_{datetime.utcnow().timestamp()}",
                "type": "preference",
                "content": f"Prefers {payload.responseStyle} communication style",
                "timestamp": datetime.utcnow(),
                "importance": 3
            })
        
        # Save all memory items with upsert to avoid duplicates
        if memory_items:
            for memory_item in memory_items:
                await _upsert_memory_item(
                    user_id,
                    memory_item["content"],
                    memory_item["type"],
                    memory_item.get("importance", 1)
                )
        
        # Also save to Pinecone for semantic search
        from app.services.memory_manager import save_long_term_memory
        profile_summary = f"User Profile: {payload.username}"
        if payload.hobby and len(payload.hobby) > 0:
            profile_summary += f" enjoys {', '.join(payload.hobby)}"
        if payload.role:
            profile_summary += f" works as {payload.role}"
        if payload.interests:
            profile_summary += f" interested in {', '.join(payload.interests[:3])}"
        
        await save_long_term_memory(user_id, profile_summary)
        
        return {
            "status": "success",
            "message": "Onboarding completed successfully",
            "user": {
                "email": payload.email,
                "username": payload.username,
                "user_id": user_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete onboarding: {e}")

# Memory management endpoints
@router.get("/memory")
async def get_user_memory(user_id: str, limit: int = 50):
    """Get user's memory items sorted by importance and recency"""
    memory_items = await memory_collection.find(
        {"user_id": user_id}
    ).sort([("importance", -1), ("timestamp", -1)]).limit(limit).to_list(limit)
    
    return {"memory": memory_items, "count": len(memory_items)}

@router.post("/memory")
async def add_memory_item(user_id: str, content: str, memory_type: str = "fact", importance: int = 1):
    """Add or update a memory item for user without duplicates"""
    res = await _upsert_memory_item(user_id, content, memory_type, importance)

    # Also save/update in Pinecone for semantic search (deterministic id)
    from app.services.memory_manager import save_long_term_memory
    await save_long_term_memory(user_id, content, memory_type)
    
    return {"status": "upserted", "memory_id": res.get("id")}

# Enhanced Task management endpoints
@router.get("/tasks")
async def get_user_tasks(user_id: str, status: str = None, limit: int = 20):
    """Get user's tasks, optionally filtered by status"""
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    tasks = await tasks_collection.find(query).sort("createdAt", -1).limit(limit).to_list(limit)
    
    # Convert ObjectId to string for JSON serialization
    for task in tasks:
        if "_id" in task:
            task["_id"] = str(task["_id"])
    
    # Get counts for UI
    pending_count = await tasks_collection.count_documents({"user_id": user_id, "status": "pending"})
    completed_count = await tasks_collection.count_documents({"user_id": user_id, "status": "completed"})
    
    return {
        "tasks": tasks,
        "counts": {
            "pending": pending_count,
            "completed": completed_count
        }
    }

@router.post("/tasks")
async def create_task(user_id: str, title: str, description: str = "", due_date: datetime = None):
    """Create new task for user"""
    task_id = f"task_{user_id}_{datetime.utcnow().timestamp()}"
    
    task = {
        "taskId": task_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": "pending",
        "createdAt": datetime.utcnow(),
        "dueDate": due_date,
        "completedAt": None
    }
    
    await tasks_collection.insert_one(task)
    
    # Add to memory
    await add_memory_item(user_id, f"Created task: {title}", "behavior", 2)
    
    return {"status": "created", "task": task}

@router.put("/tasks/{task_id}")
async def update_task_status(task_id: str, status: str, user_id: str):
    """Update task status"""
    update_data = {"status": status}
    if status == "completed":
        update_data["completedAt"] = datetime.utcnow()
    
    result = await tasks_collection.update_one(
        {"taskId": task_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        # Add to memory
        await add_memory_item(user_id, f"Task {status}: {task_id}", "behavior", 1)
        return {"status": "updated"}
    
    raise HTTPException(status_code=404, detail="Task not found")

@router.put("/profile")
async def update_user_profile(payload: ProfileUpdate):
    """Update profile fields in MongoDB users collection"""
    update_fields = {}
    for key in ["username", "hobby", "role", "interests", "responseStyle"]:
        val = getattr(payload, key)
        if val is not None:
            update_fields[key] = val
    if not update_fields:
        return {"status": "noop"}
    await users_collection.update_one({"email": payload.email}, {"$set": update_fields}, upsert=True)
    return {"status": "updated"}

# 🧹 USER DELETION AND CLEANUP ENDPOINTS

@router.delete("/delete/{user_id}")
async def delete_user_completely(user_id: str):
    """
    🚨 NUCLEAR DELETION: Remove user from ALL storage systems
    
    This endpoint ensures complete cleanup across:
    - MongoDB (all collections)
    - Redis (sessions, cache, OTP)  
    - Pinecone (vector memory)
    - Neo4j (graph memory)
    
    No ghost data will remain after this operation.
    """
    try:
        from app.services.cleanup_service import cleanup_user_completely
        
        # Get user info before deletion for logging
        user = await users_collection.find_one({"$or": [
            {"_id": user_id},
            {"user_id": user_id},
            {"email": user_id}
        ]})
        
        user_email = user.get("email") if user else None
        
        # Perform comprehensive cleanup
        cleanup_results = await cleanup_user_completely(user_id, user_email)
        
        return {
            "success": cleanup_results["success"],
            "message": f"User deletion completed across {cleanup_results['systems_cleaned']}/{cleanup_results['total_systems']} systems",
            "user_id": user_id,
            "user_email": user_email,
            "cleanup_details": cleanup_results,
            "warning": "This action cannot be undone. All user data has been permanently deleted."
        }
        
    except Exception as e:
        print(f"❌ User deletion failed: {e}")
        raise HTTPException(status_code=500, detail=f"User deletion failed: {str(e)}")

@router.post("/cleanup/emergency")
async def emergency_cleanup_all_data():
    """
    🚨 EMERGENCY: Delete ALL data from ALL systems
    
    ⚠️ WARNING: This will delete EVERYTHING:
    - All users
    - All memories  
    - All sessions
    - All vector data
    - All graph data
    
    Use only for development/testing when you need a complete reset.
    """
    try:
        from app.services.cleanup_service import cleanup_all_ghost_data
        
        result = await cleanup_all_ghost_data()
        
        return {
            "success": result["status"] == "success",
            "message": "EMERGENCY CLEANUP COMPLETED - ALL DATA DELETED",
            "warning": "This action cannot be undone. All data across all systems has been permanently deleted.",
            "result": result
        }
        
    except Exception as e:
        print(f"❌ Emergency cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency cleanup failed: {str(e)}")

@router.get("/verify/{user_id}")
async def verify_user_exists_mongodb_only(user_id: str):
    """
    🔍 DATABASE-FIRST CHECK: Verify user exists in MongoDB only
    
    This endpoint ONLY checks MongoDB - the single source of truth.
    Use this to verify if a user should have access to memories/data.
    """
    try:
        from app.services.cleanup_service import verify_user_exists_in_mongodb
        
        user = await verify_user_exists_in_mongodb(user_id)
        
        if user:
            return {
                "exists": True,
                "user_id": user_id,
                "email": user.get("email"),
                "name": user.get("name") or user.get("username"),
                "created_at": user.get("createdAt"),
                "message": "User found in MongoDB - memories can be loaded"
            }
        else:
            return {
                "exists": False,
                "user_id": user_id,
                "message": "User NOT found in MongoDB - do not load any memories"
            }
            
    except Exception as e:
        print(f"❌ User verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"User verification failed: {str(e)}")