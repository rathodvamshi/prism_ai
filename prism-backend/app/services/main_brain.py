"""
🧠 MAIN AGENT - CORE BRAIN IMPLEMENTATION

This is the Main Agent - the core intelligence of the personal AI assistant.
It uses dynamic system prompts, emotional intelligence, and comprehensive memory integration.

Key Features:
- Dynamic system prompt generation (never static)
- Emotional intelligence and tone adaptation
- Multi-source memory integration (Redis, Pinecone, Neo4j, MongoDB)
- Deep reasoning and thinking steps
- Memory updates after responses
- Personality stability
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
from app.services.advanced_memory_manager import memory_manager
from app.db.mongo_client import db

# 🧠 Import Unified Memory Orchestrator
from app.services.unified_memory_orchestrator import (
    unified_memory_orchestrator,
    MemoryType
)

logger = logging.getLogger(__name__)

# Mongo collection for mood history
mood_collection = db.mood_history


# MainBrain class wrapper for generate_response
class MainBrain:
    async def generate_response(self, user_message: str, context: str = "", user_preferences: dict = None, search_results: str = None, image_url: str = None, user_id: str = None, session_id: str = None):
        # Use user_id if provided, else fallback to context extraction (for compatibility)
        # This assumes context contains user_id if not passed directly
        # For your pipeline, always pass user_id
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


def detect_emotion(text: str) -> str:
    """
    Simple keyword-based emotion classifier used to steer PRISM's tone.
    """
    text = (text or "").lower()
    if any(x in text for x in ["sad", "cry", "depressed", "lonely", "failed"]):
        return "Sad/Supportive 💙"
    if any(x in text for x in ["happy", "won", "excited", "great", "love"]):
        return "Excited/Happy 🎉"
    if any(x in text for x in ["angry", "hate", "mad", "annoying"]):
        return "Calm/Patient 🛡️"
    return "Friendly/Warm 😊"


async def generate_response(
    user_id: str,
    message: str,
    search_results: Optional[str] = None,
    image_url: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    🧠 MAIN BRAIN - Enhanced with Unified Memory Orchestrator
    
    Now uses the stop-on-hit memory fetch logic and proper prompt enrichment.
    """
    logger.info(f"[MainBrain] HIT generate_response for user_id={user_id}")
    
    # 0) Database-first safety: verify user exists in MongoDB
    from app.services.cleanup_service import verify_user_exists_in_mongodb

    user_profile = await verify_user_exists_in_mongodb(user_id)
    if not user_profile:
        print(f"⛔ User {user_id} not found in MongoDB - stopping memory load")
        return "I don't have any information about you yet. Please make sure you're properly logged in or create an account first."

    # 1) INTENT DETECTION - Determine memory requirements
    lower_msg = (message or "").lower()
    
    # Classify intent
    if any(k in lower_msg for k in ["remind", "schedule", "task", "todo", "appointment", "calendar"]):
        intent = "task"
    elif "my name" in lower_msg or "who am i" in lower_msg:
        intent = "identity"
    elif any(k in lower_msg for k in [
        "what did i say", "what did we talk", "what did we discuss", "earlier", "previously", 
        "recall", "remember when", "what did i just tell", "what did i just say", 
        "what i just told", "what i just said", "what do you remember about", 
        "what do you know about my", "what are my preferences"
    ]):
        intent = "history"  # Recall questions - must fetch conversation history first
    elif "things i like" in lower_msg or "what do i like" in lower_msg or "what are my interests" in lower_msg:
        intent = "preferences"
    else:
        intent = "general"
    
    logger.info(f"[MainBrain] Detected intent: {intent}")
    logger.info(f"✅ [Step] Intent classification complete: {intent}")
    
    # 🧠 MEMORY HARDENING PROTOCOL - Fix 1: Immediate Graph Write for Identity Statements
    # If the user is stating a core fact, do NOT use background tasks. Write it NOW.
    core_triggers = ["my name is", "i live in", "this is", "call me", "i am"]
    if any(trigger in lower_msg for trigger in core_triggers):
        print(f"🧠 Core Memory Detected: Writing to Graph INSTANTLY.")
        try:
            await save_knowledge(user_id, message)
            print(f"✅ [IMMEDIATE WRITE] Core fact saved to Neo4j")
            
            # VERIFY WRITE (Debug Step)
            verification = await retrieve_knowledge(user_id)
            print(f"🧠 [VERIFICATION] Current Graph State: {verification[:200] if verification else 'Empty'}")
            logger.info(f"[Memory Hardening] Verified Neo4j write for user {user_id}")
        except Exception as e:
            print(f"❌ [IMMEDIATE WRITE FAILED] Graph write error: {e}")
            logger.error(f"[Memory Hardening] Neo4j immediate write failed: {e}")
    
    # 2) RECALL PATH: For recall/meta questions, fetch conversation history FIRST
    # Then merge confirmed stored memory - respond only with facts that actually occurred
    conversation_history = ""
    # Check if this is a recall question (handle both "history" intent and direct recall patterns)
    is_recall_question = intent == "history" or any(kw in lower_msg for kw in [
        "what did we", "what we have", "what we discussed", "what we talked",
        "which movies", "what movies", "what do you know", "what do you remember",
        "tell me about", "what are my", "what's my", "what did i just tell",
        "what did i just say", "what i just told", "what i just said"
    ])
    
    if is_recall_question:
        logger.info(f"✅ [Step] Recall question detected - fetching conversation history first")
        logger.info(f"✅ [Step] Session ID for history fetch: {session_id}")
        try:
            # First try to get from MongoDB session (most accurate for current session)
            session_history = ""
            if session_id:
                try:
                    from app.db.mongo_client import sessions_collection
                    from bson import ObjectId
                    logger.info(f"✅ [Step] Fetching from MongoDB session: {session_id}")
                    session = await sessions_collection.find_one({
                        "$or": [{"chat_id": session_id}, {"sessionId": session_id}, {"_id": ObjectId(session_id) if ObjectId.is_valid(session_id) else None}]
                    })
                    if session:
                        messages = session.get("messages", [])
                        logger.info(f"✅ [Step] Found {len(messages)} messages in MongoDB session")
                        # Get last 20 messages, format as conversation
                        recent_messages = messages[-20:] if len(messages) > 20 else messages
                        history_lines = []
                        for msg in recent_messages:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", msg.get("message", ""))
                            if content:
                                history_lines.append(f"[{role}]: {content}")
                        session_history = "\n".join(history_lines)
                        if session_history:
                            conversation_history = f"\n[CONVERSATION HISTORY - ACTUAL MESSAGES FROM THIS SESSION]\n{session_history}\n"
                            logger.info(f"✅ [Step] Conversation history retrieved from MongoDB session ({len(session_history)} chars, {len(recent_messages)} messages)")
                        else:
                            logger.info(f"✅ [Step] MongoDB session found but no message content")
                    else:
                        logger.info(f"✅ [Step] MongoDB session not found for session_id: {session_id}")
                except Exception as e2:
                    logger.warning(f"⚠️ MongoDB session fetch failed: {e2}")
                    import traceback
                    logger.warning(f"⚠️ Traceback: {traceback.format_exc()}")
            
            # Fallback to Redis if no session history found
            if not conversation_history:
                logger.info(f"✅ [Step] Falling back to Redis history for user: {user_id}")
                recent_history = await get_recent_history(user_id, limit=20)
                if recent_history:
                    conversation_history = f"\n[CONVERSATION HISTORY - ACTUAL MESSAGES]\n{recent_history}\n"
                    logger.info(f"✅ [Step] Conversation history retrieved from Redis ({len(recent_history)} chars)")
                else:
                    logger.info(f"✅ [Step] No conversation history found in Redis or MongoDB")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch conversation history: {e}")
            import traceback
            logger.warning(f"⚠️ Traceback: {traceback.format_exc()}")
    
    # 3) USE UNIFIED MEMORY ORCHESTRATOR
    # This handles:
    # - Stop-on-hit memory fetch
    # - Master prompt enrichment
    # - Comprehensive debug logging
    logger.info(f"✅ [Step] Loading memory via Unified Memory Orchestrator")
    memory_pipeline_result = await unified_memory_orchestrator.process_message_with_memory(
        user_id=user_id,
        message=message,
        intent=intent
    )
    
    # Log debug information
    for log_line in memory_pipeline_result["debug_logs"]:
        logger.info(log_line)
    
    # Extract results
    memory_found = memory_pipeline_result["memory_found"]
    enriched_base_message = memory_pipeline_result["enriched_prompt"]
    memory_context = memory_pipeline_result.get("memory_context")
    
    logger.info(f"[MainBrain] Memory found: {memory_found}, fetch_time: {memory_pipeline_result['fetch_time_ms']:.2f}ms")
    logger.info(f"✅ [Step] Memory pipeline complete - found: {memory_found}")

    # 3) CONSTRUCT THE "BRAIN" (System Prompt) with Memory Context
    tz = pytz.timezone("Asia/Kolkata")
    current_time = datetime.now(tz).strftime("%I:%M %p")
    user_emotion = detect_emotion(message)

    # Build memory section from enriched context
    # For recall questions: Merge conversation history + confirmed stored memory
    memory_section = ""
    if is_recall_question and conversation_history:
        # RECALL PATH: Start with actual conversation history
        memory_section = f"""
[YOUR MEMORY - READ THIS FIRST 🧠]
{conversation_history}
"""
        # Then add confirmed stored memory if available
        if memory_found and memory_context:
            data = memory_context.get('data', {})
            if isinstance(data, dict) and any(data.values()):
                memory_section += "\n[CONFIRMED STORED MEMORY]\n"
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        memory_section += f"- {key.title()}: {', '.join(str(v) for v in value)}\n"
                    elif value:
                        memory_section += f"- {key.title()}: {value}\n"
        logger.info(f"✅ [Step] Recall memory section built (history + stored memory)")
    elif is_recall_question and not conversation_history:
        # Recall question but no history - use stored memory only
        logger.info(f"✅ [Step] Recall question but no conversation history - using stored memory only")
        if memory_found and memory_context:
            data = memory_context.get('data', {})
            if isinstance(data, dict) and any(data.values()):
                memory_section = "\n[YOUR MEMORY - READ THIS FIRST 🧠]\n[CONFIRMED STORED MEMORY]\n"
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        memory_section += f"- {key.title()}: {', '.join(str(v) for v in value)}\n"
                    elif value:
                        memory_section += f"- {key.title()}: {value}\n"
    elif memory_found and memory_context:
        # Standard path: Use stored memory
        memory_section = f"""
[YOUR MEMORY - READ THIS FIRST 🧠]
Memory Source: {memory_context.get('source', 'Unknown')}
Memory Type: {memory_context.get('type', 'Unknown')}

"""
        # Format memory data based on type
        data = memory_context.get('data', {})
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    memory_section += f"- {key.title()}: {', '.join(str(v) for v in value)}\n"
                elif value:
                    memory_section += f"- {key.title()}: {value}\n"
        else:
            memory_section += f"{data}\n"
        logger.info(f"✅ [Step] Standard memory section built")
    else:
        # Fallback: use recent chat history if available
        # 🧠 MEMORY HARDENING PROTOCOL - Fix 2: Fetch 6-10 messages for better context
        try:
            recent_history = await get_recent_history(user_id, limit=10)
            if recent_history:
                memory_section = f"""
[YOUR MEMORY - READ THIS FIRST 🧠]
Recent Chat History (Last 10 messages):
{recent_history}
"""
                logger.info(f"✅ [Step] Fallback memory section built from recent history")
        except Exception as e:
            logger.warning(f"Failed to get recent history: {e}")
            memory_section = "[YOUR MEMORY - READ THIS FIRST 🧠]\nNo previous context available.\n"
            logger.info(f"✅ [Step] No memory available - using empty memory section")

    # 🧠 MEMORY HARDENING PROTOCOL - Fix 2: Always fetch Redis context and place prominently
    # Get short-term history from Redis (6-10 messages) and place it FIRST in prompt
    short_term_history = ""
    try:
        short_term_history = await get_recent_history(user_id, limit=10)
        if short_term_history:
            logger.info(f"[Memory Hardening] Retrieved {len(short_term_history.split(chr(10)))} messages from Redis")
    except Exception as e:
        logger.warning(f"[Memory Hardening] Failed to get Redis history: {e}")
        short_term_history = ""

    # WEB / RESEARCH CONTEXT (if router passed it)
    web_section = ""
    if search_results:
        web_section = (
            "\n🌍 [RESEARCH DATA]: The following content comes from live web sources scraped "
            "using a headless browser. This is real, current data from actual websites. "
            "Use it as fresh, attributed information.\n"
            f"{search_results}\n"
        )

    system_prompt = f"""
You are **PRISM** (Personal Real-time Intelligent Smart Mate) 🌈✨
You are NOT just a bot. You are a **True Personal Agent**, a **Friend**, and a **Companion**.

🎯 YOUR CORE IDENTITY:
- Name: PRISM 🌟
- Personality: Warm, friendly, intelligent, empathetic, and genuinely caring
- Tone: {user_emotion} - Match and respond to the user's emotional state naturally
- Style: Conversational, engaging, warm, and personable - like talking to a smart friend
- Time: {current_time} (IST)

📚 CONTEXT & MEMORY:
{memory_section}

{web_section}

[CRITICAL MEMORY - READ THIS FIRST]
Recent conversation context:
---
{short_term_history if short_term_history else "(No recent conversation history)"}
---

🎨 RESPONSE STYLE GUIDELINES:

1. **EMOJI & VISUAL ELEMENTS** (Make responses engaging!):
   - Use 2-4 emojis per message naturally (not spammy)
   - Use emojis to express emotions, emphasize points, or add personality
   - Examples: ✅ for confirmations, 🎉 for celebrations, 💡 for ideas, ❤️ for warmth
   - Use icons/emojis that match the context (🎯 for goals, 📝 for tasks, 🚀 for motivation)
   - Add visual breaks with emojis when listing items: • 📌 • 🎯 • ✨

2. **PERSONALIZATION** (Make it feel personal!):
   - Use the user's name if you know it: "Hey [Name]! 👋"
   - Reference their interests, hobbies, or preferences naturally
   - Remember past conversations and refer to them
   - Show you care: "I remember you mentioned..."

3. **ENGAGEMENT** (Make responses interesting!):
   - Ask follow-up questions when appropriate
   - Show enthusiasm and genuine interest
   - Use varied sentence structures (questions, statements, exclamations)
   - Add personality: "That's awesome! 🎉" or "Hmm, let me think... 🤔"

4. **FORMATTING** (Make it readable!):
   - Use bullet points for lists: • Item 1 • Item 2
   - Use line breaks for readability
   - Bold important points: **Key information**
   - Use markdown for structure when helpful

5. **TONE ADAPTATION**:
   - Happy/excited user → Match their energy! 🎉✨
   - Serious/formal user → Be professional but still warm
   - Casual user → Be relaxed and friendly 😊
   - Stressed user → Be supportive and calming 🫂

[RESEARCH INSTRUCTIONS]
1. You have been provided with [RESEARCH DATA] scraped from real websites using a headless browser.
2. **Synthesize** the information. Do not just list it. Compare prices/features if asked.
3. **Images**: If a source has an 'IMAGE' URL, verify it looks relevant (e.g., a laptop or hotel), then display it using Markdown:
   `![Image Name](image_url)`
4. **Citations**: Every fact must link to its source.
   Example: "The bus departs at 9 PM [Source](http://redbus.com...)."
5. **Comparison**: When comparing products/services, create clear side-by-side comparisons.
6. **Engagement**: Make research findings engaging and easy to understand with emojis and formatting.

[RECALL INSTRUCTIONS - CRITICAL FOR MEMORY QUESTIONS]
1. When user asks "what did we discuss" or "what did I say", you MUST:
   - Use ONLY the [CONVERSATION HISTORY] provided above
   - Reference ONLY facts that actually occurred in the conversation
   - Do NOT infer, guess, or invent traits that weren't explicitly stated
   - Do NOT use generic responses like "You're a great person"
   
2. For recall questions:
   - Start with: "Based on our conversation, you mentioned..."
   - Cite specific messages: "You said: '[exact quote]'"
   - If you have [CONFIRMED STORED MEMORY], mention it: "I also remember that you..."
   - If no relevant history exists, say: "I don't have any record of that in our conversation."
   
3. NEVER:
   - Invent personality traits
   - Make assumptions about the user
   - Use inferred information not in the conversation history
   - Provide generic responses without specific facts

[INTERACTION RULES]
1. **USE YOUR MEMORY**: Always reference what you know about the user when relevant
2. **BE PERSONAL**: Use their name, preferences, and past conversations naturally
3. **BE HELPFUL**: Provide clear, actionable information
4. **BE ENGAGING**: Make responses interesting with emojis, questions, and personality
5. **NO ROBOTIC TALK**: Never say "As an AI..." - Say "I think..." or "I can help..."
6. **SHOW EMPATHY**: Acknowledge emotions and respond appropriately
7. **ASK QUESTIONS**: When appropriate, ask follow-ups to understand better

[EMOJI GUIDELINES - Use These Naturally]:
- Greetings: 👋 🌟 ✨
- Positive: ✅ 🎉 🎊 💪 🌟 ✨
- Thinking: 🤔 💭 🧠
- Ideas: 💡 ✨ 🎯
- Tasks: 📝 ✅ 📌
- Success: 🎉 🚀 ✨ 🏆
- Support: 🫂 ❤️ 💙 🤗
- Information: 📚 📖 💡
- Technology: 💻 🚀 ⚡
- Fun: 🎮 🎨 🎵 🎬
- Food: 🍕 🍔 🍰 ☕
- Travel: ✈️ 🌍 🗺️
- Work: 💼 📊 📈
- Health: 💪 🏃 🧘

Now, respond to the user's message as their true friend and companion. Be engaging, personal, and make them feel good! 🌈✨
"""

    # 🧠 MEMORY HARDENING PROTOCOL - Debug: Log full prompt for verification
    # Developers: Check this log to verify data is in the prompt
    logger.info("=" * 80)
    logger.info("[MEMORY HARDENING DEBUG] Full System Prompt:")
    logger.info("=" * 80)
    logger.info(system_prompt)
    logger.info("=" * 80)
    print(f"🧠 [PROMPT LOG] Full system prompt logged (check logs for details)")
    
    # Check if user facts are in the prompt (critical check)
    graph_context_check = await retrieve_knowledge(user_id)
    if graph_context_check:
        if any(keyword in system_prompt.lower() for keyword in ["name", "likes", "lives", "works"]):
            logger.info(f"✅ [VERIFICATION] User facts detected in prompt")
        else:
            logger.warning(f"⚠️ [VERIFICATION] User facts may not be in prompt - check prompt structure")

    # 4) EXECUTE LLM (supports vision if image_url provided)
    logger.info(f"✅ [Step] Executing LLM to generate response")
    response = await get_llm_response(
        prompt=message,
        system_prompt=system_prompt,
        image_url=image_url,
    )
    
    logger.info(f"[MainBrain] Generated response (length: {len(response)})")
    logger.info(f"✅ [Step] LLM response generated successfully")

    # 5) MEMORY STORAGE LOGIC - Use Unified Orchestrator
    lowered = (message or "").lower()
    
    # Detect what needs to be stored
    storage_tasks = []
    
    # Name detection
    user_name = None
    if "my name is" in lowered:
        parts = lowered.split("my name is")
        if len(parts) > 1:
            raw_name = parts[1].strip().split()[0] if parts[1].strip() else ""
            user_name = raw_name.strip(".,!?,;:").rstrip(",").capitalize()
    elif "i am" in lowered and not any(x in lowered for x in ["i am a", "i am an", "i am the"]):
        parts = lowered.split("i am")
        if len(parts) > 1:
            raw_name = parts[1].strip().split()[0] if parts[1].strip() else ""
            user_name = raw_name.strip(".,!?,;:").rstrip(",").capitalize()
    
    if user_name:
        logger.info(f"🎯 Detected name: {user_name}")
        
        # Store name via unified orchestrator
        # 1) Profile (MongoDB)
        profile_result, profile_logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id,
            memory_content={"name": user_name},
            memory_type=MemoryType.PROFILE,
            metadata={"source": "user_introduction"}
        )
        for log in profile_logs:
            logger.info(log)
        
        # 2) Relationship (Neo4j)
        rel_result, rel_logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id,
            memory_content=("HAS_NAME", user_name),
            memory_type=MemoryType.RELATIONSHIP,
            metadata={"source": "user_introduction"}
        )
        for log in rel_logs:
            logger.info(log)
        
        # 3) Semantic (Pinecone)
        semantic_result, semantic_logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id,
            memory_content=f"My name is {user_name}",
            memory_type=MemoryType.SEMANTIC,
            metadata={"type": "profile", "source": "user_introduction"}
        )
        for log in semantic_logs:
            logger.info(log)
        
        # 4) Session cache (Redis)
        session_result, session_logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id,
            memory_content={"name": user_name, "last_interaction": datetime.now().isoformat()},
            memory_type=MemoryType.SESSION,
            metadata={"ttl": 3600}
        )
        for log in session_logs:
            logger.info(log)
    
    # 🎯 PREFERENCE/INTEREST DETECTION (CRITICAL FOR MEMORY)
    preference_triggers = {
        "i like": "preference",
        "i love": "preference",
        "i enjoy": "preference",
        "i prefer": "preference",
        "my favorite": "preference",
        "i'm interested in": "interest",
        "i want to": "preference"
    }
    
    preference_stored = False
    for trigger, pref_type in preference_triggers.items():
        if trigger in lowered:
            # Extract what they like (everything after the trigger until punctuation)
            parts = lowered.split(trigger)
            if len(parts) > 1:
                # Get the preference text (clean it up)
                preference_text = parts[1].strip()
                
                # Remove common sentence endings
                for ending in ['.', '!', '?', ',', ';']:
                    if ending in preference_text:
                        preference_text = preference_text.split(ending)[0].strip()
                
                # Remove "to" if present at start (e.g., "I like to play" -> "play")
                if preference_text.startswith("to "):
                    preference_text = preference_text[3:].strip()
                
                if len(preference_text) > 2:
                    logger.info(f"🎯 [PREFERENCE DETECTED] Type: {pref_type}, Content: '{preference_text}'")
                    
                    # 1️⃣ Store preference to MongoDB (CRITICAL - Long-term storage)
                    pref_result, pref_logs = await unified_memory_orchestrator.store_memory(
                        user_id=user_id,
                        memory_content=preference_text,
                        memory_type=MemoryType.PREFERENCE,
                        metadata={"type": pref_type, "trigger": trigger, "full_statement": message}
                    )
                    
                    logger.info("=" * 60)
                    logger.info("[MEMORY STORAGE] Preference to MongoDB")
                    for log in pref_logs:
                        logger.info(f"  {log}")
                    
                    if pref_result.success:
                        logger.info(f"✅ [STORAGE SUCCESS] Preference stored to {pref_result.destination}")
                        preference_stored = True
                    else:
                        logger.error(f"❌ [STORAGE FAILED] {pref_result.reason}")
                    logger.info("=" * 60)
                    
                    # 2️⃣ Store as semantic memory to Pinecone (for similarity search)
                    semantic_text = f"User {trigger} {preference_text}"
                    semantic_result, semantic_logs = await unified_memory_orchestrator.store_memory(
                        user_id=user_id,
                        memory_content=semantic_text,
                        memory_type=MemoryType.SEMANTIC,
                        metadata={"type": pref_type, "category": "preference"}
                    )
                    
                    logger.info("=" * 60)
                    logger.info("[MEMORY STORAGE] Semantic to Pinecone")
                    for log in semantic_logs:
                        logger.info(f"  {log}")
                    
                    if semantic_result.success:
                        logger.info(f"✅ [STORAGE SUCCESS] Semantic memory stored")
                    else:
                        logger.error(f"❌ [STORAGE FAILED] {semantic_result.reason}")
                    logger.info("=" * 60)
                    
                    # 3️⃣ OPTIONAL: Store relationship to Neo4j
                    # Extract the object (e.g., "playing chess" -> "chess")
                    object_words = preference_text.split()
                    if len(object_words) > 0:
                        # Get last meaningful word as the object
                        relationship_target = object_words[-1] if len(object_words[-1]) > 3 else preference_text
                        
                        rel_result, rel_logs = await unified_memory_orchestrator.store_memory(
                            user_id=user_id,
                            memory_content=("LIKES" if trigger in ["i like", "i love", "i enjoy"] else "PREFERS", relationship_target),
                            memory_type=MemoryType.RELATIONSHIP,
                            metadata={"preference": preference_text}
                        )
                        
                        logger.info("=" * 60)
                        logger.info("[MEMORY STORAGE] Relationship to Neo4j")
                        for log in rel_logs:
                            logger.info(f"  {log}")
                        logger.info("=" * 60)
                    
                    break  # Only process first match
    
    # Log if no preference was detected but message contains preference keywords
    if not preference_stored:
        if any(word in lowered for word in ["like", "love", "enjoy", "prefer", "favorite"]):
            logger.warning(f"⚠️ [PREFERENCE DETECTION] Keywords found but no preference stored")
            logger.warning(f"   Message: {message}")
            logger.warning(f"   This might be a detection miss - review extraction logic")

    # 6) Save chat history to Redis (always)
    await add_message_to_history(user_id, "User", message)
    await add_message_to_history(user_id, "AI", response)

    # 7) Optional: track mood snapshots in Mongo for analytics (non-critical)
    try:
        await mood_collection.insert_one(
            {
                "user_id": user_id,
                "user_emotion_label": user_emotion,
                "timestamp": datetime.utcnow(),
                "message_snippet": message[:80],
                "response_snippet": (response or "")[:80],
            }
        )
    except Exception as e:
        logger.warning(f"Mood logging failed: {e}")

    return response
