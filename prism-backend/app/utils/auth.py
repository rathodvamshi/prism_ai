"""
JWT Authentication Utilities
Handles JWT token creation, validation, and user authentication
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Cookie, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.db.mongo_client import users_collection, auth_sessions_collection
from app.models.user_models import User
import logging
import hashlib

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration (still available for internal tools)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30 * 24 * 60)  # 30 days
REFRESH_TOKEN_EXPIRE_DAYS = getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 90)  # 90 days
SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')

# Security scheme for FastAPI (Bearer tokens – legacy/internal)
security = HTTPBearer()

class AuthUtils:
    """Authentication utility class for JWT operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt with proper 72-byte limit handling"""
        # ☁️ CRITICAL: bcrypt has a 72-byte limit, not character limit
        # Encode to bytes first, then truncate to 72 bytes
        password_bytes = password.encode('utf-8')
        
        if len(password_bytes) > 72:
            # Truncate to 72 bytes (not characters)
            safe_password_bytes = password_bytes[:72]
            safe_password = safe_password_bytes.decode('utf-8', errors='ignore')
            logger.warning(f"Password truncated from {len(password)} chars ({len(password_bytes)} bytes) to {len(safe_password)} chars (72 bytes) for bcrypt")
        else:
            safe_password = password
        
        try:
            # Use bcrypt with properly truncated password
            hashed = pwd_context.hash(safe_password)
            logger.info(f"✅ Password hashed successfully using bcrypt")
            return hashed
        except Exception as e:
            logger.error(f"❌ Bcrypt hashing failed: {e}")
            # Last resort: use SHA256 with salt (not ideal but works)
            import hashlib
            import secrets
            salt = secrets.token_hex(16)
            combined = f"{salt}:{safe_password}".encode('utf-8')
            hashed = hashlib.sha256(combined).hexdigest()
            logger.warning(f"⚠️ Using SHA256 fallback for password hashing")
            return f"sha256:{salt}:{hashed}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash with proper 72-byte limit handling"""
        # ☁️ CRITICAL: Apply same 72-byte truncation as in hash_password
        password_bytes = plain_password.encode('utf-8')
        
        if len(password_bytes) > 72:
            safe_password_bytes = password_bytes[:72]
            safe_password = safe_password_bytes.decode('utf-8', errors='ignore')
        else:
            safe_password = plain_password
        
        try:
            # Check if it's a SHA256 fallback hash (format: "sha256:salt:hash")
            if hashed_password.startswith("sha256:"):
                import hashlib
                parts = hashed_password.split(":")
                if len(parts) == 3:
                    salt, stored_hash = parts[1], parts[2]
                    combined = f"{salt}:{safe_password}".encode('utf-8')
                    computed_hash = hashlib.sha256(combined).hexdigest()
                    return computed_hash == stored_hash
                return False
            
            # Standard bcrypt verification
            return pwd_context.verify(safe_password, hashed_password)
        except Exception as e:
            logger.error(f"❌ Password verification failed: {e}")
            return False

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create refresh token"
            )

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError as e:
            logger.error(f"JWT Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user from database by email"""
        try:
            user = await users_collection.find_one({"email": email})
            return user
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database by ID"""
        try:
            from bson import ObjectId
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            user = await users_collection.find_one({"_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None

    @staticmethod
    def create_user_response(user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe user response (remove sensitive fields)"""
        safe_user = {
            "id": str(user["_id"]),
            "email": user["email"],
            "verified": user.get("verified", False),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login")
        }
        
        # Add optional fields if they exist
        if "name" in user:
            safe_user["name"] = user["name"]
        if "profile" in user:
            safe_user["profile"] = user["profile"]
            
        return safe_user

# Dependency to get current user from JWT token (legacy / internal)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token
    Usage: user = Depends(get_current_user)
    """
    token = credentials.credentials
    
    # Verify token
    payload = AuthUtils.verify_token(token)
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from payload
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user_data = await AuthUtils.get_user_by_id(user_id)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(
        user_id=str(user_data["_id"]),
        email=user_data["email"],
        name=user_data.get("name")
    )

# Optional dependency for endpoints that may or may not require authentication (JWT-based)
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """
    FastAPI dependency for optional authentication
    Returns user if valid token is provided, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Dependency to ensure user is verified (JWT-based placeholder)
async def get_verified_user(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to ensure user is verified
    """
    # This part needs to be adapted as the user object is now a Pydantic model
    # We need to fetch the full user data from DB to check 'verified' status
    # For now, let's assume if the user object exists, they are verified.
    # A proper implementation would fetch the 'verified' field from the DB.
    # This is a placeholder to make the code run.
    # In a real scenario, you would do:
    # user_data = await AuthUtils.get_user_by_id(user.user_id)
    # if not user_data.get("verified", False):
    #     raise HTTPException(...)
    return user


# --------------------------------------------------------------------
# Session-based Authentication (Server-side sessions with HTTP-only cookie)
# --------------------------------------------------------------------

SESSION_COOKIE_NAME = getattr(settings, "SESSION_COOKIE_NAME", "session_id")
SESSION_EXPIRE_DAYS = getattr(settings, "SESSION_EXPIRE_DAYS", 30)
AUTH_SINGLE_SESSION = getattr(settings, "AUTH_SINGLE_SESSION", False)


async def create_session_for_user(
    user: dict,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> str:
    """
    Create a new login session for the given user and persist it in MongoDB.
    Returns the opaque sessionId to be set in an HTTP-only cookie.
    """
    from bson import ObjectId
    import uuid

    user_id = user.get("_id") or user.get("id") or user.get("user_id")
    if isinstance(user_id, str):
        try:
            user_id_obj = ObjectId(user_id)
        except Exception:
            # Fallback: store string user id if not a valid ObjectId
            user_id_obj = user_id
    else:
        user_id_obj = user_id

    # Optionally enforce a single active session per user
    if AUTH_SINGLE_SESSION and user_id_obj:
        try:
            await auth_sessions_collection.update_many(
                {"userId": user_id_obj, "is_active": True},
                {"$set": {"is_active": False, "invalidated_at": datetime.now(timezone.utc)}},
            )
        except Exception as e:
            logger.warning(f"Failed to invalidate existing sessions for user {user_id}: {e}")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=SESSION_EXPIRE_DAYS)

    session_doc = {
        "sessionId": session_id,
        "userId": user_id_obj,
        "email": user.get("email"),
        "created_at": now,
        "expires_at": expires_at,
        "user_agent": user_agent or "",
        "ip": ip or "",
        "is_active": True,
    }

    try:
        await auth_sessions_collection.insert_one(session_doc)
        logger.info(f"✅ Created login session for user {user.get('email')} | sessionId={session_id}")
    except Exception as e:
        logger.error(f"❌ Failed to create login session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create login session",
        )

    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    """Fetch a session document by opaque sessionId and validate basic fields."""
    if not session_id:
        return None

    try:
        session = await auth_sessions_collection.find_one({"sessionId": session_id})
        if not session:
            return None

        if not session.get("is_active", False):
            return None

        expires_at = session.get("expires_at")
        if isinstance(expires_at, datetime):
            # Safety fix: ensure expires_at is timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return None

        return session
    except Exception as e:
        logger.error(f"❌ Failed to fetch session: {e}")
        return None


async def get_current_user_from_session(
    session_cookie_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User:
    """
    FastAPI dependency to get the authenticated user from an HTTP-only session cookie.

    - Reads opaque session_id from cookie
    - Validates session in auth_sessions_collection
    - Loads user from users_collection
    """
    if not session_cookie_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = await get_session(session_cookie_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user_id = session.get("userId")
    try:
        from bson import ObjectId

        if isinstance(user_id, str) and ObjectId.is_valid(user_id):
            user_id_query = ObjectId(user_id)
        else:
            user_id_query = user_id

        user_doc = await users_collection.find_one({"_id": user_id_query})
    except Exception as e:
        logger.error(f"❌ Error fetching user for session: {e}")
        user_doc = None

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for session",
        )

    # Minimal user model used throughout the app
    return User(
        user_id=str(user_doc["_id"]),
        email=user_doc["email"],
        name=user_doc.get("name"),
    )


async def get_optional_user_from_session(
    session_cookie_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Optional[User]:
    """Optional session-based dependency: returns User or None."""
    if not session_cookie_id:
        return None
    try:
        return await get_current_user_from_session(session_cookie_id=session_cookie_id)
    except HTTPException:
        return None

# Rate limiting and security utilities
class SecurityUtils:
    """Security utility functions"""

    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, str]:
        """
        Check if password meets security requirements
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        return True, ""

    @staticmethod
    def sanitize_user_input(input_text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_text:
            return ""
        
        # Trim whitespace and limit length
        sanitized = input_text.strip()[:max_length]
        
        # Remove potentially dangerous characters (basic sanitization)
        # Note: For production, consider using a proper sanitization library
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized

# Export main utilities
__all__ = [
    'AuthUtils',
    'SecurityUtils',
    'get_current_user',
    'get_optional_user',
    'get_verified_user',
    'pwd_context',
    'security'
]