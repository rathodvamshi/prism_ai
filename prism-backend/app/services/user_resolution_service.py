"""
🔐 USER IDENTITY RESOLUTION SERVICE
====================================

🎯 MISSION: Enforce ONE EMAIL = ONE USER across entire system

This service is the ONLY authorized way to:
- Normalize email addresses
- Generate canonical user_ids
- Resolve email → user_id mappings
- Prevent duplicate user creation

🚨 CRITICAL RULES:
1. Email is the PRIMARY identity key
2. ONE email maps to exactly ONE user_id
3. user_id is immutable and used everywhere
4. All user creation MUST go through this service
5. Email normalization is MANDATORY before any operation

📊 GUARANTEES:
- Database-level uniqueness (MongoDB unique index)
- Cross-session continuity
- No memory fragmentation
- No duplicate graph nodes
- No duplicate vectors
"""

import re
import hashlib
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class UserIdentityResolutionError(Exception):
    """Raised when user identity resolution fails"""
    pass


class UserResolutionService:
    """
    🔐 Canonical User Resolution Service
    
    This is the SINGLE SOURCE OF TRUTH for user identity management.
    
    Key Responsibilities:
    1. Email normalization (lowercase, trim, sanitize)
    2. Canonical user_id generation (deterministic hash)
    3. User lookup and creation (with uniqueness enforcement)
    4. Debug logging for all identity operations
    
    Usage:
        service = UserResolutionService(mongo_client)
        user_id, is_new = await service.resolve_user("User@Gmail.com")
        # user_id is now the canonical ID to use everywhere
    """
    
    def __init__(self, mongo_client: AsyncIOMotorClient):
        """
        Initialize User Resolution Service
        
        Args:
            mongo_client: MongoDB async client for user storage
        """
        self.mongo = mongo_client
        from app.config import settings
        from urllib.parse import urlsplit
        try:
            uri_path = urlsplit(settings.MONGO_URI).path.strip("/")
            db_name = uri_path if uri_path else "prismdb"
        except Exception:
            db_name = "prismdb"
            
        self.db = self.mongo[db_name]
        self.users_collection = self.db["users"]
        
        logger.info("🔐 [User Resolution Service] Initialized")
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """
        🧹 Normalize email to canonical form
        
        Normalization steps:
        1. Strip whitespace (leading/trailing)
        2. Convert to lowercase
        3. Remove invisible characters
        4. Remove extra spaces
        5. Validate basic format
        
        Args:
            email: Raw email address
            
        Returns:
            Normalized email (lowercase, trimmed)
            
        Raises:
            ValueError: If email is invalid
        """
        if not email or not isinstance(email, str):
            raise ValueError("Email must be a non-empty string")
        
        # Step 1: Strip whitespace
        normalized = email.strip()
        
        # Step 2: Convert to lowercase
        normalized = normalized.lower()
        
        # Step 3: Remove invisible characters (zero-width, non-breaking spaces, etc.)
        normalized = re.sub(r'[\u200B-\u200D\uFEFF\u00A0]', '', normalized)
        
        # Step 4: Remove extra internal spaces
        normalized = re.sub(r'\s+', '', normalized)
        
        # Step 5: Basic validation (must contain @ and .)
        if '@' not in normalized or '.' not in normalized:
            raise ValueError(f"Invalid email format: {email}")
        
        logger.debug(f"🧹 [Email Normalization] {email} → {normalized}")
        
        return normalized
    
    @staticmethod
    def generate_user_id(normalized_email: str) -> str:
        """
        🔑 Generate canonical user_id from normalized email
        
        Uses SHA256 hash to create deterministic, unique user_id.
        Same email always produces same user_id.
        
        Format: u_{first_12_chars_of_hash}
        Example: u_8392ab4def56
        
        Args:
            normalized_email: Email in canonical form
            
        Returns:
            Canonical user_id (immutable identifier)
        """
        # Create SHA256 hash of normalized email
        email_bytes = normalized_email.encode('utf-8')
        hash_object = hashlib.sha256(email_bytes)
        hash_hex = hash_object.hexdigest()
        
        # Use first 12 characters for readability
        user_id = f"u_{hash_hex[:12]}"
        
        logger.debug(f"🔑 [User ID Generation] {normalized_email} → {user_id}")
        
        return user_id
    
    async def ensure_unique_index(self) -> bool:
        """
        🔒 Ensure MongoDB unique index exists on email field
        
        This is DATABASE-LEVEL enforcement (not just app-level).
        Prevents duplicate users at the storage layer.
        
        Returns:
            True if index created/verified, False if error
        """
        try:
            # Create unique index on email field
            await self.users_collection.create_index("email", unique=True, name="email_unique_idx")
            logger.info("🔒 [MongoDB] Unique index on 'email' field ENFORCED")
            return True
        except Exception as e:
            logger.error(f"❌ [MongoDB] Failed to create unique index: {e}")
            return False
    
    async def resolve_user(
        self,
        email: str,
        additional_data: Optional[Dict] = None
    ) -> Tuple[str, bool, Dict]:
        """
        🎯 RESOLVE EMAIL → CANONICAL USER_ID (Primary Method)
        
        This is the ONLY authorized way to obtain a user_id.
        
        Process:
        1. Normalize email
        2. Generate canonical user_id
        3. Check if user exists in MongoDB
        4. If not exists, create new user record
        5. Return user_id (same for existing/new)
        
        Args:
            email: User's email address (will be normalized)
            additional_data: Optional user profile data (name, etc.)
            
        Returns:
            Tuple of:
            - user_id (str): Canonical user identifier
            - is_new (bool): True if new user was created
            - user_data (dict): Full user profile from database
            
        Raises:
            UserIdentityResolutionError: If resolution fails
        """
        try:
            # Step 1: Normalize email
            normalized_email = self.normalize_email(email)
            
            # Step 2: Generate canonical user_id
            canonical_user_id = self.generate_user_id(normalized_email)
            
            logger.info("=" * 80)
            logger.info("🔐 [USER RESOLUTION] Starting identity resolution")
            logger.info(f"  📧 Raw Email: {email}")
            logger.info(f"  📧 Normalized Email: {normalized_email}")
            logger.info(f"  🔑 Canonical User ID: {canonical_user_id}")
            
            # Step 3: Check if user exists (by email - primary key)
            existing_user = await self.users_collection.find_one({"email": normalized_email})
            
            if existing_user:
                # User found - return existing data
                logger.info(f"  ✅ Existing User: YES")
                logger.info(f"  📅 Created: {existing_user.get('created_at', 'Unknown')}")
                logger.info(f"  👤 Name: {existing_user.get('name', 'Not set')}")
                logger.info("=" * 80)
                
                return canonical_user_id, False, existing_user
            
            else:
                # Step 4: Create new user record
                logger.info(f"  ✅ Existing User: NO")
                logger.info(f"  🆕 Creating new user record...")
                
                # Build user document
                user_document = {
                    "user_id": canonical_user_id,
                    "email": normalized_email,
                    "created_at": datetime.utcnow(),
                    "last_login": datetime.utcnow(),
                    "profile": additional_data or {},
                    "metadata": {
                        "original_email": email,  # Preserve original for audit
                        "source": "user_resolution_service"
                    }
                }
                
                # Insert with duplicate protection
                try:
                    result = await self.users_collection.insert_one(user_document)
                    logger.info(f"  ✅ User created successfully")
                    logger.info(f"  📝 MongoDB _id: {result.inserted_id}")
                    logger.info("=" * 80)
                    
                    return canonical_user_id, True, user_document
                    
                except Exception as insert_error:
                    # Check if it's a duplicate key error (race condition)
                    if "duplicate key" in str(insert_error).lower():
                        logger.warning(f"  ⚠️ Race condition detected - user was created by another process")
                        logger.info(f"  🔄 Re-fetching user data...")
                        
                        # Re-fetch the user
                        existing_user = await self.users_collection.find_one({"email": normalized_email})
                        if existing_user:
                            logger.info(f"  ✅ User found after race condition")
                            logger.info("=" * 80)
                            return canonical_user_id, False, existing_user
                    
                    # If not duplicate, it's a real error
                    raise insert_error
        
        except ValueError as ve:
            # Email validation error
            logger.error(f"❌ [USER RESOLUTION] Invalid email: {ve}")
            raise UserIdentityResolutionError(f"Invalid email: {ve}")
        
        except Exception as e:
            # Unexpected error
            logger.error(f"❌ [USER RESOLUTION] Failed: {e}")
            raise UserIdentityResolutionError(f"User resolution failed: {e}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        🔍 Lookup user by canonical user_id
        
        Args:
            user_id: Canonical user identifier
            
        Returns:
            User document if found, None otherwise
        """
        try:
            user = await self.users_collection.find_one({"user_id": user_id})
            
            if user:
                logger.debug(f"🔍 [User Lookup] Found user: {user_id}")
            else:
                logger.debug(f"🔍 [User Lookup] User not found: {user_id}")
            
            return user
        
        except Exception as e:
            logger.error(f"❌ [User Lookup] Error: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        🔍 Lookup user by email (normalizes first)
        
        Args:
            email: User's email address
            
        Returns:
            User document if found, None otherwise
        """
        try:
            normalized_email = self.normalize_email(email)
            user = await self.users_collection.find_one({"email": normalized_email})
            
            if user:
                logger.debug(f"🔍 [User Lookup] Found user by email: {normalized_email}")
            else:
                logger.debug(f"🔍 [User Lookup] User not found by email: {normalized_email}")
            
            return user
        
        except Exception as e:
            logger.error(f"❌ [User Lookup] Error: {e}")
            return None
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        🕒 Update user's last login timestamp
        
        Args:
            user_id: Canonical user identifier
            
        Returns:
            True if updated, False otherwise
        """
        try:
            result = await self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"🕒 [Last Login] Updated for user: {user_id}")
                return True
            else:
                logger.debug(f"🕒 [Last Login] No update needed for user: {user_id}")
                return False
        
        except Exception as e:
            logger.error(f"❌ [Last Login] Update failed: {e}")
            return False
    
    async def get_all_users_count(self) -> int:
        """
        📊 Get total number of unique users
        
        Returns:
            Count of users in database
        """
        try:
            count = await self.users_collection.count_documents({})
            logger.debug(f"📊 [User Count] Total users: {count}")
            return count
        except Exception as e:
            logger.error(f"❌ [User Count] Error: {e}")
            return 0
    
    async def validate_no_duplicates(self) -> Tuple[bool, list]:
        """
        🔍 AUDIT: Check for duplicate emails in database
        
        This should NEVER find duplicates if unique index is enforced.
        Use this for system health checks.
        
        Returns:
            Tuple of:
            - is_valid (bool): True if no duplicates found
            - duplicates (list): List of duplicate email addresses
        """
        try:
            # Aggregate to find duplicate emails
            pipeline = [
                {
                    "$group": {
                        "_id": "$email",
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}
                    }
                }
            ]
            
            duplicates_cursor = self.users_collection.aggregate(pipeline)
            duplicates = await duplicates_cursor.to_list(length=None)
            
            if duplicates:
                duplicate_emails = [dup["_id"] for dup in duplicates]
                logger.error(f"🚨 [AUDIT] DUPLICATES FOUND: {len(duplicate_emails)} emails")
                for email in duplicate_emails:
                    logger.error(f"  ❌ Duplicate: {email}")
                return False, duplicate_emails
            else:
                logger.info(f"✅ [AUDIT] No duplicate emails found")
                return True, []
        
        except Exception as e:
            logger.error(f"❌ [AUDIT] Validation failed: {e}")
            return False, []


# Global singleton instance (initialized by app)
_user_resolution_service: Optional[UserResolutionService] = None


def initialize_user_resolution_service(mongo_client: AsyncIOMotorClient) -> UserResolutionService:
    """
    Initialize global user resolution service
    
    Args:
        mongo_client: MongoDB async client
        
    Returns:
        UserResolutionService instance
    """
    global _user_resolution_service
    _user_resolution_service = UserResolutionService(mongo_client)
    logger.info("🔐 [User Resolution Service] Global instance initialized")
    return _user_resolution_service


def get_user_resolution_service() -> UserResolutionService:
    """
    Get global user resolution service instance
    
    Returns:
        UserResolutionService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _user_resolution_service is None:
        raise RuntimeError("User Resolution Service not initialized. Call initialize_user_resolution_service() first.")
    return _user_resolution_service


# Convenience function for quick resolution
async def resolve_user_identity(email: str) -> Tuple[str, bool]:
    """
    🎯 Quick convenience function for user resolution
    
    Args:
        email: User's email address
        
    Returns:
        Tuple of (user_id, is_new)
    """
    service = get_user_resolution_service()
    user_id, is_new, _ = await service.resolve_user(email)
    return user_id, is_new
