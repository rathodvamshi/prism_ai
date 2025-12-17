"""
🚀 Part 20: Idempotency Keys for Duplicate Prevention

Prevents duplicate operations from:
- Retry storms
- Double-clicks
- Network issues causing retries

Uses Redis for fast idempotency key storage (5 min TTL).
"""

import hashlib
import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

from app.db.redis_client import redis_client

logger = logging.getLogger(__name__)


class IdempotencyManager:
    """
    🚀 Part 20: Manages idempotency keys to prevent duplicate operations.
    
    Keys stored in Redis with 5-minute TTL (enough for retries, not forever).
    """
    
    IDEMPOTENCY_PREFIX = "idempotency"
    DEFAULT_TTL = 300  # 5 minutes
    
    @staticmethod
    def generate_key(user_id: str, operation: str, data: dict) -> str:
        """
        Generate idempotency key from operation and data.
        
        Args:
            user_id: User identifier
            operation: Operation type (e.g., "create_task", "send_email")
            data: Operation data (task description, due date, etc.)
        
        Returns:
            Idempotency key (hash of user + operation + data)
        
        Example:
            key = IdempotencyManager.generate_key(
                user_id="123",
                operation="create_task",
                data={"description": "Buy milk", "due_date": "2025-12-20"}
            )
            # Returns: "idempotency:123:create_task:a1b2c3d4..."
        """
        # Create deterministic hash from data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        # Format: idempotency:userId:operation:hash
        return f"{IdempotencyManager.IDEMPOTENCY_PREFIX}:{user_id}:{operation}:{data_hash}"
    
    @staticmethod
    async def check_and_set(
        user_id: str,
        operation: str,
        data: dict,
        result: Optional[Any] = None,
        ttl: int = DEFAULT_TTL
    ) -> tuple[bool, Optional[Any]]:
        """
        Check if operation already executed, if not mark as executed.
        
        Args:
            user_id: User identifier
            operation: Operation type
            data: Operation data
            result: Operation result to cache (optional)
            ttl: Time to live in seconds
        
        Returns:
            (is_duplicate, cached_result)
            - is_duplicate: True if operation already executed
            - cached_result: Previous result if duplicate, None otherwise
        
        Example:
            is_duplicate, cached_result = await IdempotencyManager.check_and_set(
                user_id="123",
                operation="create_task",
                data={"description": "Buy milk"},
                result={"task_id": "456"}
            )
            
            if is_duplicate:
                return cached_result  # Return previous result
            else:
                # Execute operation
                ...
        """
        key = IdempotencyManager.generate_key(user_id, operation, data)
        
        try:
            # Check if key exists
            existing = await redis_client.get(key)
            
            if existing:
                logger.info(f"🔄 Duplicate operation detected: {operation} for user {user_id}")
                # Parse cached result
                try:
                    cached_result = json.loads(existing)
                    return True, cached_result
                except:
                    return True, None
            
            # Key doesn't exist - set it with result
            value = json.dumps(result) if result else "executed"
            await redis_client.setex(key, ttl, value)
            
            logger.debug(f"✅ Idempotency key set: {operation} for user {user_id}")
            return False, None
            
        except Exception as e:
            logger.warning(f"⚠️ Idempotency check failed (continuing anyway): {e}")
            # If Redis fails, allow operation (better than blocking)
            return False, None
    
    @staticmethod
    async def invalidate(user_id: str, operation: str, data: dict):
        """
        Invalidate idempotency key (allow operation again).
        
        Use when user intentionally wants to retry (e.g., after cancel).
        """
        key = IdempotencyManager.generate_key(user_id, operation, data)
        
        try:
            await redis_client.delete(key)
            logger.debug(f"🗑️ Idempotency key invalidated: {operation}")
        except Exception as e:
            logger.warning(f"⚠️ Idempotency invalidation failed: {e}")


# ========== CONVENIENCE FUNCTIONS ==========

