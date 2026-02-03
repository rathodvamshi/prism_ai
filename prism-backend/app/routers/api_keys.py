"""
🔑 API KEYS MANAGEMENT ROUTER (ADVANCED)

Features:
- Free usage limit tracking (10 requests/day)
- User API key management (BYOK - Bring Your Own Key)
- API key rotation (automatic switch when exhausted)
- Daily reset handling (smart date tracking)
- Up to 5 API keys per user
- Priority ordering for key rotation
- Per-key usage analytics
- Countdown timer for reset
- Key health validation

Security:
- Keys are encrypted at rest using Fernet
- Keys are never sent back to frontend (masked only)
- Keys never appear in logs
- Duplicate detection via SHA256 hash
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from datetime import datetime, date, timedelta
from bson import ObjectId
import logging
import hashlib
import asyncio

from cryptography.fernet import Fernet
import json as json_module  # For Redis caching

from app.db.mongo_client import db, mongo_retry
from app.utils.auth import get_current_user_from_session
from app.config import settings
from app.db.redis_client import get_redis_client  # For caching API key lookups

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Keys Management"])

# Collections
api_keys_collection = db.api_keys
usage_collection = db.usage_tracking

# Encryption key (should be in env vars in production)
def _get_fernet_key():
    """Get or generate a valid Fernet encryption key."""
    key = getattr(settings, 'ENCRYPTION_KEY', None) or getattr(settings, 'API_KEY_ENCRYPTION_KEY', None)
    
    if key:
        try:
            # Try to use the existing key
            if isinstance(key, str):
                key = key.encode()
            # Validate by trying to create Fernet with it
            Fernet(key)
            return key
        except Exception as e:
            logger.warning(f"⚠️ Invalid ENCRYPTION_KEY in env: {e}. Generating new key.")
    
    # Generate a new key if none exists or invalid
    new_key = Fernet.generate_key()
    logger.warning("⚠️ Using generated encryption key. Set ENCRYPTION_KEY in production!")
    return new_key

ENCRYPTION_KEY = _get_fernet_key()
fernet = Fernet(ENCRYPTION_KEY)

# ============ CONSTANTS ============
FREE_REQUEST_LIMIT = 50  # Free tier: 50 requests/day, then user needs own API key
MAX_API_KEYS_PER_USER = 5
SUPPORTED_PROVIDERS = ["groq"]
SUPPORTED_MODELS = {
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-11b-vision-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
}

# ============ ERROR CODES ============
class ErrorCodes:
    FREE_LIMIT_EXCEEDED = "FREE_LIMIT_EXCEEDED"
    ALL_KEYS_EXHAUSTED = "ALL_KEYS_EXHAUSTED"
    MAX_KEYS_REACHED = "MAX_KEYS_REACHED"
    INVALID_KEY = "INVALID_KEY"
    DUPLICATE_KEY = "DUPLICATE_KEY"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"


# ============ MODELS ============

class AddApiKeyRequest(BaseModel):
    provider: str = Field(default="groq", description="API provider")
    model: str = Field(default="llama-3.1-8b-instant", description="Model to use")
    api_key: str = Field(..., description="The API key")
    label: Optional[str] = Field(None, description="Optional label (e.g., 'Primary', 'Backup')")
    priority: Optional[int] = Field(None, description="Priority order (1 = highest, used first)")


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    model: str
    label: str
    masked_key: str
    is_active: bool
    is_exhausted_today: bool
    is_valid: bool = True  # For health check results
    last_exhausted_at: Optional[str] = None
    created_at: str
    last_used: Optional[str] = None
    priority: int = 1
    requests_today: int = 0  # Per-key usage tracking


class UsageStatsResponse(BaseModel):
    free_requests_used: int
    free_limit: int
    free_requests_remaining: int
    has_personal_keys: bool
    active_keys_count: int
    exhausted_keys_count: int
    total_keys_count: int
    max_keys_allowed: int
    can_make_requests: bool
    current_key_source: str  # "platform", "user", or "none"
    active_key_label: Optional[str] = None
    # New fields for enhanced UX
    warning_level: Optional[str] = None  # "low" (80%), "critical" (90%), None
    reset_time_seconds: Optional[int] = None  # Seconds until midnight UTC
    reset_time_formatted: Optional[str] = None  # Human readable "4h 23m"
    total_requests_today: int = 0  # Total across all keys


class ValidateKeyRequest(BaseModel):
    provider: str = Field(default="groq")
    model: str = Field(default="llama-3.1-8b-instant")
    api_key: str


class ValidateKeyResponse(BaseModel):
    valid: bool
    message: str
    warning: Optional[str] = None


class DashboardResponse(BaseModel):
    usage: UsageStatsResponse
    keys: List[ApiKeyResponse]
    messages: List[str]  # Info/warning messages for user


# ============ HELPER FUNCTIONS ============

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for use"""
    return fernet.decrypt(encrypted_key.encode()).decode()


def mask_api_key(api_key: str) -> str:
    """Mask API key for display (e.g., gsk_****abcd)"""
    if len(api_key) <= 8:
        return "****" + api_key[-4:] if len(api_key) > 4 else "****"
    return api_key[:4] + "****" + api_key[-4:]


def hash_api_key(api_key: str) -> str:
    """Hash API key for duplicate detection"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_today_str() -> str:
    """Get today's date as ISO string for comparison"""
    return date.today().isoformat()


