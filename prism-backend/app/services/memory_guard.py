"""
🛡️ MEMORY GUARD - User Isolation & Security Layer
==================================================

This module provides strict user isolation and security for all memory operations.
It acts as a protective wrapper around memory services.

Key Features:
- Strict user_id validation before any memory operation
- Zero cross-user contamination guarantees
- Defensive checks for every memory query
- Privacy-first design with consent tracking
- Audit logging for security compliance

Usage:
    from app.services.memory_guard import MemoryGuard, memory_guard
    
    # Validate before any operation
    if memory_guard.validate_access(user_id, operation="read"):
        memories = await fetch_memories(user_id)
"""

import logging
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryOperation(Enum):
    """Memory operation types for access control"""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"


class MemoryAccessDenied(Exception):
    """Raised when memory access is denied due to security violation"""
    pass


class UserIdValidationError(Exception):
    """Raised when user_id fails validation"""
    pass


class MemoryGuard:
    """
    🛡️ MEMORY GUARD - Enforces Strict User Isolation
    
    Rules:
    1. Every operation MUST have a valid user_id
    2. User IDs must be validated before use
    3. Cross-user access is ALWAYS denied
    4. All operations are logged for audit
    5. Sensitive data requires explicit consent
    """
    
    def __init__(self):
        # Track active user sessions (user_id -> session_info)
        self._active_sessions: Dict[str, Dict] = {}
        
        # Track blocked operations (for rate limiting / abuse prevention)
        self._blocked_users: Set[str] = set()
        
        # Consent registry (user_id -> consented_data_types)
        self._consent_registry: Dict[str, Set[str]] = {}
        
        # Sensitive data types that require explicit consent
        self.SENSITIVE_DATA_TYPES = {
            "health", "financial", "political", "religious", 
            "biometric", "genetic", "sexual_orientation", "ethnicity"
        }
        
        # Valid user_id patterns (more flexible for real-world usage)
        self.VALID_USER_ID_PATTERNS = [
            r'^[0-9a-fA-F]{24}$',  # MongoDB ObjectId
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',  # UUID
            r'^u_[a-zA-Z0-9_-]{5,50}$',  # Custom prefixed format
            r'^user_[a-zA-Z0-9_-]{5,50}$',  # user_ prefixed format
            r'^[a-zA-Z][a-zA-Z0-9_-]{4,49}$',  # Simple alphanumeric (min 5 chars)
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',  # Email format
        ]
        
        # Minimum user ID length for security
        self.MIN_USER_ID_LENGTH = 5
        
        logger.info("🛡️ MemoryGuard initialized - User isolation enforced")
    
    def validate_user_id(self, user_id: Any) -> Tuple[bool, str]:
        """
        Validate user_id format and integrity
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if user_id is None:
            return False, "user_id cannot be None"
        
        if not isinstance(user_id, str):
            return False, f"user_id must be string, got {type(user_id).__name__}"
        
        user_id = user_id.strip()
        
        if not user_id:
            return False, "user_id cannot be empty"
        
        if len(user_id) > 100:
            return False, "user_id exceeds maximum length (100 chars)"
        
        if len(user_id) < self.MIN_USER_ID_LENGTH:
            return False, f"user_id must be at least {self.MIN_USER_ID_LENGTH} characters"
        
        # Check for injection attempts
        if self._contains_injection(user_id):
            logger.warning(f"🚨 SECURITY: Potential injection attempt in user_id: {user_id[:20]}...")
            return False, "user_id contains invalid characters"
        
        # Validate against known patterns
        is_valid_pattern = any(
            re.match(pattern, user_id) 
            for pattern in self.VALID_USER_ID_PATTERNS
        )
        
        if not is_valid_pattern:
            return False, f"user_id '{user_id[:20]}...' does not match valid patterns"
        
        return True, "valid"
    
    def _contains_injection(self, value: str) -> bool:
        """Check for potential injection patterns"""
        injection_patterns = [
            r'[\$\{\}]',  # Template injection
            r'<script',  # XSS
            r'javascript:',  # XSS
            r'[\x00-\x1f]',  # Control characters
            r'\.\./',  # Path traversal
            r'__proto__',  # Prototype pollution
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    def validate_access(
        self,
        user_id: str,
        operation: MemoryOperation,
        target_user_id: Optional[str] = None,
        data_type: Optional[str] = None
    ) -> bool:
        """
        🛡️ CRITICAL: Validate memory access before ANY operation
        
        Args:
            user_id: The user requesting access
            operation: The type of operation
            target_user_id: The user whose data is being accessed (for cross-check)
            data_type: Type of data being accessed (for consent check)
            
        Returns:
            True if access is allowed, raises exception otherwise
        """
        # 1. Validate user_id format
        is_valid, error = self.validate_user_id(user_id)
        if not is_valid:
            logger.error(f"🚨 SECURITY: Invalid user_id - {error}")
            raise UserIdValidationError(error)
        
        # 2. Check if user is blocked
        if user_id in self._blocked_users:
            logger.warning(f"🚨 SECURITY: Blocked user attempted access: {user_id[:8]}...")
            raise MemoryAccessDenied("User access is blocked")
        
        # 3. CRITICAL: Cross-user access check
        if target_user_id is not None:
            target_valid, _ = self.validate_user_id(target_user_id)
            if target_valid and self._normalize_user_id(user_id) != self._normalize_user_id(target_user_id):
                logger.error(
                    f"🚨 SECURITY: Cross-user access DENIED! "
                    f"User {user_id[:8]}... tried to access {target_user_id[:8]}..."
                )
                raise MemoryAccessDenied("Cross-user access is strictly forbidden")
        
        # 4. Consent check for sensitive data
        if data_type and data_type.lower() in self.SENSITIVE_DATA_TYPES:
            if not self._has_consent(user_id, data_type):
                logger.warning(
                    f"⚠️ PRIVACY: Sensitive data access without consent - "
                    f"user={user_id[:8]}..., type={data_type}"
                )
                raise MemoryAccessDenied(f"Consent required for {data_type} data")
        
        # 5. Log successful access (without exposing user_id)
        user_hash = self._hash_user_id(user_id)
        logger.debug(f"✅ Access granted: user_hash={user_hash}, op={operation.value}")
        
        return True
    
    def _normalize_user_id(self, user_id: str) -> str:
        """Normalize user_id for comparison"""
        normalized = user_id.strip().lower()
        return normalized
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user_id for logging (privacy protection)"""
        return hashlib.sha256(user_id.encode()).hexdigest()[:12]
    
    def _has_consent(self, user_id: str, data_type: str) -> bool:
        """Check if user has given consent for specific data type"""
        user_consents = self._consent_registry.get(user_id, set())
        return data_type.lower() in user_consents
    
    def grant_consent(self, user_id: str, data_types: List[str]) -> bool:
        """Record user consent for specific data types"""
        is_valid, _ = self.validate_user_id(user_id)
        if not is_valid:
            return False
        
        if user_id not in self._consent_registry:
            self._consent_registry[user_id] = set()
        
        for data_type in data_types:
            self._consent_registry[user_id].add(data_type.lower())
        
        logger.info(f"✅ Consent granted: user_hash={self._hash_user_id(user_id)}, types={data_types}")
        return True
    
    def revoke_consent(self, user_id: str, data_types: Optional[List[str]] = None) -> bool:
        """Revoke user consent for specific or all data types"""
        is_valid, _ = self.validate_user_id(user_id)
        if not is_valid:
            return False
        
        if user_id in self._consent_registry:
            if data_types:
                for data_type in data_types:
                    self._consent_registry[user_id].discard(data_type.lower())
            else:
                self._consent_registry[user_id].clear()
        
        logger.info(f"✅ Consent revoked: user_hash={self._hash_user_id(user_id)}")
        return True
    
    def scope_query(self, user_id: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        🛡️ CRITICAL: Add user scoping to any database query
        
        Ensures queries ALWAYS include user_id filter.
        This is the LAST LINE OF DEFENSE against cross-user data access.
        
        Args:
            user_id: The user making the query
            query: The original query dict
            
        Returns:
            Query with user_id scope enforced
        """
        # Validate user_id first
        is_valid, error = self.validate_user_id(user_id)
        if not is_valid:
            raise UserIdValidationError(error)
        
        # Create new query with user scope (don't modify original)
        scoped_query = query.copy()
        
        # Add user_id filter (support multiple field names)
        user_id_fields = ["user_id", "userId", "owner_id", "created_by"]
        
        # Check if any user field already exists
        existing_user_field = None
        for field in user_id_fields:
            if field in scoped_query:
                existing_user_field = field
                break
        
        if existing_user_field:
            # Verify it matches the requesting user
            existing_value = scoped_query[existing_user_field]
            if isinstance(existing_value, str):
                if self._normalize_user_id(existing_value) != self._normalize_user_id(user_id):
                    raise MemoryAccessDenied("Query user_id doesn't match requesting user")
        else:
            # Add user_id to query
            scoped_query["user_id"] = user_id
        
        return scoped_query
    
    def scope_document(self, user_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        🛡️ CRITICAL: Add user ownership to any document before storage
        
        Args:
            user_id: The user creating the document
            document: The document to store
            
        Returns:
            Document with user ownership fields
        """
        is_valid, error = self.validate_user_id(user_id)
        if not is_valid:
            raise UserIdValidationError(error)
        
        # Create new document with ownership (don't modify original)
        scoped_doc = document.copy()
        
        # Add ownership fields
        scoped_doc["user_id"] = user_id
        scoped_doc["_owner"] = user_id
        scoped_doc["_created_at"] = datetime.utcnow().isoformat()
        scoped_doc["_updated_at"] = datetime.utcnow().isoformat()
        
        return scoped_doc
    
    def verify_ownership(self, user_id: str, document: Dict[str, Any]) -> bool:
        """
        Verify that a document belongs to the specified user
        
        Args:
            user_id: The user claiming ownership
            document: The document to verify
            
        Returns:
            True if user owns the document
        """
        is_valid, _ = self.validate_user_id(user_id)
        if not is_valid:
            return False
        
        # Check ownership fields
        owner_fields = ["user_id", "userId", "_owner", "owner_id", "created_by"]
        
        for field in owner_fields:
            if field in document:
                doc_owner = document[field]
                if isinstance(doc_owner, str):
                    if self._normalize_user_id(doc_owner) == self._normalize_user_id(user_id):
                        return True
                    else:
                        logger.warning(
                            f"🚨 SECURITY: Ownership mismatch - "
                            f"claimed={user_id[:8]}..., actual={doc_owner[:8]}..."
                        )
                        return False
        
        # No ownership field found - deny by default
        logger.warning("⚠️ Document has no ownership field - denying access")
        return False
    
    def sanitize_memory_content(self, content: Any) -> Any:
        """
        Sanitize memory content before storage
        
        Removes potential injection vectors and normalizes data.
        """
        if content is None:
            return None
        
        if isinstance(content, str):
            # Remove control characters
            sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
            # Limit length
            sanitized = sanitized[:10000]  # Max 10KB per memory item
            return sanitized.strip()
        
        if isinstance(content, dict):
            # Dangerous keys to remove (MongoDB operators, injection vectors)
            dangerous_keys = {
                '$where', '$gt', '$lt', '$ne', '$or', '$and', '$set', '$unset',
                '$push', '$pull', '$inc', '$regex', '$expr', '$function',
                'db', '__proto__', 'constructor', 'prototype'
            }
            
            return {
                self.sanitize_memory_content(k): self.sanitize_memory_content(v)
                for k, v in content.items()
                if k is not None and k not in dangerous_keys and not str(k).startswith('$')
            }
        
        if isinstance(content, list):
            return [self.sanitize_memory_content(item) for item in content[:100]]  # Max 100 items
        
        if isinstance(content, (int, float, bool)):
            return content
        
        # Unknown type - convert to string
        return str(content)[:1000]
    
    def create_audit_log(
        self,
        user_id: str,
        operation: MemoryOperation,
        success: bool,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create an audit log entry for memory operations
        
        Note: User IDs are hashed for privacy in logs
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_hash": self._hash_user_id(user_id),
            "operation": operation.value,
            "success": success,
            "details": {
                k: v for k, v in (details or {}).items()
                if k not in ["user_id", "password", "token", "secret"]
            }
        }


def require_user_isolation(operation: MemoryOperation = MemoryOperation.READ):
    """
    🛡️ Decorator to enforce user isolation on any memory function
    
    Usage:
        @require_user_isolation(MemoryOperation.WRITE)
        async def save_memory(user_id: str, content: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from args or kwargs
            user_id = kwargs.get("user_id") or (args[0] if args else None)
            
            if user_id is None:
                raise UserIdValidationError("user_id is required for memory operations")
            
            # Validate access
            memory_guard.validate_access(user_id, operation)
            
            # Execute original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global singleton instance
memory_guard = MemoryGuard()