async def is_duplicate_task(
    user_id: str,
    description: str,
    due_date: str
) -> tuple[bool, Optional[dict]]:
    """
    Check if task creation is duplicate.
    
    Returns:
        (is_duplicate, cached_task)
    """
    return await IdempotencyManager.check_and_set(
        user_id=user_id,
        operation="create_task",
        data={
            "description": description.strip().lower(),
            "due_date": due_date
        }
    )


async def mark_task_created(
    user_id: str,
    description: str,
    due_date: str,
    task_id: str
):
    """
    Mark task as created with idempotency key.
    
    Stores task_id so duplicate attempts return same task.
    """
    await IdempotencyManager.check_and_set(
        user_id=user_id,
        operation="create_task",
        data={
            "description": description.strip().lower(),
            "due_date": due_date
        },
        result={"task_id": task_id}
    )


async def is_duplicate_email(
    user_id: str,
    email_type: str,
    recipient: str
) -> tuple[bool, Optional[dict]]:
    """
    Check if email send is duplicate.
    
    Prevents sending same email twice (e.g., task reminder).
    """
    return await IdempotencyManager.check_and_set(
        user_id=user_id,
        operation=f"send_email_{email_type}",
        data={"recipient": recipient}
    )


# ========== USAGE EXAMPLES ==========

"""
Example 1: Prevent duplicate task creation

    @router.post("/tasks/confirm")
    async def confirm_task(payload: dict, user: dict = Depends(get_current_user)):
        user_id = user.get("id")
        description = payload.get("description")
        due_date = payload.get("due_date")
        
        # Check if duplicate
        is_duplicate, cached_result = await is_duplicate_task(
            user_id=user_id,
            description=description,
            due_date=due_date
        )
        
        if is_duplicate:
            logger.info(f"Duplicate task creation prevented for user {user_id}")
            return cached_result  # Return existing task
        
        # Not duplicate - create task
        task = await create_task(payload)
        
        # Mark as created
        await mark_task_created(
            user_id=user_id,
            description=description,
            due_date=due_date,
            task_id=task.id
        )
        
        return task


Example 2: Prevent duplicate email sends

    async def send_task_reminder(task: dict):
        user_id = task.get("userId")
        recipient = task.get("user_email")
        
        # Check if already sent
        is_duplicate, _ = await is_duplicate_email(
            user_id=str(user_id),
            email_type="task_reminder",
            recipient=recipient
        )
        
        if is_duplicate:
            logger.info(f"Duplicate email send prevented: {recipient}")
            return
        
        # Not duplicate - send email
        await send_email(recipient, task)


Example 3: Custom idempotency check

    async def process_payment(user_id: str, amount: float, payment_method: str):
        # Check if payment already processed
        is_duplicate, cached_result = await IdempotencyManager.check_and_set(
            user_id=user_id,
            operation="process_payment",
            data={
                "amount": amount,
                "payment_method": payment_method
            }
        )
        
        if is_duplicate:
            logger.warning(f"Duplicate payment prevented for user {user_id}")
            return cached_result
        
        # Process payment
        result = await stripe.charge(amount, payment_method)
        
        # Cache result for future duplicate checks
        await IdempotencyManager.check_and_set(
            user_id=user_id,
            operation="process_payment",
            data={
                "amount": amount,
                "payment_method": payment_method
            },
            result=result
        )
        
        return result


Example 4: Invalidate idempotency key (allow retry)

    @router.post("/tasks/{task_id}/retry")
    async def retry_task(task_id: str, user: dict = Depends(get_current_user)):
        user_id = user.get("id")
        task = await get_task(task_id)
        
        # Invalidate idempotency key to allow retry
        await IdempotencyManager.invalidate(
            user_id=user_id,
            operation="create_task",
            data={
                "description": task.description,
                "due_date": task.due_date
            }
        )
        
        # Now user can create task again
        ...


Example 5: Debug idempotency keys

    # Redis CLI
    redis-cli
    > KEYS idempotency:*
    > GET idempotency:123:create_task:a1b2c3d4
    > TTL idempotency:123:create_task:a1b2c3d4  # Check remaining time
    > DEL idempotency:123:create_task:a1b2c3d4  # Manually remove
"""