def get_seconds_until_midnight_utc() -> Tuple[int, str]:
    """
    Calculate seconds until midnight UTC for countdown timer.
    Returns: (seconds, formatted_string like "4h 23m")
    """
    now = datetime.utcnow()
    midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    delta = midnight - now
    total_seconds = int(delta.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        formatted = f"{hours}h {minutes}m"
    else:
        formatted = f"{minutes}m"
    
    return total_seconds, formatted


async def validate_groq_key(api_key: str, model: str = "llama-3.1-8b-instant") -> dict:
    """
    Validate a Groq API key by making a minimal test request.
    Returns: {"valid": bool, "message": str, "warning": str|None}
    """
    from groq import AsyncGroq
    import asyncio
    
    try:
        client = AsyncGroq(api_key=api_key)
        
        # Make a minimal test request (ping)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            ),
            timeout=10.0
        )
        
        return {"valid": True, "message": "✅ API key is valid and working!", "warning": None}
        
    except Exception as e:
        error_str = str(e).lower()
        
        if "401" in error_str or "invalid" in error_str or "authentication" in error_str:
            return {"valid": False, "message": "❌ Invalid API key. Please check and try again.", "warning": None}
        elif "404" in error_str or "model" in error_str:
            return {"valid": False, "message": f"❌ Model '{model}' not supported with this key.", "warning": None}
        elif "429" in error_str or "rate" in error_str or "quota" in error_str:
            # Key is valid but has low quota - still accept it
            return {"valid": True, "message": "✅ API key is valid!", "warning": "⚠️ This key has low quota or is rate limited. It may exhaust quickly."}
        elif "403" in error_str or "permission" in error_str:
            return {"valid": False, "message": "❌ API key lacks required permissions.", "warning": None}
        else:
            logger.error(f"API key validation error: {e}")
            return {"valid": False, "message": f"❌ Validation failed: {str(e)[:80]}", "warning": None}


async def reset_exhausted_keys_if_new_day(user_id: str):
    """
    Check if any exhausted keys can be reset (new day).
    Groq resets limits daily, so we just check the date.
    
    OPTIMIZED: Uses Redis to track last reset check to avoid hitting MongoDB on every request.
    """
    today = get_today_str()
    
    # Use Redis to check if we already ran this today for this user
    try:
        redis_client = await get_redis_client()
        cache_key = f"key_reset_check:{user_id}:{today}"
        
        # If we already checked today, skip the MongoDB call
        if await redis_client.exists(cache_key):
            return
        
        # Mark as checked for today (expires at midnight + 1 hour buffer)
        await redis_client.set(cache_key, "1", ex=86400)  # 24 hours
    except Exception as e:
        logger.warning(f"Redis cache unavailable for reset check: {e}")
        # Continue without cache - will hit MongoDB
    
    # Find keys exhausted on a previous day and reset them
    result = await api_keys_collection.update_many(
        {
            "user_id": user_id,
            "is_exhausted_today": True,
            "last_exhausted_date": {"$ne": today}
        },
        {
            "$set": {
                "is_exhausted_today": False
            }
        }
    )
    
    if result.modified_count > 0:
        logger.info(f"♻️ Reset {result.modified_count} exhausted keys for user {user_id[:8]}... (new day)")


async def mark_key_exhausted(key_id: ObjectId, user_id: str = None):
    """
    Mark an API key as exhausted for today.
    
    🚀 OPTIMIZED: Invalidates Redis cache after update
    """
    today = get_today_str()
    
    # Get user_id if not provided (for cache invalidation)
    if not user_id:
        key = await api_keys_collection.find_one({"_id": key_id}, {"user_id": 1})
        user_id = key.get("user_id") if key else None
    
    await api_keys_collection.update_one(
        {"_id": key_id},
        {
            "$set": {
                "is_exhausted_today": True,
                "last_exhausted_date": today,
                "last_exhausted_at": datetime.utcnow()
            }
        }
    )
    
    # Invalidate cache so next request gets fresh data
    if user_id:
        try:
            redis_client = await get_redis_client()
            await redis_client.delete(f"user_keys:{user_id}")
        except Exception:
            pass
    
    logger.info(f"⚠️ API key {key_id} marked as exhausted for today")


async def get_next_available_key(user_id: str, exclude_key_id: ObjectId = None) -> dict | None:
    """
    Find the next available (non-exhausted) key for user.
    
    🚀 OPTIMIZED:
    - Uses Redis cache for key list (avoids DB on every request)
    - Priority ordering: lowest priority number = used first
    - Automatic rotation: if key exhausted, moves to next
    - Maximum 5 keys per user
    
    Returns the key document or None.
    """
    import time
    start = time.time()
    
    # 🚀 FAST PATH: Try Redis cache first
    try:
        redis_client = await get_redis_client()
        cache_key = f"user_keys:{user_id}"
        cached = await redis_client.get(cache_key)
        
        if cached:
            keys_data = json_module.loads(cached)
            # Find first non-exhausted key
            for key_data in keys_data:
                if not key_data.get("is_exhausted_today", False):
                    if exclude_key_id and str(key_data["_id"]) == str(exclude_key_id):
                        continue
                    # Return full key from DB (we need encrypted_key)
                    key = await api_keys_collection.find_one({"_id": ObjectId(key_data["_id"])})
                    if key and not key.get("is_exhausted_today", False):
                        logger.debug(f"⚡ Key lookup from cache [{(time.time()-start)*1000:.0f}ms]")
                        return key
    except Exception as e:
        logger.warning(f"Redis cache miss for keys: {e}")
    
    # 🐢 SLOW PATH: Query MongoDB
    query = {
        "user_id": user_id,
        "is_exhausted_today": {"$ne": True}
    }
    
    if exclude_key_id:
        query["_id"] = {"$ne": exclude_key_id}
    
    # Get keys ordered by priority (ascending), then creation date
    key = await api_keys_collection.find_one(query, sort=[("priority", 1), ("created_at", 1)])
    
    # Update cache with all user keys (for future lookups)
    try:
        all_keys = await api_keys_collection.find({"user_id": user_id}).sort([("priority", 1)]).to_list(5)
        if all_keys:
            cache_data = [{"_id": str(k["_id"]), "priority": k.get("priority", 999), "is_exhausted_today": k.get("is_exhausted_today", False)} for k in all_keys]
            await redis_client.set(f"user_keys:{user_id}", json_module.dumps(cache_data), ex=60)  # 1 min cache
    except Exception:
        pass
    
    logger.debug(f"🔍 Key lookup from DB [{(time.time()-start)*1000:.0f}ms]")
    return key


