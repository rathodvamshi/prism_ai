"""
Streaming Router
Handles SSE-based streaming of AI responses with cancellation support.

🚀 V2: Speculative Start - Stream begins immediately, validation happens async
🎚️ V3: Adaptive Quality - Smart load shedding based on system conditions
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import AsyncGenerator, Optional
import json
import asyncio
import logging
import re
from datetime import datetime
from uuid import uuid4

from app.services.generation_manager import GenerationManager, GenerationState
from app.services.input_validator import InputValidator, default_validator
from app.db.mongo_client import get_database
from app.utils.auth import get_current_user_from_session
from app.db.redis_client import get_redis_client
from app.services.main_brain import generate_response_stream
from app.models.chat_models import MessageRole
from app.routers.api_keys import (
    increment_free_usage,
    increment_user_key_usage,
    get_api_key_for_user,
    handle_key_exhaustion,
    get_current_key_id_for_user,
    ErrorCodes
)

# 🎚️ Import Adaptive Quality Service
try:
    from app.services.adaptive_quality import adaptive_quality
    ADAPTIVE_QUALITY_AVAILABLE = True
except ImportError:
    ADAPTIVE_QUALITY_AVAILABLE = False

# 🛡️ SHARED METADATA PATTERN - Never send to UI (Internal Analytics only)
# INFO: ACTION tags are NOT filtered here because the Frontend needs them to trigger UI components.
# Frontend parser handles hiding ACTION tags from visible text.
METADATA_PATTERN = re.compile(r'<!--\s*THINKING_DATA:.*?-->', re.DOTALL)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/streaming", tags=["streaming"])


# Dependency to extract user_id string from User object
async def get_user_id_string(current_user = Depends(get_current_user_from_session)) -> str:
    """Extract user_id string from User object"""
    return str(current_user.user_id)


# Dependency injection
async def get_generation_manager(redis_client = Depends(get_redis_client)) -> GenerationManager:
    """Get generation manager instance"""
    return GenerationManager(redis_client)


def get_input_validator() -> InputValidator:
    """Get input validator instance"""
    return default_validator


class GenerateRequest(BaseModel):
    """Request to start a new generation"""
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    mode: Optional[str] = "text"  # "text" or "voice"


class GenerateResponse(BaseModel):
    """Response with generation ID to start streaming"""
    generation_id: str
    chat_id: str
    status: str


class FinalizeRequest(BaseModel):
    """Request to finalize and persist a completed generation"""
    final_content: Optional[str] = None
    metadata: Optional[dict] = {}


@router.post("/chat/{chat_id}/finalize/{generation_id}")
async def finalize_generation(
    chat_id: str,
    generation_id: str,
    request: Optional[FinalizeRequest] = None,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager)
):
    """
    Finalize and persist a completed generation.
    Safe, idempotent, and reload-proof.
    
    🚀 OPTIMIZED V2: Parallel operations for faster response
    """
    from app.db.mongo_client import sessions_collection
    from bson import ObjectId
    import uuid
    
    try:
        mongo_user_id = ObjectId(user_id)
    except:
        mongo_user_id = user_id

    # 🚀 PARALLEL: Check idempotency AND fetch state simultaneously
    existing_msg_task = sessions_collection.find_one(
        {
            "$and": [
                {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                {"$or": [{"user_id": mongo_user_id}, {"userId": user_id}]},
                {"messages.generation_id": generation_id}
            ]
        },
        {"_id": 1}
    )
    state_task = gen_manager.get_generation(generation_id)
    
    existing_msg, state = await asyncio.gather(existing_msg_task, state_task)
    
    if existing_msg:
        logger.info(f"✅ Generation {generation_id} already persisted. Returning 200 OK (Idempotent).")
        asyncio.create_task(gen_manager.cleanup(generation_id))  # Fire-and-forget
        return {
            "status": "ok",
            "message": "Already finalized",
            "generation_id": generation_id
        }
    
    # 3. Handle Missing Generation (Graceful 200)
    # If state is missing, it was likely already cleaned up or never existed.
    # Don't error, just assume success.
    if not state:
        logger.info(f"⚠️ Finalize called for missing generation {generation_id}. Assuming already cleaned/done. Returning 200 OK.")
        return {
            "status": "ok",
            "message": "Generation not found (likely already cleaned)",
            "generation_id": generation_id
        }
    
    # 4. Verify Ownership (Security)
    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 5. Handle Statuses
    logger.info(f"🔍 Finalizing generation {generation_id} | Status: {state.status}")

    # If already cancelled, failed, or unknown -> return 200 OK
    if state.status in ["cancelled", "failed", "cleaned"]:
        logger.info(f"Generation {generation_id} is {state.status}. Skipping persistence.")
        asyncio.create_task(gen_manager.cleanup(generation_id))
        return {
            "status": "ok",
            "message": f"Generation was {state.status}",
            "generation_id": generation_id
        }

    # If no content provided, we can't save proper messages
    # But we should still cleanup and return success
    final_content = request.final_content if request else None
    
    if not final_content:
        logger.info(f"Finalize called without content for {generation_id}. Checking Redis buffer...")
        final_content = await gen_manager.get_content(generation_id)

    if not final_content:
        logger.warning(f"Finalize called without content for {generation_id}. Marking complete without saving messages.")
        await gen_manager.update_status(generation_id, "completed")
        asyncio.create_task(gen_manager.cleanup(generation_id))
        return {
             "status": "ok", 
             "message": "Marked completed (no content to save)",
             "generation_id": generation_id
        }

    # 6. Persist to MongoDB (The Real Work)
    try:
        now_utc = datetime.utcnow()
        now_iso = now_utc.isoformat()
        
        # Prepare User Message
        user_message_id = str(uuid.uuid4())
        user_message_doc = {
            "id": user_message_id,
            "message_id": user_message_id,
            "role": MessageRole.USER.value,
            "content": state.prompt,
            "generation_id": generation_id,
            "timestamp": now_utc,
            "created_at": now_iso,
            "metadata": {"source": "web_client"}
        }
        
        # Prepare Assistant Message
        assistant_message_id = str(uuid.uuid4())
        metadata = request.metadata or {} if request else {}
        assistant_message_doc = {
            "id": assistant_message_id,
            "message_id": assistant_message_id,
            "role": MessageRole.ASSISTANT.value,
            "content": final_content,
            "generation_id": generation_id,
            "metadata": metadata,
            "timestamp": now_utc,
            "created_at": now_iso,
            "chunks_sent": state.chunks_sent
        }
        
        # Atomic Push
        result = await sessions_collection.update_one(
            {
                "$and": [
                    {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                    {"$or": [{"user_id": mongo_user_id}, {"userId": user_id}]}
                ]
            },
            {
                "$push": {
                    "messages": {
                        "$each": [user_message_doc, assistant_message_doc]
                    }
                },
                "$set": {
                    "updated_at": now_utc,
                    "updatedAt": now_utc
                }
            }
        )
        
        if result.matched_count == 0:
            # Session lost?
            logger.warning(f"Session {chat_id} not found during finalize. Msg not saved.")
            # Don't error, just return OK. It's not the client's fault session is gone.
            return {"status": "ok", "message": "Session not found, but accepted"}

        # 7. � SINGLE-SHOT Usage Tracking (prevents double counting)
        async def commit_usage_once():
            """
            Commit usage exactly ONCE per generation_id.
            Uses atomic Redis lock to prevent race conditions.
            """
            try:
                # 🔒 Atomic check: Only the first caller wins
                should_commit, reason = await gen_manager.commit_usage(generation_id)
                
                if not should_commit:
                    logger.debug(f"🔄 Usage already committed for {generation_id[:8]}... ({reason})")
                    return {"committed": False, "reason": reason}
                
                # ✅ First caller - actually increment usage
                if state.key_source == "platform":
                    usage_result = await increment_free_usage(user_id, generation_id)
                    if usage_result.get("success"):
                        logger.info(f"✅ [SINGLE-SHOT] Free usage: {usage_result['new_count']}/10 for user {user_id[:8]}...")
                    return {"committed": True, "usage": usage_result}
                else:
                    key_id = state.key_id or await get_current_key_id_for_user(user_id)
                    if key_id:
                        result = await increment_user_key_usage(user_id, key_id, generation_id)
                        logger.info(f"✅ [SINGLE-SHOT] User key usage tracked for {user_id[:8]}...")
                        return {"committed": True, "usage": result}
                    return {"committed": True, "usage": None}
                    
            except Exception as e:
                logger.warning(f"⚠️ Single-shot usage commit error: {e}")
                return {"committed": False, "error": str(e)}
        
        # 🚀 Fire-and-forget: Don't wait for usage tracking
        asyncio.create_task(commit_usage_once())

        # 8. 🚀 OPTIMIZED: Parallel status update + cleanup trigger
        asyncio.create_task(gen_manager.update_status(generation_id, "finalized"))
        asyncio.create_task(gen_manager.cleanup(generation_id))
        
        # 9. ✨ PRO AUTO-RENAME: Generating perfect titles automatically
        # Runs in background to keep UI snappy
        async def auto_rename_pro():
            try:
                # Check current title
                current_session = await sessions_collection.find_one(
                    {"chat_id": chat_id}, 
                    {"title": 1, "messages": 1}
                )
                
                if not current_session: return
                
                current_title = current_session.get("title", "New Chat")
                # Default variations to catch (including simple greetings)
                is_default = current_title in ["New Chat", "Chat", "Untitled", "New Conversation", "New Beginning", "New Idea"]
                
                # Only rename if default and early in conversation (<= 4 messages)
                msg_count = len(current_session.get("messages", []))
                
                if is_default and msg_count <= 6:  # Allow up to 3 turns before giving up on renaming
                    from app.utils.llm_client import generate_chat_title
                    
                    # Generate punchy title using the prompt + response context
                    new_title = await generate_chat_title(state.prompt, final_content)
                    
                    if new_title and len(new_title) > 2:
                        await sessions_collection.update_one(
                            {"chat_id": chat_id},
                            {"$set": {"title": new_title}}
                        )
                        logger.info(f"✨ Auto-Renamed Session {chat_id} -> '{new_title}'")
            except Exception as e:
                logger.warning(f"⚠️ Auto-rename failed: {e}")

        asyncio.create_task(auto_rename_pro())
        
        logger.info(f"✅ State Machine: {generation_id} -> finalized -> cleanup")
        
        # Build response with usage info for frontend
        # 🚀 Note: usage_result tracked in background, frontend will poll /api-keys/usage
        response_data = {
            "message_id": assistant_message_id,
            "generation_id": generation_id,
            "status": "persisted",
            "key_source": state.key_source,  # "platform" or "user"
            "model": state.model_used or "llama-3.1-8b-instant",
        }
        
        return response_data
    
    except Exception as e:
        logger.error(f"❌ Finalize Logic Error: {e}", exc_info=True)
        # Even on error, return 200 OK so frontend doesn't crash?
        # User said "Finalize should never break the system".
        # But if we failed to save, maybe we should let them retry?
        # User said: "Prevent crashes on refresh / retries... Return 200 OK even if already finalized"
        # If DB write fails, it's a real error. I will Use a generic 500 but caught by global handler.
        # Wait, user said "Do NOT throw raw exceptions... return 200 OK"
        # I will return a success-like response but log the error heavily.
        return JSONResponse(
            status_code=200, # Fake 200 to prevent frontend crash
            content={
                "status": "error",
                "message": "Finalization accepted but persistence failed", 
                "detail": str(e)
            }
        )





@router.post("/chat/{chat_id}/generate", response_model=GenerateResponse)
async def create_generation(
    chat_id: str,
    request: GenerateRequest,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager),
    validator: InputValidator = Depends(get_input_validator)
):
    """
    Create a new generation job.
    Returns generation_id to start streaming.
    OPTIMIZED: Single API key lookup instead of duplicate calls.
    """
    import time
    start_time = time.time()
    
    try:
        # Validate input FIRST (fast, no DB)
        if not request.prompt or not request.prompt.strip():
             raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        validation = validator.validate_or_raise(request.prompt)
        validation_time = (time.time() - start_time) * 1000
        
        if validation.warnings:
            logger.warning(f"Input warnings for user {user_id}: {validation.warnings}")
        
        # SINGLE API key check - replaces both check_can_make_request AND get_api_key_for_user
        # This eliminates the duplicate database calls that were causing 9+ second delays
        key_check_start = time.time()
        user_api_key, key_source, error_code, selected_model = await get_api_key_for_user(user_id)
        key_check_time = (time.time() - key_check_start) * 1000
        
        # Handle errors (moved from check_can_make_request)
        if not user_api_key:
            if error_code == ErrorCodes.FREE_LIMIT_EXCEEDED:
                message = "⚠️ Free limit reached. You've used all 10 free requests. Add your Groq API key to continue."
            elif error_code == ErrorCodes.ALL_KEYS_EXHAUSTED:
                message = "🚫 All your API keys are temporarily exhausted. Limits reset daily on Groq. You can wait until tomorrow or add a new API key."
            else:
                message = "Unable to process request. Please try again later."
            
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": error_code or "FREE_LIMIT_EXCEEDED",
                    "message": message
                }
            )
        
        # Get key_id if using user's key (for tracking)
        key_id = None
        if key_source == "user":
            key_id = await get_current_key_id_for_user(user_id)
        
        # Create generation with key info
        gen_create_start = time.time()
        state = await gen_manager.create_generation(
            chat_id=chat_id,
            user_id=user_id,
            prompt=request.prompt,
            key_source=key_source,
            api_key=user_api_key,  # Pass the actual API key
            key_id=key_id,  # Pass the key ID for tracking
            model=selected_model or "llama-3.1-8b-instant"  # Pass user's selected model
        )
        gen_create_time = (time.time() - gen_create_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        logger.info(
            f"⚡ Generate endpoint [{total_time:.0f}ms total] - "
            f"validation: {validation_time:.0f}ms, key_check: {key_check_time:.0f}ms, gen_create: {gen_create_time:.0f}ms | "
            f"user: {user_id[:8]}..., key_source: {key_source}, model: {selected_model}"
        )
        
        return GenerateResponse(
            generation_id=state.generation_id,
            chat_id=chat_id,
            status=state.status
        )
    
    except ValueError as e:
        # Concurrent generation error - convert to 409 Conflict
        error_msg = str(e)
        if "already in progress" in error_msg.lower():
            logger.warning(f"409 Conflict: {error_msg}")
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "GENERATION_IN_PROGRESS",
                    "message": error_msg
                }
            )
        else:
            # Other ValueError - treat as 400 Bad Request
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create generation: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "GENERATION_START_FAILED",
                "message": str(e)
            }
        )


# ============================================================================
# 🚀 SPECULATIVE START ENDPOINT - Ultra-Low TTFB (~50ms)
# ============================================================================
# This endpoint combines /generate + /stream into ONE SSE connection.
# Stream starts IMMEDIATELY with "thinking" state while validation runs async.
# Result: User sees response begin in <100ms instead of waiting 2-7 seconds.
# ============================================================================

@router.post("/chat/{chat_id}/stream-now")
async def speculative_stream(
    chat_id: str,
    request: GenerateRequest,
    user_id: str = Depends(get_user_id_string),
    redis_client = Depends(get_redis_client)
):
    """
    🚀 SPECULATIVE START: SSE stream begins IMMEDIATELY.
    
    Flow:
    1. INSTANTLY emit "thinking" event (TTFB < 50ms)
    2. ASYNC: Validate input + check API key + create generation
    3. If validation fails → emit "error" event + close
    4. If validation passes → stream tokens normally
    
    This endpoint is GPT-style: users see "thinking..." instantly,
    then tokens flow. Perceived latency approaches zero.
    """
    import time
    start_time = time.time()
    
    gen_manager = GenerationManager(redis_client)
    validator = default_validator
    
    async def speculative_event_generator():
        """SSE generator with speculative start"""
        generation_id = None
        state = None
        
        try:
            # ========================================
            # PHASE 1: INSTANT "THINKING" (< 50ms)
            # ========================================
            yield {
                "event": "thinking",
                "data": json.dumps({
                    "message": "Processing your request...",
                    "chat_id": chat_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            await asyncio.sleep(0)  # Yield to event loop to flush immediately
            
            thinking_time = (time.time() - start_time) * 1000
            logger.info(f"⚡ TTFB: {thinking_time:.0f}ms (thinking event sent)")
            
            # ========================================
            # PHASE 2: ASYNC VALIDATION (Background)
            # ========================================
            
            # 2a. Quick input validation (CPU-only, ~1ms)
            if not request.prompt or not request.prompt.strip():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "VALIDATION_ERROR",
                        "message": "Prompt cannot be empty"
                    })
                }
                return
            
            try:
                validation = validator.validate_or_raise(request.prompt)
                if validation.warnings:
                    logger.warning(f"Input warnings for user {user_id}: {validation.warnings}")
            except Exception as val_error:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "VALIDATION_ERROR",
                        "message": str(val_error)
                    })
                }
                return
            
            # 2b. API Key check (may hit cache or DB)
            user_api_key, key_source, error_code, selected_model = await get_api_key_for_user(user_id)
            
            if not user_api_key:
                if error_code == ErrorCodes.FREE_LIMIT_EXCEEDED:
                    message = "⚠️ Free limit reached. You've used all 10 free requests. Add your Groq API key to continue."
                elif error_code == ErrorCodes.ALL_KEYS_EXHAUSTED:
                    message = "🚫 All your API keys are temporarily exhausted. Limits reset daily."
                else:
                    message = "Unable to process request. Please try again later."
                
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": error_code or "FREE_LIMIT_EXCEEDED",
                        "message": message,
                        "requires_action": "add_api_key" if error_code == ErrorCodes.FREE_LIMIT_EXCEEDED else None
                    })
                }
                return
            
            # 2c. Get key_id if using user's key
            key_id = None
            if key_source == "user":
                key_id = await get_current_key_id_for_user(user_id)
            
            # 2d. Create generation record
            try:
                state = await gen_manager.create_generation(
                    chat_id=chat_id,
                    user_id=user_id,
                    prompt=request.prompt,
                    key_source=key_source,
                    api_key=user_api_key,
                    key_id=key_id,
                    model=selected_model or "llama-3.1-8b-instant"
                )
                generation_id = state.generation_id
            except ValueError as e:
                error_msg = str(e)
                if "already in progress" in error_msg.lower():
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "GENERATION_IN_PROGRESS",
                            "message": error_msg
                        })
                    }
                elif "wait a moment" in error_msg.lower():
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "RATE_LIMITED",
                            "message": error_msg
                        })
                    }
                else:
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "GENERATION_FAILED",
                            "message": error_msg
                        })
                    }
                return
            
            validation_complete_time = (time.time() - start_time) * 1000
            logger.info(
                f"⚡ Speculative validation complete [{validation_complete_time:.0f}ms] | "
                f"gen_id: {generation_id[:8]}..., key_source: {key_source}"
            )
            
            # ========================================
            # PHASE 3: EMIT READY + START STREAMING
            # ========================================
            yield {
                "event": "ready",
                "data": json.dumps({
                    "generation_id": generation_id,
                    "chat_id": chat_id,
                    "model": selected_model or "llama-3.1-8b-instant",
                    "key_source": key_source
                })
            }
            
            # 🚀 BURST + FLUSH STRATEGY for speculative streaming
            chunk_count = 0
            sse_buffer = ""
            sse_token_count = 0
            last_sse_flush = time.time()
            is_first_sse = True
            
            # Burst config (generator already batches ~30 tokens)
            SSE_BURST_TOKENS = 1    # SSE flushes per generator batch
            SSE_BURST_TIME = 0.03   # 30ms max delay
            
            # 🛡️ Metadata filtering state
            partial_tag_buffer = ""
            
            def clean_for_sse(text: str) -> str:
                """Final safety filter before SSE transmission"""
                nonlocal partial_tag_buffer
                combined = partial_tag_buffer + text
                partial_tag_buffer = ""
                clean = METADATA_PATTERN.sub('', combined)
                partial_match = re.search(r'<!--[^>]*$', clean)
                if partial_match:
                    partial_tag_buffer = partial_match.group(0)
                    clean = clean[:partial_match.start()]
                return clean
            
            async for chunk_text in generate_ai_stream(
                state.prompt,
                generation_id,
                gen_manager,
                state.user_id,
                state.chat_id,
                api_key=state.api_key,
                key_source=state.key_source,
                model=state.model_used or "llama-3.1-8b-instant"
            ):
                clean_chunk = clean_for_sse(chunk_text)
                if not clean_chunk:
                    continue
                
                chunk_count += 1
                sse_buffer += clean_chunk
                sse_token_count += 1
                
                # Check cancellation periodically
                if chunk_count % 100 == 0:
                    if await gen_manager.is_cancelled(generation_id):
                        await gen_manager.update_status(generation_id, "cancelled")
                        yield {
                            "event": "cancelled",
                            "data": json.dumps({"message": "Generation cancelled", "generation_id": generation_id})
                        }
                        return
                
                # 🚀 BURST + FLUSH STRATEGY
                now = time.time()
                time_since_flush = now - last_sse_flush
                should_flush = (
                    is_first_sse or
                    sse_token_count >= SSE_BURST_TOKENS or
                    time_since_flush >= SSE_BURST_TIME or
                    '\n' in sse_buffer
                )
                
                if should_flush and sse_buffer:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": sse_buffer})
                    }
                    sse_buffer = ""
                    sse_token_count = 0
                    last_sse_flush = now
                    is_first_sse = False
                    await asyncio.sleep(0)
            
            # Flush remaining buffer
            final_content = sse_buffer + partial_tag_buffer
            if final_content:
                final_clean = METADATA_PATTERN.sub('', final_content)
                if final_clean:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": final_clean})
                    }
            
            # ========================================
            # PHASE 4: COMPLETION
            # ========================================
            if generation_id and not await gen_manager.is_cancelled(generation_id):
                await gen_manager.update_status(generation_id, "completed")
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "message": "Generation completed",
                        "generation_id": generation_id,
                        "total_time_ms": int((time.time() - start_time) * 1000)
                    })
                }
        
        except asyncio.CancelledError:
            logger.info(f"Speculative stream cancelled (client disconnect) | gen_id: {generation_id}")
            if generation_id:
                try:
                    await gen_manager.update_status(generation_id, "cancelled")
                except Exception:
                    pass
            raise
        
        except Exception as e:
            logger.error(f"Speculative stream error: {e}", exc_info=True)
            if generation_id:
                try:
                    await gen_manager.update_status(generation_id, "failed")
                except Exception:
                    pass
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "STREAM_ERROR",
                    "message": str(e)
                })
            }
    
    return EventSourceResponse(speculative_event_generator())


async def generate_ai_stream(
    prompt: str,
    gen_id: str,
    gen_manager: GenerationManager,
    user_id: str,
    chat_id: str,
    api_key: str | None = None,  # 🔑 User's API key
    key_source: str = "platform",  # 🔑 "platform" or "user"
    model: str = "llama-3.1-8b-instant"  # 🎯 User's selected model
) -> AsyncGenerator[str, None]:
    """
    Generate AI response stream using Main Brain.
    
    🚀 ULTRA-OPTIMIZED V7 - BURST + FLUSH STRATEGY:
    - Batch tokens: flush every 30 tokens OR 50ms (whichever first)
    - First token always immediate (end "thinking" state ASAP)
    - Smoother text flow, lower CPU + socket overhead
    - Fire-and-forget background saves
    - 🛡️ METADATA FILTERING: Never send internal data to UI
    """
    import time
    
    # Update status to streaming
    asyncio.create_task(gen_manager.update_status(gen_id, "streaming"))  # 🚀 Fire-and-forget
    
    logger.debug(f"🔑 Gen {gen_id[:8]}... key_source: {key_source}")
    
    # 🚀 BURST + FLUSH CONFIG
    BURST_TOKEN_THRESHOLD = 30   # Flush after this many tokens
    BURST_TIME_THRESHOLD = 0.05  # Flush after 50ms max
    CANCEL_CHECK_INTERVAL = 500  # Check cancellation every N tokens
    PERSIST_CHAR_THRESHOLD = 2000  # Persist to Redis every N chars
    PERSIST_TIME_THRESHOLD = 15.0  # Or every N seconds
    
    # State tracking
    token_buffer = ""           # Buffer for burst batching
    token_count = 0             # Tokens in current burst
    total_tokens = 0            # Total tokens streamed
    last_flush_time = time.time()
    is_first_token = True       # First token = immediate flush
    
    # Persistence buffer (separate from streaming buffer)
    persist_buffer = ""
    persist_char_count = 0
    last_persist_time = time.time()
    
    # 🛡️ Metadata filtering state
    metadata_buffer = ""  # Buffer for partial metadata tags
    stored_metadata = ""  # Store metadata for finalization
    
    def filter_and_extract_metadata(text: str) -> str:
        """Filter metadata from streaming text, store it separately"""
        nonlocal metadata_buffer, stored_metadata
        
        # Combine with any partial tag from previous chunk
        combined = metadata_buffer + text
        metadata_buffer = ""
        
        # Extract and store any complete metadata tags
        matches = METADATA_PATTERN.findall(combined)
        for match in matches:
            stored_metadata += match
        
        # Remove complete metadata from output
        clean = METADATA_PATTERN.sub('', combined)
        
        # Check for partial opening tag at end
        partial_match = re.search(r'<!--[^>]*$', clean)
        if partial_match:
            metadata_buffer = partial_match.group(0)
            clean = clean[:partial_match.start()]
        
        return clean
    
    try:
        async for token in generate_response_stream(
            user_id=user_id,
            message=prompt,
            session_id=chat_id,
            api_key=api_key,
            key_source=key_source,
            model=model  # 🎯 Pass user's selected model
        ):
            # 🚀 Skip empty tokens immediately
            if not token:
                continue
            
            # 🛡️ CRITICAL: Filter metadata BEFORE yielding
            clean_token = filter_and_extract_metadata(str(token))
            
            # Skip if nothing after filtering
            if not clean_token:
                continue
            
            # Accumulate in burst buffer
            token_buffer += clean_token
            token_count += 1
            total_tokens += 1
            
            # Also accumulate for persistence
            persist_buffer += clean_token
            persist_char_count += len(clean_token)
            
            # 🚀 BURST + FLUSH LOGIC
            now = time.time()
            time_since_flush = now - last_flush_time
            
            should_flush = (
                is_first_token or                          # Always flush first token immediately
                token_count >= BURST_TOKEN_THRESHOLD or    # 30 tokens = flush
                time_since_flush >= BURST_TIME_THRESHOLD or # 50ms = flush
                '\n' in token_buffer                       # Newline = flush (preserves formatting)
            )
            
            if should_flush and token_buffer:
                yield token_buffer
                token_buffer = ""
                token_count = 0
                last_flush_time = now
                is_first_token = False
                await asyncio.sleep(0)  # Yield to event loop
            
            # 🚀 Check cancellation periodically (not every token)
            if total_tokens % CANCEL_CHECK_INTERVAL == 0:
                if await gen_manager.is_cancelled(gen_id):
                    logger.info(f"Generation {gen_id} cancelled")
                    return
            
            # 🚀 Persist to Redis periodically (fire-and-forget)
            if persist_char_count >= PERSIST_CHAR_THRESHOLD or (now - last_persist_time) > PERSIST_TIME_THRESHOLD:
                asyncio.create_task(gen_manager.increment_chunks(gen_id, persist_char_count))
                asyncio.create_task(gen_manager.append_content(gen_id, persist_buffer))
                persist_buffer = ""
                persist_char_count = 0
                last_persist_time = now
        
        # 🚀 Final burst flush (any remaining tokens)
        if token_buffer:
            yield token_buffer
        
    except Exception as stream_error:
        # 🛡️ Graceful Degradation
        error_msg = str(stream_error).lower()
        is_rate_limit = "429" in error_msg or "resource exhausted" in error_msg or "quota" in error_msg
        
        # Flush any buffered content before error message
        if token_buffer:
            yield token_buffer
        
        if total_tokens > 0:
            logger.warning(f"⚠️ Stream interrupted for {gen_id}: {type(stream_error).__name__}")
            
            if is_rate_limit:
                yield "\n\n(High traffic - please try again)"
            else:
                yield "\n\n(Connection hiccup - let's try again)"
            return
        else:
            logger.error(f"❌ Generation failed for {gen_id}: {stream_error}")
            raise stream_error

    finally:
        # Final persistence flush (fire-and-forget)
        if persist_char_count > 0:
            asyncio.create_task(gen_manager.increment_chunks(gen_id, persist_char_count))
            asyncio.create_task(gen_manager.append_content(gen_id, persist_buffer))


@router.get("/chat/{chat_id}/stream/{generation_id}")
async def stream_response(
    chat_id: str,
    generation_id: str,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager)
):
    """
    SSE endpoint for streaming AI responses.
    Supports reconnection and resume.
    """
    # Get generation state
    state = await gen_manager.get_generation(generation_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Verify ownership
    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify chat_id matches
    if state.chat_id != chat_id:
        raise HTTPException(status_code=400, detail="Chat ID mismatch")
    
    async def event_generator():
        """SSE event generator"""
        import time
        try:
            # If already completed/cancelled, send final event
            if state.status in ["completed", "cancelled", "failed"]:
                yield {
                    "event": state.status,
                    "data": json.dumps({
                        "message": f"Generation {state.status}",
                        "generation_id": generation_id
                    })
                }
                return
            
            # Start/resume streaming
            logger.info(f"Starting stream for generation {generation_id}, key_source: {state.key_source}")
            
            # 🚀 BURST + FLUSH STRATEGY V2 for SSE layer
            # Note: generate_ai_stream already batches, but we add SSE-level smoothing
            gen_id_str = generation_id
            chunk_count = 0
            sse_buffer = ""
            sse_token_count = 0
            last_sse_flush = time.time()
            is_first_sse = True
            
            # Burst config for SSE layer (can be different from generator layer)
            SSE_BURST_TOKENS = 1     # Since generator already batches, SSE can flush more often
            SSE_BURST_TIME = 0.03    # 30ms for ultra-smooth feel
            
            # 🛡️ SSE layer metadata filter state
            partial_tag_buffer = ""
            
            def clean_for_sse(text: str) -> str:
                """Final safety filter before SSE transmission"""
                nonlocal partial_tag_buffer
                combined = partial_tag_buffer + text
                partial_tag_buffer = ""
                
                # Remove complete metadata using shared pattern
                clean = METADATA_PATTERN.sub('', combined)
                
                # Buffer partial tags
                partial_match = re.search(r'<!--[^>]*$', clean)
                if partial_match:
                    partial_tag_buffer = partial_match.group(0)
                    clean = clean[:partial_match.start()]
                
                return clean
            
            async for chunk_text in generate_ai_stream(
                state.prompt, 
                generation_id, 
                gen_manager, 
                state.user_id, 
                state.chat_id,
                api_key=state.api_key,
                key_source=state.key_source,
                model=state.model_used or "llama-3.1-8b-instant"
            ):
                # 🛡️ Apply final safety filter
                clean_chunk = clean_for_sse(chunk_text)
                if not clean_chunk:
                    continue
                    
                chunk_count += 1
                sse_buffer += clean_chunk
                sse_token_count += 1
                
                # 🚀 Check cancellation every 100 chunks
                if chunk_count % 100 == 0:
                    if await gen_manager.is_cancelled(generation_id):
                        await gen_manager.update_status(generation_id, "cancelled")
                        yield {
                            "event": "cancelled",
                            "data": json.dumps({
                                "message": "Generation cancelled",
                                "generation_id": gen_id_str
                            })
                        }
                        return
                
                # 🚀 BURST + FLUSH STRATEGY V2:
                # Generator already batches ~30 tokens, SSE layer just smooths delivery
                now = time.time()
                time_since_flush = now - last_sse_flush
                
                should_flush_sse = (
                    is_first_sse or                           # First = immediate
                    sse_token_count >= SSE_BURST_TOKENS or    # Token threshold
                    time_since_flush >= SSE_BURST_TIME or     # Time threshold (30ms)
                    '\n' in sse_buffer                        # Newline = flush
                )
                
                if should_flush_sse and sse_buffer:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": sse_buffer})
                    }
                    sse_buffer = ""
                    sse_token_count = 0
                    last_sse_flush = now
                    is_first_sse = False
                    await asyncio.sleep(0)  # Yield to event loop
            
            # Flush any remaining SSE buffer (WITH FILTERING!)
            # Also flush any partial tag that was buffered
            final_content = sse_buffer + partial_tag_buffer
            if final_content:
                # 🛡️ CRITICAL: Final filter pass to catch any trailing metadata
                final_clean = METADATA_PATTERN.sub('', final_content)
                if final_clean:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": final_clean})
                    }
            
            # Completed successfully
            if not await gen_manager.is_cancelled(generation_id):
                await gen_manager.update_status(generation_id, "completed")
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "message": "Generation completed",
                        "generation_id": generation_id
                    })
                }
        
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for generation {generation_id} (Client Disconnect)")
            # CRITICAL: Clean up backend state on client disconnect
            try:
                await gen_manager.update_status(generation_id, "cancelled")
            except Exception as e:
                logger.error(f"Failed to update status on cancel: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Stream error for generation {generation_id}: {e}", exc_info=True)
            try:
                await gen_manager.update_status(generation_id, "failed")
            except Exception as update_error:
                logger.error(f"Failed to update status on error: {update_error}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "generation_id": generation_id
                })
            }
            
        finally:
            # SAFETY NET: Always ensure lock is released when stream ends for any reason
            # This prevents 409 Conflict loops if update_status wasn't called
            try:
                await gen_manager.release_chat_lock(chat_id)
            except Exception as lock_error:
                logger.error(f"Failed to release chat lock in finally block: {lock_error}")
    
    # 🚀 ULTRA-FAST SSE: Disable ping interval, set no-cache headers
    return EventSourceResponse(
        event_generator(),
        ping=0,  # Disable ping to reduce overhead
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        }
    )


@router.delete("/chat/{chat_id}/cancel/{generation_id}")
async def cancel_generation(
    chat_id: str,
    generation_id: str,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager)
):
    """
    Cancel an active generation.
    Immediately stops streaming and returns control.
    """
    success = await gen_manager.request_cancellation(generation_id, user_id)
    
    if not success:
        state = await gen_manager.get_generation(generation_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Generation not found")
        
        if state.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
    
    logger.info(f"Cancellation requested for generation {generation_id}")
    
    return {
        "status": "cancellation_requested",
        "generation_id": generation_id
    }


@router.get("/chat/{chat_id}/status/{generation_id}")
async def get_generation_status(
    chat_id: str,
    generation_id: str,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager)
):
    """
    Get current status of a generation.
    Used for refresh recovery.
    """
    state = await gen_manager.get_generation(generation_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Verify ownership
    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return {
        "generation_id": state.generation_id,
        "chat_id": state.chat_id,
        "status": state.status,
        "chunks_sent": state.chunks_sent,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "cancellation_requested": state.cancellation_requested
    }





@router.get("/chat/{chat_id}/active")
async def get_active_generation(
    chat_id: str,
    user_id: str = Depends(get_user_id_string),
    gen_manager: GenerationManager = Depends(get_generation_manager)
):
    """
    Get currently active generation for a chat.
    Used for refresh recovery.
    """
    state = await gen_manager.get_active_generation_for_chat(chat_id)
    
    if not state:
        return {"active_generation": None}
    
    # Verify ownership
    if state.user_id != user_id:
        return {"active_generation": None}
    
    return {
        "active_generation": {
            "generation_id": state.generation_id,
            "status": state.status,
            "created_at": state.created_at,
            "chunks_sent": state.chunks_sent
        }
    }


# ============================================================================
# 🎚️ ADAPTIVE QUALITY ENDPOINTS
# ============================================================================

@router.get("/quality/status")
async def get_adaptive_quality_status():
    """
    Get current adaptive quality status and metrics.
    
    Returns:
        - load_score: 0.0 (idle) to 1.0+ (overloaded)
        - recommended_quality: premium/standard/fast/turbo
        - metrics: active generations, latency, error rate
        - presets: available quality presets with their parameters
    """
    if not ADAPTIVE_QUALITY_AVAILABLE:
        return {
            "enabled": False,
            "message": "Adaptive quality service not available"
        }
    
    status = adaptive_quality.get_status()
    status["enabled"] = True
    return status


@router.post("/quality/report-slow-client")
async def report_slow_client(
    user_id: str = Depends(get_user_id_string)
):
    """
    Report that the current client is experiencing slow reads.
    This triggers quality degradation for smoother streaming.
    
    Called by frontend when it detects:
    - High buffer latency
    - Dropped frames
    - Network congestion
    """
    if not ADAPTIVE_QUALITY_AVAILABLE:
        return {"status": "not_available"}
    
    await adaptive_quality.record_slow_client(user_id)
    preset = adaptive_quality.get_recommended_preset(user_id)
    
    logger.info(f"🐢 Slow client reported: {user_id[:8]}... → quality={preset.name}")
    
    return {
        "status": "recorded",
        "recommended_quality": preset.name,
        "params": preset.to_dict()
    }


@router.post("/quality/report-recovered")
async def report_client_recovered(
    user_id: str = Depends(get_user_id_string)
):
    """
    Report that the client has recovered from slow state.
    This allows quality to be restored.
    """
    if not ADAPTIVE_QUALITY_AVAILABLE:
        return {"status": "not_available"}
    
    await adaptive_quality.record_client_recovered(user_id)
    preset = adaptive_quality.get_recommended_preset(user_id)
    
    logger.info(f"✅ Client recovered: {user_id[:8]}... → quality={preset.name}")
    
    return {
        "status": "recorded",
        "recommended_quality": preset.name,
        "params": preset.to_dict()
    }
