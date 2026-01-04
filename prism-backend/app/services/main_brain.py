
"""
🧠 MAIN AGENT - CORE BRAIN IMPLEMENTATION (BEHAVIOR ENGINE V2)

This is the Main Agent - the core intelligence of the personal AI assistant.
Refactored to use DYNAMIC BEHAVIOR ENGINE (No fixed roles).

Key Features:
- Behavioral Signal Extraction (Formality, Emotion, Style)
- Dynamic System Prompt Construction
- Holographic Memory Integration
- "Thinking" Transparency
- Response Quality Checks
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pytz
import logging
import asyncio

from app.utils.llm_client import get_llm_response
from app.db.redis_client import add_message_to_history, get_recent_history, redis_client
from app.services.memory_manager import retrieve_long_term_memory, save_long_term_memory
from app.services.graph_service import save_knowledge, retrieve_knowledge
from app.db.mongo_client import db

# 🧠 Import Unified Memory Orchestrator & Behavior Engine
from app.services.unified_memory_orchestrator import (
    unified_memory_orchestrator,
    MemoryType
)
from app.services.behavior_engine import behavior_engine

logger = logging.getLogger(__name__)

# Mongo collection for mood history
mood_collection = db.mood_history


def _assess_quality(response: str, behavior_profile: Any) -> tuple[float, str]:
    """
    Heuristic quality check for response.
    Returns: (score, feedback_reason)
    """
    if not response or len(response.strip()) < 3:
        return 0.0, "empty response"
        
    # Heuristic 1: Length check (avoid one-word answers unless requested)
    if len(response.split()) < 3:
        return 0.4, "too short"

    # Heuristic 2: Robotic check if high warmth
    if behavior_profile.warmth > 0.7:
        if "as an ai" in response.lower() or "language model" in response.lower():
            return 0.5, "too robotic for high warmth profile"

    return 1.0, "ok"

# MainBrain class wrapper for generate_response
class MainBrain:
    async def generate_response(self, user_message: str, context: str = "", user_preferences: dict = None, search_results: str = None, image_url: str = None, user_id: str = None, session_id: str = None):
        if user_id is None:
            user_id = "unknown"
        return await generate_response(
            user_id=user_id,
            message=user_message,
            search_results=search_results,
            image_url=image_url,
            session_id=session_id
        )


def get_current_time_str() -> str:
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    return now.strftime("%A, %I:%M %p")


async def generate_response(
        user_id: str,
        message: str,
        search_results: Optional[str] = None,
        image_url: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
    """
    🧠 PROCESSED PIPELINE (STRICT):
    1. User Input
    2. Behavior Signal Extraction
    3. Emotion & Tone Analysis
    4. Dynamic Behavior Definition
    5. Temporary Master Prompt Builder
    6. Memory Lookup (ONLY if needed)
    7. Response Generation
    8. Response Quality Check (implied by LLM instructions)
    """
    logger.info(f"[MainBrain] HIT generate_response for user_id={user_id}")
    
    # 0) Database-first safety
    from app.services.cleanup_service import verify_user_exists_in_mongodb
    user_profile = await verify_user_exists_in_mongodb(user_id)
    if not user_profile:
        print(f"⛔ User {user_id} not found in MongoDB - stopping memory load")
        return "I don't have any information about you yet. Please make sure you're properly logged in or create an account first."

    # 1️⃣ BEHAVIOR & EMOTION EXTRACTION
    signals = behavior_engine.extract_behavior_signals(message)
    emotion = behavior_engine.detect_emotion(message)
    behavior_profile = behavior_engine.build_behavior_profile(signals, emotion)
    
    logger.info(f"🎭 [Behavior] Profile: {behavior_profile}")

    # 2️⃣ INTENT & MEMORY FETCH
    # Classify intent for memory purposes
    lower_msg = (message or "").lower()
    if any(k in lower_msg for k in ["remind", "schedule", "task", "todo"]):
        intent = "task"
    elif "my name" in lower_msg or "who am i" in lower_msg:
        intent = "identity"
    elif any(k in lower_msg for k in ["recall", "remember", "what did we discuss", "earlier"]):
        intent = "history"
    elif "like" in lower_msg or "love" in lower_msg or "prefer" in lower_msg:
        intent = "preferences"
    else:
        intent = "general"

    # Fetch Memory (Holographic)
    holographic_context, debug_logs = await unified_memory_orchestrator.get_holographic_context(
        user_id=user_id,
        query=message,
        intent=intent
    )
    
    # Enrich Prompt (Get the memory block string)
    memory_section, enrichment_logs = unified_memory_orchestrator.enrich_master_prompt(
        base_prompt="", 
        context=holographic_context,
        debug_logs=[]
    )
    
    # 3️⃣ DYNAMIC SYSTEM PROMPT CONSTRUCTION
    core_identity = """