async def activate_key(key_id: ObjectId, user_id: str):
    """
    Activate a specific key and deactivate others.
    
    🚀 OPTIMIZED: Uses bulk_write for single round-trip to DB
    """
    from pymongo import UpdateMany, UpdateOne
    
    # Single bulk operation instead of 2 separate calls
    await api_keys_collection.bulk_write([
        UpdateMany({"user_id": user_id}, {"$set": {"is_active": False}}),
        UpdateOne({"_id": key_id}, {"$set": {"is_active": True}})
    ], ordered=True)
    
    # Invalidate cache
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(f"user_keys:{user_id}")
    except Exception:
        pass


# ============ ENDPOINTS ============

# 🚀 CACHE TTL for usage stats (seconds) - INCREASED for better performance
USAGE_CACHE_TTL = 30  # 🔧 Increased from 10s to 30s - reduces DB load by 3x
USAGE_EXTENDED_CACHE_TTL = 60  # For users with no recent changes

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(current_user = Depends(get_current_user_from_session)):
    """
    Get user's usage statistics including free requests remaining.
    Uses retry logic for MongoDB connection resilience.
    🚀 CACHED: Results cached in Redis for 30s to reduce DB load.
    """
    user_id = current_user.user_id
    today = get_today_str()
    cache_key = f"usage_stats:{user_id}:{today}"
    
    # 🚀 TRY CACHE FIRST
    try:
        redis_client = await get_redis_client()
        cached = await redis_client.get(cache_key)
        if cached:
            cached_data = json_module.loads(cached)
            return UsageStatsResponse(**cached_data)
    except Exception:
        pass  # Cache miss or error, continue to DB
    
    try:
        # 🚀 PARALLEL PRE-FLIGHT: Fetch usage/keys in one go
        # Optimized: Use projection for keys to fetch only what we need (speed boost)
        keys_projection = {
            "is_exhausted_today": 1, 
            "is_active": 1, 
            "requests_today": 1, 
            "label": 1, 
            "priority": 1
        }
        
        # Fire-and-forget the reset check to avoid blocking the response
        # Reset keys if new day (Fast check)
        await reset_exhausted_keys_if_new_day(user_id)
        
        # 🛡️ SEQUENTIAL EXECUTION (Fixes "coroutine expected, got Future" error in some environments)
        usage = await usage_collection.find_one({"user_id": user_id})
        all_keys = await api_keys_collection.find({"user_id": user_id}, keys_projection).to_list(100)
        
        if not usage:
            usage = {
                "user_id": user_id,
                "free_requests_used": 0,
                "free_limit": FREE_REQUEST_LIMIT,
                "last_reset_date": today,
                "created_at": datetime.utcnow()
            }
            # Background insert to save time
            asyncio.create_task(usage_collection.insert_one(usage))
        else:
            # Check if we need to reset free usage (new day)
            last_reset = usage.get("last_reset_date", "")
            if last_reset != today:
                asyncio.create_task(usage_collection.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "free_requests_used": 0,
                            "last_reset_date": today,
                            "last_reset_at": datetime.utcnow(),
                            "counted_generation_ids": []
                        }
                    }
                ))
                usage["free_requests_used"] = 0
        
        total_keys = len(all_keys)
        exhausted_keys = sum(1 for k in all_keys if k.get("is_exhausted_today", False))
        active_keys = total_keys - exhausted_keys
        
        # Calculate total requests today across all keys
        total_requests_today = sum(k.get("requests_today", 0) for k in all_keys)
        
        # Find active key (handling possibility of multiple actives gracefully)
        active_key = next((k for k in all_keys if k.get("is_active", False)), None)
        
        free_used = usage.get("free_requests_used", 0) if usage else 0
        free_remaining = max(0, FREE_REQUEST_LIMIT - free_used)
        has_keys = total_keys > 0
        
        # Determine current key source
        if free_remaining > 0:
            current_source = "platform"
        elif active_keys > 0:
            current_source = "user"
        else:
            current_source = "none"
        
        can_make = current_source != "none"
        
        # Calculate warning level for free usage
        warning_level = None
        usage_percentage = (free_used / FREE_REQUEST_LIMIT) * 100 if FREE_REQUEST_LIMIT > 0 else 0
        if usage_percentage >= 90:
            warning_level = "critical"
        elif usage_percentage >= 80:
            warning_level = "low"
        
        # Get countdown timer (only relevant if there are exhausted keys or high usage)
        reset_seconds, reset_formatted = None, None
        if exhausted_keys > 0 or warning_level:
            reset_seconds, reset_formatted = get_seconds_until_midnight_utc()
        
        response_data = UsageStatsResponse(
            free_requests_used=free_used,
            free_limit=FREE_REQUEST_LIMIT,
            free_requests_remaining=free_remaining,
            has_personal_keys=has_keys,
            active_keys_count=active_keys,
            exhausted_keys_count=exhausted_keys,
            total_keys_count=total_keys,
            max_keys_allowed=MAX_API_KEYS_PER_USER,
            can_make_requests=can_make,
            current_key_source=current_source,
            active_key_label=active_key.get("label") if active_key else None,
            warning_level=warning_level,
            reset_time_seconds=reset_seconds,
            reset_time_formatted=reset_formatted,
            total_requests_today=total_requests_today + free_used
        )
        
        # 🚀 CACHE THE RESPONSE (10s TTL)
        try:
            redis_client = await get_redis_client()
            await redis_client.setex(
                cache_key, 
                USAGE_CACHE_TTL, 
                json_module.dumps(response_data.model_dump())
            )
        except Exception:
            pass  # Cache write failure is non-critical
        
        return response_data
    except Exception as e:
        # Graceful degradation - return default stats if DB is temporarily unavailable
        logger.error(f"❌ get_usage_stats error (returning defaults): {e}")
        return UsageStatsResponse(
            free_requests_used=0,
            free_limit=FREE_REQUEST_LIMIT,
            free_requests_remaining=FREE_REQUEST_LIMIT,
            has_personal_keys=False,
            active_keys_count=0,
            exhausted_keys_count=0,
            total_keys_count=0,
            max_keys_allowed=MAX_API_KEYS_PER_USER,
            can_make_requests=True,
            current_key_source="platform",
            active_key_label=None,
            warning_level=None,
            reset_time_seconds=None,
            reset_time_formatted=None,
            total_requests_today=0
        )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(current_user = Depends(get_current_user_from_session)):
    """
    Get full dashboard with usage stats, keys, and messages.
    """
    user_id = current_user.user_id
    
    # Reset exhausted keys if new day
    await reset_exhausted_keys_if_new_day(user_id)
    
    # Get usage stats (reuse the endpoint logic)
    usage = await get_usage_stats(current_user)
    
    # Get keys
    keys = await list_api_keys(current_user)
    
    # Generate helpful messages
    messages = []
    
    if usage.free_requests_remaining == 0 and usage.total_keys_count == 0:
        messages.append("⚠️ Free limit reached. Add your Groq API key to continue chatting!")
    elif usage.free_requests_remaining <= 5 and usage.free_requests_remaining > 0:
        messages.append(f"📊 Only {usage.free_requests_remaining} free requests left. Consider adding a backup API key.")
    
    if usage.exhausted_keys_count > 0:
        messages.append(f"⏳ {usage.exhausted_keys_count} key(s) are exhausted today. Limits reset tomorrow automatically.")
    
    if usage.total_keys_count >= MAX_API_KEYS_PER_USER:
        messages.append(f"📋 Maximum keys ({MAX_API_KEYS_PER_USER}) reached. Delete a key to add new ones.")
    
    if usage.current_key_source == "user" and usage.active_key_label:
        messages.append(f"🔑 Currently using: {usage.active_key_label}")
    
    return DashboardResponse(
        usage=usage,
        keys=keys,
        messages=messages
    )


