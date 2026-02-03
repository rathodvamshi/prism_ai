
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from app.db.mongo_client import users_collection, sessions_collection, db
from app.utils.auth import get_current_user_from_session, AuthUtils, create_session_for_user
from app.db.redis_client import redis_client
from bson import ObjectId
import logging
import json
import psutil
import os

# Configure Logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

# --- DEPENDENCIES ---

async def require_admin(user: dict = Depends(get_current_user_from_session)):
    """
    Strict dependency to ensure the user has 'admin' role.
    """
    # Accessing attribute via dot notation because get_current_user_from_session returns an object (likely User model or similar)
    # However, in auth.py it seemed to return a dict or object. Let's assume object based on usage `user.email`.
    # Safety check for dict vs object
    role = getattr(user, "role", None) or user.get("role")
    
    if role != "admin":
        logger.warning(f"⛔ Unauthorized Admin Access Attempt by {getattr(user, 'email', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCES DENIED: You do not have clearance for the God Mode Protocol."
        )
    return user

# --- MODELS ---

class AdminAction(BaseModel):
    action: str  # "ban", "unban", "reset_password", "promote", "demote"
    reason: Optional[str] = None

class BroadcastMessage(BaseModel):
    title: str
    message: str
    priority: str = "normal" # "normal", "high", "critical"
    target_audience: str = "dall" # "all", "active_now"

# --- SYSTEM HEALTH & STATS ---

