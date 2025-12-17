"""
🚀 Part 19: Structured Logging for Fast Debugging

Every request logs:
- user_id
- session_id
- intent (what user wants)
- latency (how long it took)
- error_type (if failed)

Benefits:
- Fast debugging with grep/search
- Track user journeys
- Identify slow operations
- Monitor error patterns
"""

import logging
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class StructuredLogger:
    """
    🚀 Part 19: Structured logger for requests and operations.
    
    Logs in JSON format for easy parsing and analysis.
    """
    
    @staticmethod
    def log_request(
        user_id: str,
        session_id: Optional[str],
        intent: str,
        latency_ms: float,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log structured request data.
        
        Args:
            user_id: User identifier
            session_id: Chat session ID (if applicable)
            intent: What the user wants (e.g., "create_task", "chat_message", "list_tasks")
            latency_ms: Time taken in milliseconds
            success: Whether operation succeeded
            error_type: Type of error (e.g., "ValidationError", "DatabaseError")
            error_message: Error message (truncated)
            metadata: Additional context (task_id, message_count, etc.)
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "intent": intent,
            "latency_ms": round(latency_ms, 2),
            "success": success
        }
        
        if error_type:
            log_data["error_type"] = error_type
        
        if error_message:
            log_data["error_message"] = error_message[:200]  # Truncate long errors
        
        if metadata:
            log_data["metadata"] = metadata
        
        # Log as JSON for easy parsing
        log_json = json.dumps(log_data)
        
        if success:
            logger.info(f"📊 REQUEST | {log_json}")
        else:
            logger.warning(f"⚠️ REQUEST_ERROR | {log_json}")
    
    @staticmethod
    def log_operation(
        operation: str,
        user_id: str,
        latency_ms: float,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log structured operation data (DB queries, API calls, etc.).
        
        Args:
            operation: Operation name (e.g., "mongodb_query", "redis_get", "neo4j_write")
            user_id: User identifier
            latency_ms: Time taken in milliseconds
            success: Whether operation succeeded
            error_type: Type of error
            metadata: Additional context (query, collection, etc.)
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "latency_ms": round(latency_ms, 2),
            "success": success
        }
        
        if error_type:
            log_data["error_type"] = error_type
        
        if metadata:
            log_data["metadata"] = metadata
        
        log_json = json.dumps(log_data)
        
        if success:
            logger.debug(f"🔧 OPERATION | {log_json}")
        else:
            logger.warning(f"⚠️ OPERATION_ERROR | {log_json}")


@contextmanager
def track_request(
    user_id: str,
    intent: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager to track request timing and log automatically.
    
    Usage:
        with track_request(user_id="123", intent="create_task", session_id="abc"):
            result = create_task(...)
            # Logs automatically with timing
    """
    start_time = time.time()
    error_type = None
    error_message = None
    
    try:
        yield
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        
        StructuredLogger.log_request(
            user_id=user_id,
            session_id=session_id,
            intent=intent,
            latency_ms=latency_ms,
            success=error_type is None,
            error_type=error_type,
            error_message=error_message,
            metadata=metadata
        )


@contextmanager
def track_operation(
    operation: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager to track operation timing and log automatically.
    
    Usage:
        with track_operation("mongodb_query", user_id="123", metadata={"collection": "tasks"}):
            result = await tasks_collection.find_one({"_id": task_id})
            # Logs automatically with timing
    """
    start_time = time.time()
    error_type = None
    
    try:
        yield
    except Exception as e:
        error_type = type(e).__name__
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        
        StructuredLogger.log_operation(
            operation=operation,
            user_id=user_id,
            latency_ms=latency_ms,
            success=error_type is None,
            error_type=error_type,
            metadata=metadata
        )


# ========== CONVENIENCE FUNCTIONS ==========

def log_chat_message(
    user_id: str,
    session_id: str,
    intent: str,
    latency_ms: float,
    message_length: int,
    success: bool = True,
    error_type: Optional[str] = None
):
    """Log chat message processing"""
    StructuredLogger.log_request(
        user_id=user_id,
        session_id=session_id,
        intent=f"chat_{intent}",
        latency_ms=latency_ms,
        success=success,
        error_type=error_type,
        metadata={"message_length": message_length}
    )


def log_task_operation(
    user_id: str,
    intent: str,
    latency_ms: float,
    task_id: Optional[str] = None,
    success: bool = True,
    error_type: Optional[str] = None
):
    """Log task operation (create, update, cancel)"""
    metadata = {}
    if task_id:
        metadata["task_id"] = task_id
    
    StructuredLogger.log_request(
        user_id=user_id,
        session_id=None,
        intent=f"task_{intent}",
        latency_ms=latency_ms,
        success=success,
        error_type=error_type,
        metadata=metadata
    )


def log_memory_operation(
    user_id: str,
    operation: str,
    latency_ms: float,
    db_type: str,
    success: bool = True,
    error_type: Optional[str] = None
):
    """Log memory operation (MongoDB, Redis, Neo4j, Pinecone)"""
    StructuredLogger.log_operation(
        operation=f"{db_type}_{operation}",
        user_id=user_id,
        latency_ms=latency_ms,
        success=success,
        error_type=error_type,
        metadata={"db": db_type}
    )


# ========== USAGE EXAMPLES ==========

"""
Example 1: Track entire request with context manager

    @router.post("/tasks/confirm")
    async def confirm_task(payload: dict, user: dict = Depends(get_current_user)):
        user_id = user.get("id")
        
        with track_request(user_id=user_id, intent="create_task"):
            result = await create_task(payload)
            return result
        # Automatically logs: user_id, intent, latency, success


Example 2: Manual logging with detailed metadata

    @router.post("/chat")
    async def chat(message: str, user: dict = Depends(get_current_user)):
        start = time.time()
        user_id = user.get("id")
        session_id = message.get("session_id")
        
        try:
            response = await process_message(message)
            latency_ms = (time.time() - start) * 1000
            
            log_chat_message(
                user_id=user_id,
                session_id=session_id,
                intent="general_chat",
                latency_ms=latency_ms,
                message_length=len(message),
                success=True
            )
            
            return response
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            log_chat_message(
                user_id=user_id,
                session_id=session_id,
                intent="general_chat",
                latency_ms=latency_ms,
                message_length=len(message),
                success=False,
                error_type=type(e).__name__
            )
            raise


Example 3: Track DB operation

    async def get_user_tasks(user_id: str):
        with track_operation("mongodb_query", user_id, metadata={"collection": "tasks"}):
            tasks = await tasks_collection.find({"userId": user_id}).to_list(100)
        # Automatically logs: operation, user_id, latency
        return tasks


Example 4: Grep/search logs

    # Find all slow requests (>1000ms)
    grep "latency_ms.*[0-9]{4,}" app.log
    
    # Find all errors for user 123
    grep "user_id.*123.*success.*false" app.log
    
    # Find all task creation attempts
    grep "intent.*create_task" app.log
    
    # Find all Redis errors
    grep "OPERATION_ERROR.*redis" app.log


Example 5: JSON parsing for analytics

    import json
    
    def analyze_logs(log_file):
        slow_requests = []
        error_counts = {}
        
        with open(log_file) as f:
            for line in f:
                if "REQUEST |" in line:
                    # Extract JSON from log line
                    json_str = line.split("REQUEST | ")[1]
                    data = json.loads(json_str)
                    
                    # Find slow requests
                    if data["latency_ms"] > 1000:
                        slow_requests.append(data)
                    
                    # Count errors by type
                    if not data["success"]:
                        error_type = data.get("error_type", "Unknown")
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return slow_requests, error_counts
"""