@router.get("/keys", response_model=List[ApiKeyResponse])
async def list_api_keys(current_user = Depends(get_current_user_from_session)):
    """
    List all API keys for the current user (masked).
    """
    user_id = current_user.user_id
    
    # Reset exhausted keys if new day
    await reset_exhausted_keys_if_new_day(user_id)
    
    # Also reset daily request counters if new day
    today = get_today_str()
    await api_keys_collection.update_many(
        {
            "user_id": user_id,
            "last_request_date": {"$ne": today}
        },
        {
            "$set": {"requests_today": 0, "last_request_date": today}
        }
    )
    
    keys = await api_keys_collection.find({"user_id": user_id}).sort([("priority", 1), ("created_at", 1)]).to_list(100)
    
    result = []
    for key in keys:
        try:
            decrypted = decrypt_api_key(key["encrypted_key"])
            masked = mask_api_key(decrypted)
        except:
            masked = "****error****"
        
        result.append(ApiKeyResponse(
            id=str(key["_id"]),
            provider=key["provider"],
            model=key.get("model", "llama-3.1-8b-instant"),
            label=key.get("label", "My API Key"),
            masked_key=masked,
            is_active=key.get("is_active", False),
            is_exhausted_today=key.get("is_exhausted_today", False),
            is_valid=key.get("is_valid", True),
            last_exhausted_at=key.get("last_exhausted_at").isoformat() if key.get("last_exhausted_at") else None,
            created_at=key["created_at"].isoformat() if isinstance(key["created_at"], datetime) else key["created_at"],
            last_used=key.get("last_used").isoformat() if key.get("last_used") else None,
            priority=key.get("priority", 1),
            requests_today=key.get("requests_today", 0)
        ))
    
    return result


