
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging
import json
from datetime import datetime, timezone
from app.db.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    🔐 GLOBAL AUTH MIDDLEWARE
    
    Responsibilities:
    1. Resolve user ONCE per request
    2. Check Redis cache first (TTL 5-15 min)
    3. If valid, attach to request.state.user
    4. If invalid/missing, set request.state.user = None (Controllers decide 401)
    
    Critically fixes "401 after persistent login" issues.
    """
    
    async def dispatch(self, request: Request, call_next):
        
        # Skip auth for public endpoints to save resources
        if request.url.path.startswith(("/health", "/static", "/docs", "/openapi.json", "/auth/login", "/auth/signup")):
            return await call_next(request)
            
        # 1. Try to get Session ID from Cookie (Preferred)
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        
        # 2. Key for Redis Cache
        user_cache_key = None
        user_data = None
        
        if session_id:
            # Check Redis for "session_user:{session_id}"
            user_cache_key = f"session_user:{session_id}"
            cached_user = await redis_client.get(user_cache_key)
            
            if cached_user:
                try:
                    user_data = json.loads(cached_user)
                    # logger.debug(f"✅ Auth Cache Hit (Redis): {user_data.get('email')}")
                except:
                    # Invalid cache data
                    user_data = None
        
        # 3. If cache miss, but session_id exists, resolve from MongoDB
        if not user_data and session_id:
            # We need to perform the resolution logic here once
            # To avoid circular imports, strict usage of collections from db modules
            try:
                from app.db.mongo_client import auth_sessions_collection, users_collection
                from bson import ObjectId
                
                # Fetch Session
                session = await auth_sessions_collection.find_one({"sessionId": session_id})
                
                if session and session.get("is_active", False):
                    # Check expiration
                    expires_at = session.get("expires_at")
                    if expires_at and expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                        
                        # Valid Session -> Fetch User
                        user_id = session.get("userId")
                        if isinstance(user_id, str):
                            user_id = ObjectId(user_id)
                            
                        user = await users_collection.find_one({"_id": user_id})
                        if user:
                            # Construct Lightweight Object
                            user_data = {
                                "user_id": str(user["_id"]),
                                "email": user["email"],
                                "name": user.get("name", ""),
                                "role": user.get("role", "user")
                            }
                            
                            # Cache in Redis (10 minutes)
                            if user_cache_key:
                                await redis_client.setex(user_cache_key, 600, json.dumps(user_data))
                                logger.info(f"💾 Auth Resolved & Cached: {user_data['email']}")
            except Exception as e:
                logger.error(f"❌ Auth Resolution Error: {e}")
                
        # 4. Attach to request state
        request.state.user = user_data # Dict or None
        
        # Call next middleware/route
        response = await call_next(request)
        return response