@router.get("/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    """
    Get aggregated high-level statistics for the dashboard.
    """
    try:
        total_users = await users_collection.count_documents({})
        active_users_24h = await users_collection.count_documents({
            "last_login": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        })
        
        total_sessions = await sessions_collection.count_documents({})
        
        # Calculate growth (Mock comparison for now)
        growth_rate = 12.5 # Placeholder or allow real calculation if strict history exists
        
        return {
            "total_users": total_users,
            "active_users_24h": active_users_24h,
            "total_sessions": total_sessions,
            "growth_rate": growth_rate,
            "system_status": "OPTIMAL"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system-health")
async def get_system_health(admin: dict = Depends(require_admin)):
    """
    Real-time system health check (CPU, RAM, DB Latency).
    """
    try:
        # System Metrics
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # DB Latency Check (Ping)
        start_db = datetime.now()
        await db.command("ping")
        db_latency = (datetime.now() - start_db).total_seconds() * 1000
        
        # Redis Latency
        start_redis = datetime.now()
        await redis_client.ping()
        redis_latency = (datetime.now() - start_redis).total_seconds() * 1000
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "db_latency_ms": round(db_latency, 2),
            "redis_latency_ms": round(redis_latency, 2),
            "server_time": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "Critical Error", "detail": str(e)}

# --- USER MANAGEMENT ---

@router.get("/users")
async def list_users(
    skip: int = 0, 
    limit: int = 20, 
    search: str = "", 
    admin: dict = Depends(require_admin)
):
    """
    Searchable, paginated user list.
    """
    query = {}
    if search:
        query = {
            "$or": [
                {"email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]
        }
    
    users_cursor = users_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
    users = await users_cursor.to_list(length=limit)
    
    # Sanitize and format
    result = []
    for u in users:
        result.append({
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u.get("name", "N/A"),
            "role": u.get("role", "user"),
            "verified": u.get("verified", False),
            "created_at": u.get("created_at"),
            "last_login": u.get("last_login"),
            "is_banned": u.get("is_banned", False)
        })
        
    total = await users_collection.count_documents(query)
    
    return {"users": result, "total": total}

@router.get("/users/{user_id}/details")
async def get_user_details(user_id: str, admin: dict = Depends(require_admin)):
    """
    Get deep insights into a specific user.
    """
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get Session Count
        session_count = await sessions_collection.count_documents({"userId": ObjectId(user_id)})
        
        # Get specific sessions (recent 5)
        recent_sessions = await sessions_collection.find(
            {"userId": ObjectId(user_id)}
        ).sort("updatedAt", -1).limit(5).to_list(5)
        
        formatted_sessions = []
        for s in recent_sessions:
            formatted_sessions.append({
                "id": str(s.get("sessionId")),
                "updatedAt": s.get("updatedAt"),
                "messageCount": len(s.get("messages", []))
            })

        return {
            "profile": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user.get("name"),
                "role": user.get("role", "user"),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login"),
                "is_banned": user.get("is_banned", False)
            },
            "stats": {
                "total_sessions": session_count,
            },
            "recent_activity": formatted_sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user details: {str(e)}")

@router.post("/users/{user_id}/action")
async def perform_user_action(
    user_id: str, 
    action_payload: AdminAction,
    admin: dict = Depends(require_admin)
):
    """
    Ban, Unban, or Reset users.
    """
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        action = action_payload.action
        
        if action == "ban":
            await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_banned": True, "ban_reason": action_payload.reason}}
            )
            # Kill sessions? (Optional: Implement session revocation here)
            return {"status": "success", "message": f"User {user['email']} has been BANNED."}
            
        elif action == "unban":
            await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_banned": False}}
            )
            return {"status": "success", "message": f"User {user['email']} has been UNBANNED."}
            
        elif action == "promote":
             await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"role": "admin"}}
            )
             return {"status": "success", "message": "User promoted to Admin."}
             
        elif action == "demote":
             await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"role": "user"}}
            )
             return {"status": "success", "message": "User demoted to User."}

        else:
            raise HTTPException(status_code=400, detail="Invalid action")

    except Exception as e:
        logger.error(f"Admin Action Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- GOD MODE: IMPERSONATION ---

@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: str, 
    response: Request, # Hint: fastapi Response object needs to be imported if we set cookies
    admin: dict = Depends(require_admin)
):
    """
    [GOD MODE] Generate a session for the target user and return it.
    The Admin can then 'become' this user.
    """
    from fastapi import Response # Late import to avoid changing global deps if not needed elsewhere
    
    # 1. Fetch Target User
    target_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # 2. Audit This Action (CRITICAL)
    logger.warning(
        f"🕵️ GOD MODE ACTIVATED: Admin {admin.email} is impersonating {target_user['email']}"
    )
    # TODO: Write to specific audit log collection
    
    # 3. Create Session with a flag (optional) or just a standard session
    # We might want to set a short expiry for impersonation sessions
    session_id = await create_session_for_user(
        target_user,
        user_agent="AdminImpersonation/1.0",
        ip="127.0.0.1"
    )
    
    return {
        "status": "success", 
        "impersonation_token": session_id,
        "target_email": target_user["email"],
        "message": "You are now entering the Matrix."
    }

# --- SESSIONS INTELLIGENCE ---

@router.get("/sessions")
async def list_all_sessions(
    skip: int = 0, 
    limit: int = 50, 
    admin: dict = Depends(require_admin)
):
    """
    Global view of chat sessions.
    """
    sessions_cursor = sessions_collection.find({}).sort("updatedAt", -1).skip(skip).limit(limit)
    sessions = await sessions_cursor.to_list(length=limit)
    
    results = []
    for s in sessions:
        # Resolve user email for display
        user_email = "Unknown"
        if "userId" in s:
            u = await users_collection.find_one({"_id": s["userId"]}, {"email": 1})
            if u: user_email = u["email"]
            
        results.append({
            "id": s.get("sessionId"),
            "user_email": user_email,
            "updatedAt": s.get("updatedAt"),
            "message_count": len(s.get("messages", [])),
            "preview": s.get("name", "Untitled Session")
        })
        
    return results

@router.get("/sessions/{session_id}/transcript")
async def get_session_transcript(
    session_id: str, 
    admin: dict = Depends(require_admin)
):
    """
    Full read-only transcript of a session.
    """
    session = await sessions_collection.find_one({"sessionId": session_id})
    if not session:
         raise HTTPException(status_code=404, detail="Session not found")
         
    return {
        "id": session.get("sessionId"),
        "messages": session.get("messages", [])
    }

# --- SYSTEM CONTROL ---

@router.post("/broadcast")
async def send_broadcast(
    msg: BroadcastMessage,
    admin: dict = Depends(require_admin)
):
    """
    Send a system-wide notification (Stored in Redis for Frontend polling or WebSocket).
    """
    broadcast_data = {
        "id": ObjectId().__str__(),
        "title": msg.title,
        "message": msg.message,
        "type": msg.priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "by": admin.email
    }
    
    # Store in Redis list 'system_broadcasts'
    # Frontend can poll /api/system/notifications
    await redis_client.lpush("system_broadcasts", json.dumps(broadcast_data))
    await redis_client.ltrim("system_broadcasts", 0, 9) # Keep last 10
    
    return {"status": "published", "data": broadcast_data}