@router.post("/validate", response_model=ValidateKeyResponse)
async def validate_api_key(request: ValidateKeyRequest):
    """
    Validate an API key before saving.
    Makes a test request to verify the key works.
    """
    # Validate provider
    if request.provider not in SUPPORTED_PROVIDERS:
        return ValidateKeyResponse(
            valid=False,
            message=f"❌ Unsupported provider: {request.provider}. Use: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    
    # Validate model
    if request.model not in SUPPORTED_MODELS.get(request.provider, []):
        return ValidateKeyResponse(
            valid=False,
            message=f"❌ Unsupported model: {request.model}"
        )
    
    # Basic format validation
    if not request.api_key or len(request.api_key.strip()) < 10:
        return ValidateKeyResponse(
            valid=False,
            message="❌ API key is too short or empty."
        )
    
    api_key = request.api_key.strip()
    
    # Groq keys typically start with "gsk_"
    if request.provider == "groq" and not api_key.startswith("gsk_"):
        return ValidateKeyResponse(
            valid=False,
            message="❌ Groq API keys should start with 'gsk_'. Please check your key."
        )
    
    # Live validation
    result = await validate_groq_key(api_key, request.model)
    
    return ValidateKeyResponse(
        valid=result["valid"],
        message=result["message"],
        warning=result["warning"]
    )


@router.post("/keys", response_model=ApiKeyResponse)
async def add_api_key(request: AddApiKeyRequest, current_user = Depends(get_current_user_from_session)):
    """
    Add a new API key for the user.
    Validates the key, checks for duplicates, max limit, and stores encrypted.
    """
    user_id = current_user.user_id
    api_key = request.api_key.strip()
    
    # Check max keys limit
    existing_count = await api_keys_collection.count_documents({"user_id": user_id})
    if existing_count >= MAX_API_KEYS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCodes.MAX_KEYS_REACHED,
                "message": f"❌ Maximum API keys ({MAX_API_KEYS_PER_USER}) reached. Please delete one to add a new key."
            }
        )
    
    # Validate provider and model
    if request.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_PROVIDER", "message": f"❌ Unsupported provider: {request.provider}"}
        )
    
    if request.model not in SUPPORTED_MODELS.get(request.provider, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_MODEL", "message": f"❌ Unsupported model: {request.model}"}
        )
    
    # Format validation
    if not api_key or len(api_key) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": ErrorCodes.INVALID_KEY, "message": "❌ API key is too short."}
        )
    
    if request.provider == "groq" and not api_key.startswith("gsk_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": ErrorCodes.INVALID_KEY, "message": "❌ Groq keys must start with 'gsk_'"}
        )
    
    # Check for duplicate key (using hash)
    key_hash = hash_api_key(api_key)
    existing = await api_keys_collection.find_one({
        "user_id": user_id,
        "key_hash": key_hash
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": ErrorCodes.DUPLICATE_KEY, "message": "❌ This API key has already been added to your account."}
        )
    
    # Validate the key with live request
    validation = await validate_groq_key(api_key, request.model)
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": ErrorCodes.INVALID_KEY, "message": validation["message"]}
        )
    
    # Determine if this should be the active key
    # If no active key exists, or all existing are exhausted, make this active
    active_key = await api_keys_collection.find_one({
        "user_id": user_id,
        "is_active": True,
        "is_exhausted_today": {"$ne": True}
    })
    
    should_activate = active_key is None
    
    if should_activate:
        # Deactivate all other keys
        await api_keys_collection.update_many(
            {"user_id": user_id},
            {"$set": {"is_active": False}}
        )
    
    # Encrypt and store the key
    encrypted_key = encrypt_api_key(api_key)
    
    # Determine priority - if not provided, put at end
    if request.priority is not None:
        priority = request.priority
    else:
        # Get highest priority number and add 1
        highest = await api_keys_collection.find_one(
            {"user_id": user_id},
            sort=[("priority", -1)]
        )
        priority = (highest.get("priority", 0) + 1) if highest else 1
    
    key_doc = {
        "user_id": user_id,
        "provider": request.provider,
        "model": request.model,
        "encrypted_key": encrypted_key,
        "key_hash": key_hash,
        "label": request.label or f"Key #{existing_count + 1}",
        "is_active": should_activate,
        "is_exhausted_today": False,
        "is_valid": True,
        "last_exhausted_date": None,
        "last_exhausted_at": None,
        "created_at": datetime.utcnow(),
        "last_used": None,
        "priority": priority,
        "requests_today": 0,
        "last_request_date": get_today_str()
    }
    
    result = await api_keys_collection.insert_one(key_doc)
    
    # 🚀 Invalidate cache so new key is immediately available
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(f"user_keys:{user_id}")
    except Exception:
        pass
    
    logger.info(f"✅ API key added for user {user_id[:8]}... (label: {key_doc['label']}, active: {should_activate}, priority: {priority})")
    
    return ApiKeyResponse(
        id=str(result.inserted_id),
        provider=request.provider,
        model=request.model,
        label=key_doc["label"],
        masked_key=mask_api_key(api_key),
        is_active=should_activate,
        is_exhausted_today=False,
        is_valid=True,
        created_at=key_doc["created_at"].isoformat(),
        priority=priority,
        requests_today=0
    )


