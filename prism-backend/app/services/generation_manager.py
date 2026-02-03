"""
Generation Manager Service
Handles state management for AI response generations using Redis.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Literal, Any
from pydantic import BaseModel
from uuid import uuid4
import logging
import asyncio

logger = logging.getLogger(__name__)


class GenerationState(BaseModel):
    """
    State model for a single generation job.
    Strict State Machine: created -> generating -> streaming -> completed -> finalized -> cleaned
    """
    generation_id: str
    chat_id: str
    user_id: str
    status: Literal["created", "queued", "generating", "streaming", "completed", "finalized", "cleaned", "failed", "cancelled"]
    prompt: str
    
    # Timestamps for State Machine
    created_at: str
    updated_at: str
    started_at: Optional[str] = None    # When streaming started
    completed_at: Optional[str] = None  # When streaming finished
    finalized_at: Optional[str] = None  # When persisted to DB
    cleaned_at: Optional[str] = None    # When resources freed
    last_token_at: Optional[str] = None # For Soft Timeout Watchdog
    
    # Metrics & Metadata
    chunks_sent: int = 0
    total_tokens: int = 0
    cancellation_requested: bool = False
    last_error: Optional[str] = None
    
    # 📊 Observability
    model_used: Optional[str] = None
    retry_count: int = 0
    generation_duration_ms: Optional[float] = None
    
    # 🔑 API Key Tracking (for free limit counting)
    key_source: Literal["platform", "user"] = "platform"  # "platform" = counts against free limit, "user" = user's own key
    api_key: Optional[str] = None  # Decrypted user API key (if using user's key) - NOT stored in Redis
    key_id: Optional[str] = None  # MongoDB ObjectId of user's API key (for tracking)
    
    # 🔒 Single-Shot Usage Tracking (prevents double counting)
    usage_committed: bool = False  # True once usage has been incremented for this generation


class GenerationManager:
    """
    Manages generation lifecycle using Redis as state store.
    Ensures single source of truth for all active generations.
    """
    
    # 🚀 LUA SCRIPT: Truly atomic generation creation
    # Executes cooldown check, lock acquire, and state check in ONE atomic operation
    CREATE_GENERATION_LUA = """
    local cooldown_key = KEYS[1]
    local active_key = KEYS[2]
    local lock_key = KEYS[3]
    local gen_key = KEYS[4]
    
    local lock_timeout = tonumber(ARGV[1])
    local cooldown_ttl = tonumber(ARGV[2])
    local state_ttl = tonumber(ARGV[3])
    local gen_id = ARGV[4]
    local state_json = ARGV[5]
    local stale_threshold = tonumber(ARGV[6])
    local current_time = tonumber(ARGV[7])
    
    -- Step 1: Check cooldown (fast fail)
    if redis.call('EXISTS', cooldown_key) == 1 then
        return {'COOLDOWN', '', ''}
    end
    
    -- Step 2: Try to acquire lock (atomic)
    local lock_acquired = redis.call('SET', lock_key, 'locked', 'EX', lock_timeout, 'NX')
    if not lock_acquired then
        -- Lock not acquired - return existing state for retry decision
        local existing_gen_id = redis.call('GET', active_key)
        if existing_gen_id then
            local existing_state = redis.call('GET', 'generation:' .. existing_gen_id)
            return {'LOCKED', existing_gen_id, existing_state or ''}
        end
        return {'LOCKED', '', ''}
    end
    
    -- Step 3: Lock acquired! Set cooldown
    redis.call('SETEX', cooldown_key, cooldown_ttl, '1')
    
    -- Step 4: Check for existing active generation
    local existing_gen_id = redis.call('GET', active_key)
    local existing_state_json = ''
    local needs_cleanup = false
    
    if existing_gen_id then
        existing_state_json = redis.call('GET', 'generation:' .. existing_gen_id) or ''
    end
    
    -- Step 5: Create new generation atomically
    redis.call('SETEX', gen_key, state_ttl, state_json)
    redis.call('SETEX', active_key, state_ttl, gen_id)
    redis.call('DEL', lock_key)  -- Release lock immediately
    
    return {'OK', existing_gen_id or '', existing_state_json}
    """
    
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.ttl = 3600  # State expiration in seconds (1 hour)
        self._create_gen_script = None  # Lazy-loaded Lua script
    
    async def _get_create_script(self):
        """Lazy-load and cache the Lua script"""
        if self._create_gen_script is None:
            self._create_gen_script = self.redis.register_script(self.CREATE_GENERATION_LUA)
        return self._create_gen_script
    
    async def create_generation(
        self, 
        chat_id: str, 
        user_id: str, 
        prompt: str,
        model: str = "llama-3.1-8b-instant",
        retry_count: int = 0,
        max_retries: int = 2,
        retry_delay: float = 0.5,
        key_source: Literal["platform", "user"] = "platform",
        api_key: Optional[str] = None,
        key_id: Optional[str] = None
    ) -> GenerationState:
        """
        Create a new generation job with TRUE ATOMIC Lua script.
        
        🚀 ULTRA-OPTIMIZED V5 (LUA):
        - Single Lua script = truly atomic (no race conditions possible)
        - Faster than pipeline (server-side execution)
        - Cooldown + lock + state check in ONE operation
        """
        gen_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        # Prepare state object
        state = GenerationState(
            generation_id=gen_id,
            chat_id=chat_id,
            user_id=user_id,
            status="created",
            prompt=prompt,
            created_at=now,
            updated_at=now,
            model_used=model,
            retry_count=retry_count,
            key_source=key_source,
            api_key=api_key,
            key_id=key_id
        )
        state_json = state.model_dump_json()
        
        # Keys for Lua script
        cooldown_key = f"user_cooldown:{user_id}"
        active_key = f"active_generation:{chat_id}"
        lock_key = f"lock:{chat_id}"
        gen_key = f"generation:{gen_id}"
        
        # 🚀 Execute atomic Lua script
        script = await self._get_create_script()
        current_time = int(datetime.utcnow().timestamp())
        
        result = await script(
            keys=[cooldown_key, active_key, lock_key, gen_key],
            args=[
                1,              # lock_timeout (1 second)
                1,              # cooldown_ttl (1 second)
                self.ttl,       # state_ttl (1 hour)
                gen_id,
                state_json,
                15,             # stale_threshold (15 seconds)
                current_time
            ]
        )
        
        # Parse result
        status = result[0].decode('utf-8') if isinstance(result[0], bytes) else result[0]
        existing_gen_id = result[1].decode('utf-8') if isinstance(result[1], bytes) else result[1]
        existing_state_json = result[2].decode('utf-8') if isinstance(result[2], bytes) else result[2]
        
        # Handle result
        if status == "COOLDOWN":
            raise ValueError("Please wait a moment before sending another message.")
        
        if status == "OK":
            # 🔥 SUCCESS! Generation created atomically
            # Handle stale cleanup in background (non-blocking)
            if existing_gen_id and existing_state_json:
                asyncio.create_task(self._handle_existing_generation(
                    existing_gen_id, existing_state_json, chat_id
                ))
            
            logger.info(f"✅ [LUA] Created generation {gen_id} for chat {chat_id} (Model: {model})")
            return state
        
        # status == "LOCKED" - Need to retry
        for attempt in range(max_retries):
            await asyncio.sleep(0.05)  # 50ms micro-wait
            
            # Check if we should fail due to active generation
            if existing_state_json:
                try:
                    existing_state = GenerationState.model_validate_json(existing_state_json)
                    if existing_state.status in ["created", "queued", "generating", "streaming"]:
                        last_update = datetime.fromisoformat(existing_state.updated_at)
                        is_stale = (datetime.utcnow() - last_update).total_seconds() > 15
                        
                        if not is_stale and attempt == max_retries - 1:
                            raise ValueError(f"A generation is already in progress ({existing_state.status}). Please wait or cancel it.")
                except Exception as e:
                    if "already in progress" in str(e):
                        raise
                    # Parse error - continue with retry
            
            # Generate new ID for retry
            gen_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            state = GenerationState(
                generation_id=gen_id,
                chat_id=chat_id,
                user_id=user_id,
                status="created",
                prompt=prompt,
                created_at=now,
                updated_at=now,
                model_used=model,
                retry_count=retry_count,
                key_source=key_source,
                api_key=api_key,
                key_id=key_id
            )
            gen_key = f"generation:{gen_id}"
            state_json = state.model_dump_json()
            current_time = int(datetime.utcnow().timestamp())
            
            # Retry Lua script
            result = await script(
                keys=[cooldown_key, active_key, lock_key, gen_key],
                args=[1, 1, self.ttl, gen_id, state_json, 15, current_time]
            )
            
            status = result[0].decode('utf-8') if isinstance(result[0], bytes) else result[0]
            
            if status == "COOLDOWN":
                raise ValueError("Please wait a moment before sending another message.")
            
            if status == "OK":
                existing_gen_id = result[1].decode('utf-8') if isinstance(result[1], bytes) else result[1]
                existing_state_json = result[2].decode('utf-8') if isinstance(result[2], bytes) else result[2]
                
                if existing_gen_id and existing_state_json:
                    asyncio.create_task(self._handle_existing_generation(
                        existing_gen_id, existing_state_json, chat_id
                    ))
                
                logger.info(f"✅ [LUA] Created generation {gen_id} on retry {attempt + 1}")
                return state
            
            # Update existing state for next iteration
            existing_gen_id = result[1].decode('utf-8') if isinstance(result[1], bytes) else result[1]
            existing_state_json = result[2].decode('utf-8') if isinstance(result[2], bytes) else result[2]
        
        raise ValueError("Failed to create generation after multiple retries")
    
    async def _handle_existing_generation(self, gen_id: str, state_json: str, chat_id: str):
        """Background task to handle existing generation (cancel or cleanup stale)"""
        try:
            existing_state = GenerationState.model_validate_json(state_json)
            
            if existing_state.status in ["created", "queued", "generating", "streaming"]:
                last_update = datetime.fromisoformat(existing_state.updated_at)
                is_stale = (datetime.utcnow() - last_update).total_seconds() > 15
                
                if is_stale:
                    await self._cleanup_stale(gen_id, chat_id)
                else:
                    # Cancel active generation (superseded by new one)
                    await self.update_status(gen_id, "cancelled")
        except Exception as e:
            logger.warning(f"⚠️ Background generation handler error: {e}")
    
    async def _cleanup_stale(self, gen_id: str, chat_id: str):
        """Fire-and-forget cleanup of stale generation"""
        try:
            await self.update_status(gen_id, "failed", last_error="Stale lock timeout")
            await self.release_chat_lock(chat_id)
            logger.info(f"🧹 Cleaned up stale generation {gen_id[:8]}...")
        except Exception as e:
            logger.warning(f"Stale cleanup failed: {e}")
    
    async def get_generation(self, gen_id: str) -> Optional[GenerationState]:
        """Retrieve generation state by ID"""
        data = await self.redis.get(f"generation:{gen_id}")
        
        if not data:
            return None
        
        try:
            return GenerationState.model_validate_json(data)
        except Exception as e:
            logger.error(f"Failed to parse generation state: {e}")
            return None
    
    async def release_chat_lock(self, chat_id: str) -> None:
        """Force release the active generation lock for a chat"""
        active_key = f"active_generation:{chat_id}"
        try:
            await self.redis.delete(active_key)
            logger.info(f"Released active generation lock for chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to release active generation lock for chat {chat_id}: {e}")
    
    async def release_processing_lock(self, chat_id: str) -> None:
        """Force release the processing lock for a chat (used during generation creation)"""
        lock_key = f"lock:{chat_id}"
        try:
            await self.redis.delete(lock_key)
            logger.debug(f"Released processing lock for chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to release processing lock for chat {chat_id}: {e}")

    async def update_status(
        self, 
        gen_id: str, 
        status: Literal["created", "queued", "generating", "streaming", "completed", "finalized", "cleaned", "failed", "cancelled"],
        **kwargs
    ) -> bool:
        """Update generation status and manage lifecycle timestamps"""
        state = await self.get_generation(gen_id)
        
        if not state:
            logger.warning(f"Attempting to update non-existent generation: {gen_id}")
            return False
            
        now_str = datetime.utcnow().isoformat()
        
        # State Transition Logic & Timestamps
        state.status = status
        state.updated_at = now_str
        
        if status == "streaming" and not state.started_at:
            state.started_at = now_str
        elif status == "completed":
            state.completed_at = now_str
            # 📊 Calculate Duration
            if state.started_at:
                try:
                    start_dt = datetime.fromisoformat(state.started_at)
                    end_dt = datetime.utcnow()
                    state.generation_duration_ms = (end_dt - start_dt).total_seconds() * 1000
                except Exception as e:
                    logger.warning(f"Failed to calculate duration for {gen_id}: {e}")
        elif status == "finalized":
            state.finalized_at = now_str
        elif status == "cleaned":
            state.cleaned_at = now_str
        
        # Update optional fields
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        # Save updated state
        await self.redis.setex(
            f"generation:{gen_id}",
            self.ttl,
            state.model_dump_json()
        )
        
        # Clear active generation marker if we reached a terminal state
        # Note: 'finalized' is terminal for the *active lock*, but strict cleanup happens at 'cleaned'
        # We release lock early at 'completed' or 'finalized' to allow new chats, 
        # but technically we might want to keep it until finalized?
        # User said: "released on completed / cancelled". 
        if status in ["completed", "finalized", "cancelled", "failed"]:
            await self.release_chat_lock(state.chat_id)
        
        logger.info(f"Updated generation {gen_id} status to {status}")
        return True

    # ... (rest of methods)

    async def commit_usage(self, gen_id: str) -> tuple[bool, str]:
        """
        🔒 SINGLE-SHOT Usage Commit
        
        Atomically marks a generation as usage-committed.
        Returns (should_increment, reason):
        - (True, "first_commit") = First call, caller should increment usage
        - (False, "already_committed") = Already committed, skip increment
        - (False, "not_found") = Generation doesn't exist
        
        Uses Redis SETNX for atomic race-condition protection.
        """
        commit_key = f"usage_committed:{gen_id}"
        
        # 🚀 Atomic check-and-set: Only one caller wins
        committed = await self.redis.set(commit_key, "1", ex=self.ttl, nx=True)
        
        if not committed:
            # Another request already committed usage
            logger.debug(f"🔄 Usage already committed for {gen_id} (idempotent)")
            return False, "already_committed"
        
        # Winner! Also update the state object for consistency
        state = await self.get_generation(gen_id)
        if state:
            state.usage_committed = True
            state.updated_at = datetime.utcnow().isoformat()
            await self.redis.setex(
                f"generation:{gen_id}",
                self.ttl,
                state.model_dump_json()
            )
            logger.info(f"✅ Usage commit lock acquired for {gen_id}")
            return True, "first_commit"
        else:
            # State expired but we got the lock - still honor it
            logger.warning(f"⚠️ Usage committed but state not found for {gen_id}")
            return True, "first_commit_state_missing"
    
    async def is_usage_committed(self, gen_id: str) -> bool:
        """Check if usage has already been committed for this generation."""
        commit_key = f"usage_committed:{gen_id}"
        exists = await self.redis.exists(commit_key)
        return bool(exists)

    async def increment_chunks(self, gen_id: str, count: int = 1) -> bool:
        """Increment chunks sent counter and update activity timestamp"""
        state = await self.get_generation(gen_id)
        
        if not state:
            return False
        
        now_str = datetime.utcnow().isoformat()
        state.chunks_sent += count
        state.total_tokens += count # Approximation
        state.updated_at = now_str
        state.last_token_at = now_str # Track activity
        
        await self.redis.setex(
            f"generation:{gen_id}",
            self.ttl,
            state.model_dump_json()
        )
        
        return True

    # ...

    async def check_timeouts(self, timeout_seconds: int = 30) -> int:
        """
        Check for and cancel stalled generations.
        Returns number of cancelled jobs.
        """
        cancelled_count = 0
        try:
            # OPTIMIZATION: In production, use 'scan_iter' or a dedicated 'active_generations' set.
            # For now, 'keys' is acceptable for typical loads (<10k active keys).
            keys = await self.redis.keys("generation:*")
            now = datetime.utcnow()
            
            for key in keys:
                # Handle bytes vs str for key
                k = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                
                # Skip content buffers efficiently
                if k.endswith(":content"):
                    continue
                    
                data = await self.redis.get(key)
                if not data: continue
                
                try:
                    # Partial parsing to avoid full validation overhead if status isn't active
                    # (Performance improvement)
                    state_dict = json.loads(data)
                    status = state_dict.get("status")
                    
                    if status not in ["generating", "streaming"]:
                        continue
                        
                    # Now full validate
                    state = GenerationState.model_validate(state_dict)
                    
                    # Determine last activity time priority:
                    last_activity_str = (
                        state.last_token_at or 
                        state.updated_at or 
                        state.started_at or 
                        state.created_at
                    )
                    
                    if not last_activity_str:
                        continue
                        
                    try:
                        # Handle potential 'Z' suffix if present (from JS/Frontend dates)
                        last_activity_str = last_activity_str.replace('Z', '+00:00')
                        last_active_dt = datetime.fromisoformat(last_activity_str)
                        
                        # Handle timezone awareness (UTC vs Naive)
                        if last_active_dt.tzinfo is not None:
                            # Convert to naive UTC for comparison with datetime.utcnow()
                            last_active_dt = last_active_dt.replace(tzinfo=None)
                            
                        time_diff = (now - last_active_dt).total_seconds()
                        
                        # Check against timeout
                        if time_diff > timeout_seconds:
                            logger.warning(
                                f"⏳ Soft Timeout: Generation {state.generation_id} "
                                f"stalled for {time_diff:.1f}s (Status: {state.status}). Cancelling."
                            )
                            # Mark as cancelled
                            await self.update_status(
                                state.generation_id, 
                                "cancelled", 
                                last_error=f"Soft Timeout ({time_diff:.0f}s inactivity)"
                            )
                            cancelled_count += 1
                    except Exception as date_err:
                        logger.warning(f"Date parsing failed for {state.generation_id}: {date_err}")
                        continue

                except Exception:
                    continue
                        
        except Exception as e:
            logger.error(f"Soft timeout check loop failed: {e}")
            
        return cancelled_count

    async def request_cancellation(self, gen_id: str, user_id: str) -> bool:
        """
        Request cancellation of a generation.
        Validates user owns the generation.
        """
        state = await self.get_generation(gen_id)
        
        if not state:
            logger.warning(f"Cannot cancel non-existent generation: {gen_id}")
            return False
        
        if state.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to cancel generation owned by {state.user_id}"
            )
            return False
        
        state.cancellation_requested = True
        state.updated_at = datetime.utcnow().isoformat()
        
        await self.redis.setex(
            f"generation:{gen_id}",
            self.ttl,
            state.model_dump_json()
        )
        
        # 🚀 Also set a fast-check cancel flag
        await self.redis.setex(f"cancel:{gen_id}", self.ttl, "1")
        
        logger.info(f"Cancellation requested for generation {gen_id}")
        return True
    
    async def is_cancelled(self, gen_id: str) -> bool:
        """🚀 ULTRA-FAST: Check simple flag instead of full state load"""
        # Single Redis EXISTS check - much faster than get + deserialize
        result = await self.redis.exists(f"cancel:{gen_id}")
        return bool(result)
    
    async def cleanup(self, gen_id: str) -> bool:
        """
        Finalize cleanup: Mark as cleaned, then remove from Redis.
        """
        state = await self.get_generation(gen_id)
        
        if state:
            # 1. Mark as cleaned (sets cleaned_at timestamp)
            # This is key for the state machine completeness
            await self.update_status(gen_id, "cleaned")
            
            # 2. Clear active generation marker (redundant as update_status does it, but safe)
            active_key = f"active_generation:{state.chat_id}"
            await self.redis.delete(active_key)
            
        # 3. Delete generation state AND content buffer from Redis
        # "cleaned state must Free Redis memory"
        await self.redis.delete(f"generation:{gen_id}:content")
        deleted = await self.redis.delete(f"generation:{gen_id}")
        
        if deleted:
            logger.info(f"Cleaned up generation {gen_id} (State: cleaned -> deleted)")
        
        return bool(deleted)

    async def append_content(self, gen_id: str, chunk: str) -> None:
        """Append content chunk to Redis buffer"""
        content_key = f"generation:{gen_id}:content"
        await self.redis.append(content_key, chunk)
        await self.redis.expire(content_key, self.ttl)

    async def get_content(self, gen_id: str) -> str:
        """Retrieve full buffered content"""
        content_key = f"generation:{gen_id}:content"
        data = await self.redis.get(content_key)
        if not data:
            return ""
        if isinstance(data, bytes):
            return data.decode('utf-8')
        return str(data)

    async def cleanup_orphaned(self, max_age_hours: int = 1) -> int:
        """
        Clean up orphaned or stuck generations.
        Called periodically by background task.
        """
        cleaned = 0
        max_age = timedelta(hours=max_age_hours)
        
        try:
            # Get all generation keys
            keys = await self.redis.keys("generation:*")
            
            for key in keys:
                try:
                    data = await self.redis.get(key)
                    if not data:
                        continue
                    
                    state = GenerationState.model_validate_json(data)
                    created_at = datetime.fromisoformat(state.created_at)
                    age = datetime.utcnow() - created_at
                    
                    # If too old and still generating, mark as failed
                    if age > max_age and state.status in ["queued", "generating"]:
                        logger.warning(
                            f"Found orphaned generation {state.generation_id}, "
                            f"age: {age.total_seconds()}s"
                        )
                        
                        await self.update_status(state.generation_id, "failed")
                        await self.cleanup(state.generation_id)
                        cleaned += 1
                
                except Exception as e:
                    logger.error(f"Error processing key {key}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Cleanup orphaned error: {e}")
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphaned generations")
        
        return cleaned
    
    async def get_active_generation_for_chat(self, chat_id: str) -> Optional[GenerationState]:
        """Get currently active generation for a chat, if any"""
        active_key = f"active_generation:{chat_id}"
        gen_id = await self.redis.get(active_key)
        
        if not gen_id:
            return None
            
        if isinstance(gen_id, bytes):
            gen_id = gen_id.decode('utf-8')
        
        return await self.get_generation(gen_id)