### CORE IDENTITY
You are Prism, an advanced, empathetic AI. 
You do not have a fixed personality; you flow like water to match the user's needs.
Your baseline is: Sweet, Polite, Warm, and Solution-Oriented.
"""
    system_prompt = await behavior_engine.build_dynamic_prompt_async(
        core_identity=core_identity,
        behavior_profile=behavior_profile,
        memory_context=memory_section,
        user_id=user_id  # 🆕 Pass user_id for interaction anchor lookup
    )
    
    # Append Search Results if any
    if search_results:
        system_prompt += f"\n\n### WEB RESEARCH\n{search_results}\n"

    # Log transparency
    logger.info(f"[MainBrain] System Prompt Length: {len(system_prompt)}")
    
    # 4️⃣ LLM GENERATION & QUALITY CHECK
    response = ""
    max_retries = 1
    
    for attempt in range(max_retries + 1):
        response = await get_llm_response(
            prompt=message,
            system_prompt=system_prompt,
            image_url=image_url,
        )
        
        # Quality Check
        quality_score, feedback = _assess_quality(response, behavior_profile)
        if quality_score >= 0.7:
            break
            
        if attempt < max_retries:
            logger.warning(f"⚠️ Response Quality Check Failed ({quality_score}): {feedback}. Regenerating...")
            system_prompt += f"\n\n[SYSTEM INSTRUCTION]: Previous draft was {feedback}. Please adjust tone and content."
    
    # 5️⃣ MEMORY STORAGE (Keep existing logic but routed via orchestrator)
    # Check for core facts to store
    # This logic is kept from original but ensures we use the orchestrator
    lowered = message.lower()
    
    # Preference Storage
    if any(k in lowered for k in ["i like", "i love", "my favorite", "i prefer"]):
         # We'll use a simplified extraction for now or rely on an async task if we had one.
         # For reliability, we trigger the orchestrator's semantic storage
         await unified_memory_orchestrator.store_memory(
             user_id=user_id,
             memory_content=message,
             memory_type=MemoryType.SEMANTIC, # Store full sentence relative to preference
             metadata={"type": "potential_preference"}
         )

    # 6️⃣ THINKING SUMMARY (Append to response or log)
    # The requirement is "Thinking Transparency" exposed to backend/frontend.
    # We will append a hidden JSON block or specific delimiter for Frontend to parse if needed.
    
    # Generate Contextual Suggestions based on Intent
    suggestions = []
    if intent == "task":
        suggestions = ["Change the time", "Cancel this task", "Show my tasks"]
    elif intent == "identity":
        suggestions = ["What can you do?", "Change your personality", "Tell me a secret"]
    elif intent == "history":
        suggestions = ["Summarize our chats", "What did I ask previously?", "Clear my memory"]
    elif intent == "preferences":
        suggestions = ["What else do you know about me?", "Forget that preference", "Save this"]
    else:
        # Generic interesting follow-ups
        suggestions = ["Tell me more", "Give me an example", "Why is that?"]

    # Construct thinking summary
    thinking_summary = {
        "intent": intent,
        "emotion": emotion,
        "behavior_profile": {
            "tone": behavior_profile.tone,
            "warmth": behavior_profile.warmth
        },
        "pipeline": ["analyzed_signals", "fetched_memory", "generated_response"],
        "suggestions": suggestions
    }
    
    # We typically don't append JSON to the visible text unless the frontend is ready.
    # The user said: "Frontend... Collapsible dropdown... Label: 'How I understood & responded'"
    # This implies we might need to send structured data.
    # However, `generate_response` returns `str`. 
    # I will append it as a specially delimiter block.
    
    import json
    thinking_json = json.dumps(thinking_summary)
    response_with_thinking = f"{response}\n\n<!--THINKING_DATA:{thinking_json}-->"
    
    return response_with_thinking