@router.put("/keys/{key_id}/activate")
async def activate_api_key_endpoint(key_id: str, current_user = Depends(get_current_user_from_session)):
    """
    Set a specific API key as the active key.
    """
    user_id = current_user.user_id
    
    try:
        key_oid = ObjectId(key_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID")
    
    # Verify ownership
    key = await api_keys_collection.find_one({"_id": key_oid, "user_id": user_id})
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": ErrorCodes.KEY_NOT_FOUND, "message": "API key not found"})
    
    # Check if key is exhausted
    if key.get("is_exhausted_today", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail={"error": "KEY_EXHAUSTED", "message": "⚠️ This key is exhausted today. It will reset tomorrow."}
        )
    
    # Activate this key
    await activate_key(key_oid, user_id)
    
    return {"message": f"✅ '{key.get('label', 'API key')}' is now active"}


@router.delete("/keys/{key_id}")
async def delete_api_key(key_id: str, current_user = Depends(get_current_user_from_session)):
    """
    Delete an API key.
    """
    user_id = current_user.user_id
    
    try:
        key_oid = ObjectId(key_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID")
    
    # Get the key before deleting
    key = await api_keys_collection.find_one({"_id": key_oid, "user_id": user_id})
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": ErrorCodes.KEY_NOT_FOUND, "message": "API key not found"})
    
    was_active = key.get("is_active", False)
    
    # Delete the key
    await api_keys_collection.delete_one({"_id": key_oid})
    
    # 🚀 Invalidate cache
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(f"user_keys:{user_id}")
    except Exception:
        pass
    
    logger.info(f"🗑️ API key deleted for user {user_id[:8]}... (label: {key.get('label')})")
    
    # If deleted key was active, activate next available key
    if was_active:
        next_key = await get_next_available_key(user_id)
        if next_key:
            await activate_key(next_key["_id"], user_id)
            return {"message": f"✅ Key deleted. Switched to '{next_key.get('label', 'next key')}'"}
    
    return {"message": "✅ API key deleted successfully"}


class ReorderKeysRequest(BaseModel):
    key_ids: List[str] = Field(..., description="List of key IDs in desired priority order (first = highest priority)")


@router.put("/keys/reorder")
async def reorder_api_keys(request: ReorderKeysRequest, current_user = Depends(get_current_user_from_session)):
    """
    Reorder API keys by priority.
    The order in key_ids list determines priority (first = highest = 1).
    """
    user_id = current_user.user_id
    
    # Verify all keys belong to user
    for idx, key_id in enumerate(request.key_ids):
        try:
            key_oid = ObjectId(key_id)
            key = await api_keys_collection.find_one({"_id": key_oid, "user_id": user_id})
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Key {key_id} not found or doesn't belong to you"
                )
            
            # Update priority (1-indexed, so first item is priority 1)
            await api_keys_collection.update_one(
                {"_id": key_oid},
                {"$set": {"priority": idx + 1}}
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid key ID: {key_id}")
    
    # 🚀 Invalidate cache after reorder
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(f"user_keys:{user_id}")
    except Exception:
        pass
    
    logger.info(f"🔄 Reordered {len(request.key_ids)} keys for user {user_id[:8]}...")
    return {"message": "✅ Keys reordered successfully"}


@router.post("/keys/{key_id}/health-check")
async def health_check_key(key_id: str, current_user = Depends(get_current_user_from_session)):
    """
    Validate a stored API key is still working.
    Makes a live test request to the provider.
    """
    user_id = current_user.user_id
    
    try:
        key_oid = ObjectId(key_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID")
    
    key = await api_keys_collection.find_one({"_id": key_oid, "user_id": user_id})
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    try:
        decrypted = decrypt_api_key(key["encrypted_key"])
        model = key.get("model", "llama-3.1-8b-instant")
        
        # Validate with live request
        result = await validate_groq_key(decrypted, model)
        
        # Update key's validity status
        await api_keys_collection.update_one(
            {"_id": key_oid},
            {"$set": {"is_valid": result["valid"], "last_validated": datetime.utcnow()}}
        )
        
        return {
            "valid": result["valid"],
            "message": result["message"],
            "warning": result["warning"],
            "label": key.get("label", "API Key")
        }
    except Exception as e:
        logger.error(f"Health check failed for key {key_id}: {e}")
        await api_keys_collection.update_one(
            {"_id": key_oid},
            {"$set": {"is_valid": False, "last_validated": datetime.utcnow()}}
        )
        return {
            "valid": False,
            "message": f"❌ Health check failed: {str(e)[:50]}",
            "label": key.get("label", "API Key")
        }


@router.post("/keys/health-check-all")
async def health_check_all_keys(current_user = Depends(get_current_user_from_session)):
    """
    Validate all stored API keys.
    Returns status for each key.
    """
    user_id = current_user.user_id
    
    keys = await api_keys_collection.find({"user_id": user_id}).to_list(100)
    
    if not keys:
        return {"results": [], "message": "No API keys to check"}
    
    results = []
    for key in keys:
        try:
            decrypted = decrypt_api_key(key["encrypted_key"])
            model = key.get("model", "llama-3.1-8b-instant")
            
            validation = await validate_groq_key(decrypted, model)
            
            await api_keys_collection.update_one(
                {"_id": key["_id"]},
                {"$set": {"is_valid": validation["valid"], "last_validated": datetime.utcnow()}}
            )
            
            results.append({
                "id": str(key["_id"]),
                "label": key.get("label", "API Key"),
                "valid": validation["valid"],
                "message": validation["message"]
            })
        except Exception as e:
            await api_keys_collection.update_one(
                {"_id": key["_id"]},
                {"$set": {"is_valid": False, "last_validated": datetime.utcnow()}}
            )
            results.append({
                "id": str(key["_id"]),
                "label": key.get("label", "API Key"),
                "valid": False,
                "message": f"❌ Error: {str(e)[:50]}"
            })
    
    valid_count = sum(1 for r in results if r["valid"])
    return {
        "results": results,
        "summary": f"✅ {valid_count}/{len(results)} keys are valid"
    }


@router.put("/keys/{key_id}/label")
async def update_key_label(key_id: str, label: str, current_user = Depends(get_current_user_from_session)):
    """
    Update the label/name of an API key.
    """
    user_id = current_user.user_id
    
    try:
        key_oid = ObjectId(key_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID")
    
    key = await api_keys_collection.find_one({"_id": key_oid, "user_id": user_id})
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    await api_keys_collection.update_one(
        {"_id": key_oid},
        {"$set": {"label": label.strip() or "My API Key"}}
    )
    
    return {"message": f"✅ Key renamed to '{label}'"}


@router.get("/providers")
async def get_supported_providers():
    """
    Get list of supported providers and their models.
    """
    return {
        "providers": SUPPORTED_PROVIDERS,
        "models": SUPPORTED_MODELS,
        "default_provider": "groq",
        "default_model": "llama-3.1-8b-instant",
        "max_keys_per_user": MAX_API_KEYS_PER_USER,
        "free_limit": FREE_REQUEST_LIMIT
    }


@router.get("/pool-status")
async def get_pool_status():
    """
    Get status of the platform Groq API key pool.
    Shows usage and availability of each key in the pool.
    
    Returns:
        Pool status with per-key usage stats
    """
    try:
        from app.services.groq_pool import get_groq_pool
        pool = await get_groq_pool()
        status = await pool.get_pool_status()
        return {
            "status": "ok",
            "pool": status
        }
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "pool": None
        }


# ============ INTERNAL FUNCTIONS FOR STREAMING ROUTER ============

async def get_api_key_for_user(user_id: str) -> Tuple[str | None, str, str | None, str]:
    """
    Get the API key to use for a user with automatic rotation.
    
    🎯 BUSINESS LOGIC:
    1. Every user gets 10 FREE requests/day using platform key
    2. After 10 free requests → must use their OWN API key (saved in DB)
    3. If user has no keys and free limit exceeded → error (must add key)
    4. Free counter resets daily at midnight
    
    🚀 ULTRA-OPTIMIZED V3:
    - Redis-first with 90s cache (increased from 60s)
    - Skip reset check if cache hit
    - Parallel cache + platform key return
    - Pipeline Redis operations for <1ms response
    
    Returns: (api_key, source, error_code, model)
        - source: "platform" (free), "user" (own key), or "none" (error)
        - error_code: None if OK, otherwise error code string
        - model: The model to use (defaults to llama-3.1-8b-instant)
    """
    import time
    start_time = time.time()
    
    today = get_today_str()
    
    # 🚀 ULTRA-FAST PATH: Try Redis cache FIRST (skip ALL DB calls on hit)
    try:
        redis_client = await get_redis_client()
        cache_key = f"usage_cache:{user_id}:{today}"  # Include date for auto-invalidation
        cached = await redis_client.get(cache_key)
        
        if cached:
            cached_data = json_module.loads(cached)
            free_used = cached_data.get("free_requests_used", 0)
            # 🚀 INSTANT RETURN on cache hit - ZERO DB calls
            if free_used < FREE_REQUEST_LIMIT:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"🆓 User {user_id[:8]}... using platform key ({FREE_REQUEST_LIMIT - free_used} free left) [{elapsed:.0f}ms]")
                return settings.GROQ_API_KEY, "platform", None, "llama-3.1-8b-instant"
            # Cache hit but limit exceeded - check for user keys in cache
            user_key_data = cached_data.get("user_key")
            if user_key_data:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"🔑 User {user_id[:8]}... using cached OWN key [{elapsed:.0f}ms]")
                return user_key_data["key"], "user", None, user_key_data.get("model", "llama-3.1-8b-instant")
    except Exception as e:
        logger.debug(f"Redis cache miss/error: {e}")
    
    # 🐢 SLOW PATH: Cache miss - check DB (should be rare)
    # Fire-and-forget reset check to not block response
    asyncio.create_task(reset_exhausted_keys_if_new_day(user_id))
    
    # Check MongoDB for usage with minimal projection
    usage = await usage_collection.find_one({"user_id": user_id}, {"free_requests_used": 1, "last_reset_date": 1})
    
    # Handle daily reset inline
    if usage:
        last_reset = usage.get("last_reset_date", "")
        if last_reset != today:
            free_used = 0  # New day = reset
            # Fire-and-forget the DB update
            asyncio.create_task(usage_collection.update_one(
                {"user_id": user_id},
                {"$set": {"free_requests_used": 0, "last_reset_date": today, "counted_generation_ids": []}}
            ))
        else:
            free_used = usage.get("free_requests_used", 0)
    else:
        free_used = 0
    
    # Build cache data for future requests
    cache_data = {"free_requests_used": free_used, "cached_at": time.time()}
    
    # 🚀 Update cache with 90s TTL (date in key auto-invalidates at midnight)
    try:
        redis_client = await get_redis_client()
        await redis_client.set(f"usage_cache:{user_id}:{today}", json_module.dumps(cache_data), ex=90)
    except Exception:
        pass
    
    # 🆓 If free requests remaining → use platform key
    if free_used < FREE_REQUEST_LIMIT:
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"🆓 User {user_id[:8]}... using platform key ({FREE_REQUEST_LIMIT - free_used} free left) [{elapsed:.0f}ms]")
        return settings.GROQ_API_KEY, "platform", None, "llama-3.1-8b-instant"
    
    # 🔑 STEP 2: Free limit exceeded → use user's own API key
    available_key = await get_next_available_key(user_id)
    
    if available_key:
        try:
            decrypted = decrypt_api_key(available_key["encrypted_key"])
            
            # Get user's preferred model from their key config
            user_model = available_key.get("model", "llama-3.1-8b-instant")
            
            # 🚀 Fire-and-forget: Don't wait for activation/update
            async def update_key_usage_background():
                try:
                    # Ensure this key is active
                    if not available_key.get("is_active", False):
                        await activate_key(available_key["_id"], user_id)
                    
                    # Update last_used timestamp
                    update_doc = {
                        "$set": {"last_used": datetime.utcnow(), "last_request_date": today},
                        "$inc": {"requests_today": 1}
                    }
                    if available_key.get("last_request_date") != today:
                        update_doc["$set"]["requests_today"] = 1
                    
                    await api_keys_collection.update_one(
                        {"_id": available_key["_id"]},
                        update_doc
                    )
                except Exception as e:
                    logger.warning(f"Background key update failed: {e}")
            
            asyncio.create_task(update_key_usage_background())
            
            # 🚀 Cache the user key for future requests (avoid DB next time)
            try:
                cache_data["user_key"] = {"key": decrypted, "model": user_model}
                redis_client = await get_redis_client()
                await redis_client.set(f"usage_cache:{user_id}:{today}", json_module.dumps(cache_data), ex=90)
            except Exception:
                pass
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"🔑 User {user_id[:8]}... using OWN key + model {user_model} [{elapsed:.0f}ms]")
            return decrypted, "user", None, user_model
            
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            asyncio.create_task(mark_key_exhausted(available_key["_id"], user_id))
            # Try next key recursively
            return await get_api_key_for_user(user_id)
    
    # 🚫 STEP 3: Check why no key available
    has_any_keys = await api_keys_collection.count_documents({"user_id": user_id}) > 0
    elapsed = (time.time() - start_time) * 1000
    
    if has_any_keys:
        # User HAS keys but ALL are exhausted today
        logger.warning(f"⚠️ User {user_id[:8]}... all keys exhausted [{elapsed:.0f}ms]")
        return None, "none", ErrorCodes.ALL_KEYS_EXHAUSTED, None
    else:
        # User has NO keys and free limit exceeded
        logger.warning(f"⚠️ User {user_id[:8]}... free limit exceeded, no keys [{elapsed:.0f}ms]")
        return None, "none", ErrorCodes.FREE_LIMIT_EXCEEDED, None


async def handle_key_exhaustion(user_id: str, current_key_id: str | None = None) -> Tuple[str | None, str | None]:
    """
    Handle when current key hits rate limit/quota.
    Marks current key exhausted and switches to next.
    
    Returns: (new_api_key, error_code)
    """
    if current_key_id:
        try:
            await mark_key_exhausted(ObjectId(current_key_id), user_id)
        except:
            pass
    
    # Try to get next available key
    next_key = await get_next_available_key(user_id, ObjectId(current_key_id) if current_key_id else None)
    
    if next_key:
        try:
            decrypted = decrypt_api_key(next_key["encrypted_key"])
            await activate_key(next_key["_id"], user_id)
            logger.info(f"🔄 Switched to next API key for user {user_id[:8]}...")
            return decrypted, None
        except Exception as e:
            logger.error(f"Failed to switch to next key: {e}")
            # Recursively try next
            return await handle_key_exhaustion(user_id, str(next_key["_id"]))
    
    return None, ErrorCodes.ALL_KEYS_EXHAUSTED


async def increment_free_usage(user_id: str, generation_id: str = None) -> dict:
    """
    Increment the free request counter for a user with ATOMIC operation.
    Called after a successful LLM request using platform key.
    
    Features:
    - Atomic increment to prevent race conditions
    - Daily reset check (if new day, reset counter first)
    - Prevents over-counting (won't increment past limit)
    - Returns the updated count for logging/debugging
    - Audit trail with generation_id
    
    Returns: {"success": bool, "new_count": int, "was_reset": bool, "message": str}
    """
    today = get_today_str()
    
    # Single DB call to get current state
    usage = await usage_collection.find_one({"user_id": user_id})
    was_reset = False
    
    # IDEMPOTENCY CHECK: If generation_id provided, check if already counted
    if generation_id and usage:
        counted_generations = usage.get("counted_generation_ids", [])
        if generation_id in counted_generations:
            current_count = usage.get("free_requests_used", 0)
            logger.info(f"🔄 Idempotent: Generation {generation_id[:8]}... already counted for user {user_id[:8]}...")
            return {
                "success": False, 
                "new_count": current_count, 
                "was_reset": False,
                "message": "Already counted (idempotent)",
                "idempotent": True
            }
    
    # Check if we need to reset (new day)
    if usage:
        last_reset = usage.get("last_reset_date", "")
        if last_reset != today:
            # New day - reset counter and clear idempotency list
            await usage_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "free_requests_used": 0,
                        "last_reset_date": today,
                        "last_reset_at": datetime.utcnow(),
                        "counted_generation_ids": []  # Clear for new day
                    }
                }
            )
            was_reset = True
            logger.info(f"♻️ Reset free usage counter for user {user_id[:8]}... (new day)")
    
    # Handle new user - create document first
    if not usage:
        try:
            await usage_collection.insert_one({
                "user_id": user_id,
                "free_requests_used": 1,
                "free_limit": FREE_REQUEST_LIMIT,
                "created_at": datetime.utcnow(),
                "last_reset_date": today,
                "last_used_at": datetime.utcnow(),
                "last_generation_id": generation_id,
                "counted_generation_ids": [generation_id] if generation_id else []
            })
            logger.info(f"📊 User {user_id[:8]}... free usage: 1/{FREE_REQUEST_LIMIT} (new record)")
            return {
                "success": True,
                "new_count": 1,
                "was_reset": False,
                "message": f"Incremented to 1/{FREE_REQUEST_LIMIT}"
            }
        except Exception as e:
            # Duplicate key race condition - another request created it first
            logger.warning(f"⚠️ Insert race condition for {user_id[:8]}..., retrying update: {e}")
            # Fall through to update path
    
    # Build update operation for existing document
    update_op = {
        "$inc": {"free_requests_used": 1},
        "$set": {
            "last_used_at": datetime.utcnow(),
            "last_generation_id": generation_id
        }
    }
    
    # Add generation_id to tracking list (for idempotency)
    if generation_id:
        update_op["$push"] = {"counted_generation_ids": {
            "$each": [generation_id],
            "$slice": -100  # Keep only last 100 to prevent unbounded growth
        }}
    
    # Atomic increment with safety check (don't go over limit)
    result = await usage_collection.find_one_and_update(
        {
            "user_id": user_id,
            "free_requests_used": {"$lt": FREE_REQUEST_LIMIT}  # Safety: don't increment past limit
        },
        update_op,
        return_document=True  # Return updated document
    )
    
    if result:
        new_count = result.get("free_requests_used", 0)
        logger.info(f"📊 User {user_id[:8]}... free usage: {new_count}/{FREE_REQUEST_LIMIT}")
        return {
            "success": True, 
            "new_count": new_count, 
            "was_reset": was_reset,
            "message": f"Incremented to {new_count}/{FREE_REQUEST_LIMIT}"
        }
    else:
        # Increment failed (likely already at limit)
        current = await usage_collection.find_one({"user_id": user_id})
        current_count = current.get("free_requests_used", 0) if current else 0
        logger.warning(f"⚠️ Free usage increment skipped for {user_id[:8]}... (at limit: {current_count})")
        return {
            "success": False, 
            "new_count": current_count, 
            "was_reset": was_reset,
            "message": f"Already at limit ({current_count}/{FREE_REQUEST_LIMIT})"
        }


async def increment_user_key_usage(user_id: str, key_id: str, generation_id: str = None) -> dict:
    """
    Increment usage counter for a user's own API key.
    Tracks per-key usage for analytics and key rotation decisions.
    
    Returns: {"success": bool, "requests_today": int}
    """
    today = get_today_str()
    
    try:
        key_oid = ObjectId(key_id) if isinstance(key_id, str) else key_id
        
        # Check if new day - reset counter
        key_doc = await api_keys_collection.find_one({"_id": key_oid})
        if key_doc and key_doc.get("last_request_date") != today:
            # New day - reset daily counter
            await api_keys_collection.update_one(
                {"_id": key_oid},
                {"$set": {"requests_today": 0, "last_request_date": today}}
            )
        
        # Atomic increment
        result = await api_keys_collection.find_one_and_update(
            {"_id": key_oid, "user_id": user_id},
            {
                "$inc": {"requests_today": 1, "total_requests": 1},
                "$set": {
                    "last_used": datetime.utcnow(),
                    "last_generation_id": generation_id
                }
            },
            return_document=True
        )
        
        if result:
            return {"success": True, "requests_today": result.get("requests_today", 0)}
        return {"success": False, "requests_today": 0}
        
    except Exception as e:
        logger.error(f"Failed to increment user key usage: {e}")
        return {"success": False, "requests_today": 0, "error": str(e)}


async def check_can_make_request(user_id: str) -> Tuple[bool, str | None]:
    """
    Check if user can make a request.
    
    Returns: (can_make, error_code)
    
    error_code can be:
    - None: can make request
    - "FREE_LIMIT_EXCEEDED": need to add API key
    - "ALL_KEYS_EXHAUSTED": all keys hit their limits
    """
    api_key, source, error_code = await get_api_key_for_user(user_id)
    
    if api_key:
        return True, None
    
    return False, error_code


async def get_current_key_id_for_user(user_id: str) -> str | None:
    """Get the ID of the currently active key for tracking exhaustion."""
    active_key = await api_keys_collection.find_one({
        "user_id": user_id,
        "is_active": True
    })
    return str(active_key["_id"]) if active_key else None
