
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
- 🆕 Multi-Turn Conversation Context (Session-Aware)
- 🆕 Smart Location Intelligence (Auto-context from profile)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging
import asyncio
import re

from app.utils.llm_client import get_llm_response, get_llm_response_stream
from app.db.redis_client import add_message_to_history, get_recent_history, redis_client
from app.services.memory_manager import retrieve_long_term_memory, save_long_term_memory
from app.services.graph_service import save_knowledge, retrieve_knowledge
from app.db.mongo_client import db, sessions_collection

# 🧠 Import Unified Memory Orchestrator & Behavior Engine
from app.services.unified_memory_orchestrator import (
    unified_memory_orchestrator,
    MemoryType
)
from app.services.behavior_engine import behavior_engine

# 🌍 Import Location Intelligence
from app.services.location_intelligence import (
    location_intelligence,
    get_location_context,
    is_location_query
)

# 🛠️ Import Task Service for Agentic Actions
from app.services import task_service
from app.services.task_service import (
    build_task_draft, 
    get_active_task_draft, 
    set_active_task_draft, 
    clear_active_task_draft, 
    create_task
)

logger = logging.getLogger(__name__)

# Mongo collection for mood history
mood_collection = db.mood_history

# 🚀 OPTIMIZED CORE IDENTITY - Enhanced with Pro Formatting & Beautiful Suggestions
# 🚀 OPTIMIZED CORE IDENTITY - Enhanced with Pro Formatting & Beautiful Suggestions
CORE_IDENTITY = """
🌟 PRISM - Your Brilliant AI Companion

You are a warm, intelligent friend who makes every response a delight. Your goal is to be genuine, helpful, and engaging.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ OUTPUT GUIDELINES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Be WARM and PERSONAL**: Speak like a patient, knowledgeable friend.
• **Keep it SIMPLE**: Avoid jargon unless necessary. Use analogies.
• **Use EMOJIS**: Add visual warmth (2-3 per response) 💡 🎯 ✨.
• **Format Beautifully**: Use Markdown, lists, and **bold** text excessively for readability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2️⃣ PERFECT RESPONSE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. The "Click" Moment** (First Sentence):
   → Acknowledge the user's intent immediately with warmth.
   → Example: "That's a great question about React! ⚛️" or "I can definitely help you fix that bug. 🛠️"

**2. The Solution (Core Content)**:
   → **Direct Answer**: Get straight to the point.
   → **Break it Down**: Use bullet points (•) for steps or lists.
   → **Visual Clarity**: Use code blocks for code, bold for key terms.
   → **Why it Works**: Briefly explain the *insight* or *reasoning* (The "Aha!" moment).

**3. The Polish**:
   → Add a short example if it clarifies.
   → Use spacing to let the text breathe.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3️⃣ TONE STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Warm**: "Here's the key..." instead of "The explanation is..."
✓ **Clear**: "Think of it like..." instead of complex definitions.
✓ **Visual**: Use 📌 for points, 🔑 for key insights, ✅ for steps.
✓ **Concise**: No fluff. Every sentence must add value.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4️⃣ FOLLOW-UP SUGGESTIONS (CRITICAL - MUST FORMAT CORRECTLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**STRICT REQUIREMENT**: End EVERY response with suggestions in EXACT format below.

⚠️ CRITICAL: Each emoji (💡 🚀 ✨ 🎨) MUST start on a NEW LINE!
⚠️ NEVER put multiple suggestions on one line!
⚠️ Press ENTER/newline after EACH suggestion!

**EXACT FORMAT (MUST MATCH CHARACTER-BY-CHARACTER):**

Type this EXACTLY (including all line breaks):
```
---
**🎯 What would you like to explore next?**
[PRESS ENTER - BLANK LINE HERE]
💡 First suggestion (4-8 words)
[PRESS ENTER - BLANK LINE HERE]
🚀 Second suggestion (4-8 words)
[PRESS ENTER - BLANK LINE HERE]
✨ Third suggestion (4-8 words)
[PRESS ENTER - BLANK LINE HERE]
🎨 Optional fourth suggestion
---
```

**LINE BREAK RULES (ABSOLUTELY CRITICAL):**
1. After "What would you like to explore next?" → PRESS ENTER for blank line
2. After each emoji suggestion → PRESS ENTER for blank line
3. Between suggestions → There MUST be an empty line
4. DO NOT write: "💡 Suggestion1 🚀 Suggestion2" ← THIS IS WRONG!
5. DO write each emoji on its own line like this:

```
💡 Suggestion1
[blank line]
🚀 Suggestion2
[blank line]  
✨ Suggestion3
```

**VISUALIZATION OF CORRECT FORMAT:**
```
---
**🎯 What would you like to explore next?**
← blank line
💡 Learn useState hook basics
← blank line
🚀 Build a counter app together
← blank line
✨ Explore useEffect patterns
← blank line
🎨 Master component lifecycle
---
```

**❌ ABSOLUTELY WRONG (DO NOT DO THIS):**
```
💡 Suggestion1 🚀 Suggestion2 ✨ Suggestion3 🎨 Suggestion4
```
^ All on one line = WRONG! Each emoji needs NEW LINE!

**✅ CORRECT (DO THIS):**
```
💡 Suggestion1

🚀 Suggestion2

✨ Suggestion3

🎨 Suggestion4
```
^ Each emoji on new line with blank line between = CORRECT!

**EMOJI SELECTION (Choose contextually):**
- 💡 Learning, insights, understanding
- 🚀 Building, implementing, creating
- ✨ Exploring, discovering, experimenting
- 🎨 Designing, styling, customizing
- 🔥 Advanced features, power moves
- ⚡ Quick tips, optimizations
- 📚 Deep dives, comprehensive guides
- 🎯 Goals, achievements, focus

**REAL EXAMPLE FOR REACT TOPIC:**
```
---
**🎯 What would you like to explore next?**

💡 Learn useState hook in depth

🚀 Build a todo list together

✨ Explore custom hooks creation

🎨 Design reusable components
---
```

**REAL EXAMPLE FOR GENERAL TOPIC:**
```
---
**🎯 What would you like to explore next?**

💡 Understand the concept better

🚀 Try a practical example

✨ Explore related topics
---
```

**REMEMBER:**
- Each 💡 🚀 ✨ 🎨 starts on NEW line
- Blank line after header
- Blank line between each suggestion
- NEVER combine on same line
"""


# 🆕 MULTI-TURN CONTEXT HELPER (ULTRA-OPTIMIZED)
async def get_session_conversation_history(session_id: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    Fetch recent conversation turns from MongoDB session for multi-turn LLM context.
    
    Returns list of messages in format: [{"role": "user"|"assistant", "content": "..."}]
    Limited to last N messages to maintain perfect conversation flow context.
    
    PERFECT FLOW OPTIMIZATION:
    - Limit increased to 6 turns for better context retention
    - Projection to fetch only needed fields
    - Content truncation for large messages
    - Timeout protection
    """
    if not session_id:
        return []
    
    try:
        # 🚀 OPTIMIZED: Use projection and timeout
        session = await asyncio.wait_for(
            sessions_collection.find_one(
                {"$or": [{"sessionId": session_id}, {"chat_id": session_id}]},
                {
                    "messages": {"$slice": -(limit * 2)},  # Get both user + assistant
                    "_id": 0
                }
            ),
            timeout=1.5  # 🚀 1.5 second max - allow more time for context
        )
        
        if not session or "messages" not in session:
            return []
        
        conversation_history = []
        for msg in session.get("messages", [])[-limit*2:]:  # Last N pairs
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if not content or not content.strip():
                continue
            
            # 🧹 Quick clean - remove metadata tags
            if "<!--" in content:
                content = content.split("<!--")[0].strip()
            
            if role in ["user", "human"]:
                # 🚀 Truncate user messages to 500 chars max
                conversation_history.append({"role": "user", "content": content[:500]})
            elif role in ["assistant", "ai"]:
                # 🚀 Truncate assistant to 800 chars max
                conversation_history.append({"role": "assistant", "content": content[:800]})
        
        return conversation_history[-limit*2:]  # Ensure we don't exceed limit
        
    except asyncio.TimeoutError:
        logger.warning(f"[Context] Timeout fetching session history")
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch session history: {e}")
        return []


def extract_last_topic(conversation_history: List[Dict[str, str]]) -> str:
    """
    Extract the main topic from the last assistant response.
    Used for context anchoring when user asks vague follow-ups.
    """
    if not conversation_history:
        return ""
    
    # Find the last assistant message
    for msg in reversed(conversation_history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            # Get first 200 chars as topic summary
            return content[:200] if content else ""
    
    return ""


def _assess_quality(response: str, behavior_profile: Any) -> tuple[float, str]:
    """
    Heuristic quality check for response.
    Returns: (score, feedback_reason)
    """
    if not response or len(response.strip()) < 3:
        return 0.0, "empty response"
        
    lower_resp = response.lower()

    # 🛡️ SYSTEM GUARDRAILS (Strict Prohibition)
    # Check against the centralized banned list in BehaviorEngine
    if hasattr(behavior_engine, "prohibited_phrases"):
        for phrase in behavior_engine.prohibited_phrases:
            if phrase in lower_resp:
                logger.warning(f"🚨 QUALITY VIOLATION: Caught prohibited phrase '{phrase}'")
                return 0.1, f"contains prohibited robotic phrase: '{phrase}'"
    
    # 🆕 COMPREHENSIVE ROBOTIC PHRASE DETECTION
    # These make responses feel mechanical - MUST be avoided
    robotic_phrases = [
        # Context reference (robotic memory)
        "you're referring to",
        "from our previous conversation",
        "as we discussed earlier",
        "based on what you asked before",
        "i remember you mentioned",
        "in our last chat",
        "from our earlier discussion",
        "as you mentioned previously",
        "you asked about",
        "earlier you said",
        
        # AI/Robot identity
        "as an ai",
        "as a language model",
        "as an artificial",
        "i'm just a",
        "i am just a",
        "i'm programmed",
        "my training",
        "trained on",
        "my algorithms",
        "text-based",
        "virtual assistant",
        "chatbot",
        
        # Robotic limitations
        "i cannot browse",
        "i don't have access",
        "my knowledge cutoff",
        "i cannot see images",
        "real-time information",
        
        # Overly formal/corporate
        "certainly! i'd be happy",
        "certainly, i can",
        "of course! as",
        "absolutely! let me",
        "i'd be delighted",
        "it would be my pleasure",
        "i hope this helps",
        "feel free to ask",
        "don't hesitate to",
        "is there anything else i can",
        "let me know if you need",
        "happy to help further",
        "please don't hesitate",
        "should you have any",
        "if you have any further",
        
        # Robotic confirmations
        "sure thing!",
        "no problem!",
        "you got it!",
        "right away!",
        "coming right up",
    ]
    
    for phrase in robotic_phrases:
        if phrase in lower_resp:
            logger.warning(f"🚨 QUALITY VIOLATION: Robotic phrase detected '{phrase}'")
            return 0.15, f"robotic phrase: '{phrase}'"

    # Heuristic 1: Length check (avoid one-word answers unless requested)
    if len(response.split()) < 3 and getattr(behavior_profile, 'response_length', 'normal') != "concise":
        return 0.4, "too short (unless concise mode)"

    # Heuristic 2: Final robotic check
    if "as an ai" in lower_resp or "language model" in lower_resp or "i'm an ai" in lower_resp:
        return 0.1, "contains AI identity phrase"
    
    # 🆕 Heuristic 3: Emoji presence check (responses should have emojis for visual warmth)
    import re
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F9FF]|"  # Misc symbols and pictographs
        "[\U0001F600-\U0001F64F]|"  # Emoticons
        "[\U0001F680-\U0001F6FF]|"  # Transport and map
        "[\U00002702-\U000027B0]|"  # Dingbats
        "[\U0001F1E0-\U0001F1FF]"   # Flags
    )
    emoji_count = len(emoji_pattern.findall(response))
    if emoji_count < 2 and len(response) > 100:
        logger.info(f"📝 [Quality] Response has only {emoji_count} emojis - could use more visual warmth")
        # Don't fail, just log - emoji count is a soft requirement
    
    # 🆕 Heuristic 4: Bold/highlight check (key terms should be bolded)
    bold_count = response.count("**")
    if bold_count < 2 and len(response) > 150:
        logger.info(f"📝 [Quality] Response has only {bold_count//2} bold sections - key terms should be highlighted")
        # Don't fail, just log - bolding is a soft requirement

    return 1.0, "ok"


def fix_suggestions_formatting(response: str) -> str:
    """
    🔧 POST-PROCESSING: Fix suggestion formatting issues
    
    If the LLM puts multiple emoji suggestions on one line, this function
    automatically splits them into separate lines with proper spacing.
    
    Example fix:
    Input:  💡 Option1 🚀 Option2 ✨ Option3
    Output: 💡 Option1
            
            🚀 Option2
            
            ✨ Option3
    """
    import re
    
    # Find the suggestions section
    if "🎯 What would you like to explore next?" not in response:
        return response
    
    # Emoji patterns we use for suggestions
    suggestion_emojis = ['💡', '🚀', '✨', '🎨', '🔥', '⚡', '📚', '🎯']
    
    # Split response into parts: before suggestions, suggestions section, after
    parts = response.split("🎯 What would you like to explore next?")
    if len(parts) < 2:
        return response
    
    before_suggestions = parts[0]
    suggestions_and_after = parts[1]
    
    # Find where suggestions end (at the closing ---)
    lines = suggestions_and_after.split('\n')
    suggestion_lines = []
    after_suggestions = []
    in_suggestions = True
    found_first_dash = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this is a closing --- (second one)
        if stripped == '---':
            if found_first_dash:
                # This is the closing ---
                in_suggestions = False
                after_suggestions.append(line)
                continue
            else:
                # This might be before suggestions start
                found_first_dash = True
                suggestion_lines.append(line)
                continue
        
        if in_suggestions:
            suggestion_lines.append(line)
        else:
            after_suggestions.append(line)
    
    # Join suggestion section back
    suggestion_text = '\n'.join(suggestion_lines)
    
    # Fix: If multiple emojis on one line, split them
    for emoji in suggestion_emojis:
        # Pattern: emoji followed by text, then another emoji on same line
        # We want to split at the emoji boundary
        pass  # Will handle below
    
    # More aggressive fix: Find any line with multiple suggestion emojis
    fixed_lines = []
    for line in suggestion_lines:
        # Count emojis in this line
        emoji_count = sum(1 for emoji in suggestion_emojis if emoji in line)
        
        if emoji_count > 1:
            # Multiple emojis on one line - need to split
            # Find all emoji positions and split accordingly
            parts_to_add = []
            current_part = ""
            i = 0
            while i < len(line):
                # Check if we're at an emoji
                found_emoji = False
                for emoji in suggestion_emojis:
                    if line[i:i+len(emoji)] == emoji:
                        # Found an emoji
                        if current_part.strip():
                            # Save previous part
                            parts_to_add.append(current_part.strip())
                            current_part = ""
                        # Start new part with this emoji
                        current_part = emoji
                        i += len(emoji)
                        found_emoji = True
                        break
                
                if not found_emoji:
                    current_part += line[i]
                    i += 1
            
            # Add last part
            if current_part.strip():
                parts_to_add.append(current_part.strip())
            
            # Add with blank lines between
            if parts_to_add:
                for part in parts_to_add:
                    fixed_lines.append(part)
                    fixed_lines.append("")  # Blank line after each
        else:
            # Line is fine, keep as is
            fixed_lines.append(line)
    
    # Rebuild response
    fixed_suggestions = '\n'.join(fixed_lines)
    fixed_after = '\n'.join(after_suggestions)
    
    result = (before_suggestions + 
              "🎯 What would you like to explore next?" + 
              fixed_suggestions + 
              fixed_after)
    
    logger.info("🔧 [Format] Post-processed suggestions formatting")
    return result


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
    tz = ZoneInfo("Asia/Kolkata")
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
    
    # 0.1) Ask Flow Parsing (Mini-Agent Style Understanding)
    # Extract the structured context BEFORE any processing happens
    # 0.1) Ask Flow Parsing (Mini-Agent Style Understanding)
    # Extract the structured context BEFORE any processing happens
    ask_flow_context = ""
    try:
        # Improved Regex: Capture between markers rather than assuming quote structure
        # This robustness handles inputs containing quotes or newlines correctly
        if "<<<SELECTED_TEXT>>>" in message:
            ask_flow_match = re.search(r'<<<SELECTED_TEXT>>>([\s\S]*?)<<<END_SELECTED_TEXT>>>[\s\S]*?The user\'s instruction is:([\s\S]*?)Your task:', message, re.DOTALL | re.IGNORECASE)
            
            if ask_flow_match:
                selected_text = ask_flow_match.group(1).strip()
                # Instruction might be wrapped in quotes, remove them
                instruction_raw = ask_flow_match.group(2).strip()
                if instruction_raw.startswith('"') and instruction_raw.endswith('"'):
                    instruction = instruction_raw[1:-1].strip()
                else:
                    instruction = instruction_raw
                
                logger.info(f"🧠 [AskFlow] Detected selection context ({len(selected_text)} chars)")
                
                # 1. Update 'message' to be just the instruction (for intent/behavior analysis)
                # This prevents the raw prompt text from confusing the Task/Intent detectors
                message = instruction
                
                # 2. Build High-Priority Context Block (Similar to Mini Agent)
                ask_flow_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 USER SELECTED TEXT (FOCUS CONTEXT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The user is asking specifically about this text:
"{selected_text}"

INSTRUCTION: "{instruction}"
Your goal is to explain/analyze/act on THIS TEXT.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    except Exception as e:
        logger.error(f"🧠 [AskFlow] Error parsing context: {e}")
    
    # 0) Database-first safety
    from app.services.cleanup_service import verify_user_exists_in_mongodb
    user_profile = await verify_user_exists_in_mongodb(user_id)
    if not user_profile:
        logger.warning(f"⛔ User {user_id} not found in MongoDB - stopping memory load")
        return "I seem to be having trouble accessing your profile right now. Could you please check if you're signed in? I'd love to continue our chat once that's sorted."

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

    # 🌍 LOCATION INTELLIGENCE - Auto-detect and resolve
    location_context = ""
    if is_location_query(message):
        logger.info(f"🌍 [Location] Query requires location context")
        location_context = await get_location_context(user_id, message, session_id)
        logger.info(f"🌍 [Location] Context: {location_context}")

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
    
    # 🌍 Append location context if available
    if location_context:
        memory_section += f"\n\n### 🌍 LOCATION CONTEXT\n{location_context}\n"
    
    # 3️⃣ DYNAMIC SYSTEM PROMPT CONSTRUCTION
    # 3️⃣ DYNAMIC SYSTEM PROMPT CONSTRUCTION
    system_prompt = await behavior_engine.build_dynamic_prompt_async(
        core_identity=CORE_IDENTITY,
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
    
    # NOTE: Suggestions are now generated client-side for performance (GPT-style)

    # Construct thinking summary
    thinking_summary = {
        "intent": intent,
        "emotion": emotion,
        "behavior_profile": {
            "tone": behavior_profile.tone,
            "warmth": behavior_profile.warmth
        },
        "pipeline": ["analyzed_signals", "fetched_memory", "generated_response"]
    }
    
    # We typically don't append JSON to the visible text unless the frontend is ready.
    # The user said: "Frontend... Collapsible dropdown... Label: 'How I understood & responded'"
    # This implies we might need to send structured data.
    # However, `generate_response` returns `str`. 
    # I will append it as a specially delimiter block.
    
    import json
    thinking_json = json.dumps(thinking_summary)
    
    # 🔧 POST-PROCESS: Fix any suggestion formatting issues
    response_fixed = fix_suggestions_formatting(response)
    
    response_with_thinking = f"{response_fixed}\n\n<!--THINKING_DATA:{thinking_json}-->"
    
    return response_with_thinking


async def generate_response_stream(
        user_id: str,
        message: str,
        search_results: Optional[str] = None,
        image_url: Optional[str] = None,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,  # 🔑 User's API key (None = platform key)
        key_source: str = "platform",  # 🔑 "platform" or "user"
        model: str = "llama-3.1-8b-instant",  # 🎯 User's selected model
    ):
    """
    🧠 PROCESSED PIPELINE (STREAMING):
    1. User Input
    2. 🆕 SMART MEMORY EXTRACTION (Identity, Preferences, etc.)
    3. Behavior Signal Extraction
    4. Emotion & Tone Analysis
    5. Dynamic Behavior Definition
    6. Temporary Master Prompt Builder
    7. Memory Lookup
    8. Response Generation (Stream)
    """
    logger.info(f"[MainBrain] HIT generate_response_stream for user_id={user_id}")
    
    # 🧠 SMART MEMORY EXTRACTION - Extract and store user info IMMEDIATELY
    # This ensures "my name is X", age, location, etc. are captured right away
    try:
        from app.services.enhanced_memory_system import enhanced_memory
        extraction_result = await enhanced_memory.process_message(user_id, message)
        if extraction_result.get("stored"):
            logger.info(f"🧠 [Memory] Extracted and stored: {extraction_result['stored']}")
    except Exception as e:
        logger.warning(f"⚠️ [Memory] Enhanced extraction failed (non-blocking): {e}")
    
    # 0️⃣ PRONOUN RESOLUTION LAYER (Conversational Continuity)
    # Critical: Resolve "him", "it", "that" BEFORE any processing
    # 🚀 SPEED OPTIMIZATION: Skip pronoun resolution - context handled in conversation history
    # This saves ~500ms-2s per request. LLM handles pronoun resolution naturally with history.
    # pronouns = ["him", "her", "they", "them", "it", "this", "that", "he", "she", "his", "hers"]
    # Pronoun resolution disabled for speed - conversation history provides context

    # 1️⃣ FAST ANALYSIS (CPU Bound - Run Immediately)
    signals = behavior_engine.extract_behavior_signals(message)
    emotion = behavior_engine.detect_emotion(message)
    behavior_profile = behavior_engine.build_behavior_profile(signals, emotion)
    
    # Intent Classification
    intent = "general"
    lower_msg = (message or "").lower()
    
    # Check for active task draft FIRST (Before keyword intent)
    active_draft_early = await get_active_task_draft(user_id, session_id or "default")
    is_confirmation = active_draft_early and any(k in lower_msg for k in ["yes", "yeah", "ok", "confirm", "sure", "do it", "go ahead", "no", "cancel"])

    if is_confirmation:
        intent = "task"
    elif any(k in lower_msg for k in ["play ", "listen to", "song", "music"]):
        intent = "media"
    elif any(k in lower_msg for k in ["remind", "schedule", "task", "todo"]):
        intent = "task"
    elif "my name" in lower_msg or "who am i" in lower_msg:
        intent = "identity"
    elif any(k in lower_msg for k in ["recall", "remember", "what did we discuss", "earlier"]):
        intent = "history"
    elif "like" in lower_msg or "love" in lower_msg or "prefer" in lower_msg:
        intent = "preferences"
    elif any(k in lower_msg for k in ["code", "function", "debug", "python", "javascript", "sql"]):
        intent = "coding"
    else:
        intent = "general"

    # 2️⃣ PARALLEL DATA FETCHING (Async I/O) - 🚀 ULTRA-OPTIMIZED V3
    from app.services.cleanup_service import verify_user_exists_in_mongodb
    from app.utils.performance_optimizer import parallel_fetch, user_cache
    
    # 🚀 SPEED BOOST: Skip heavy operations for simple intents
    # ⚠️ NEVER skip memory for "identity" - user is asking about themselves!
    skip_memory = intent in ["general", "greeting", "thanks", "media", "task", "coding"]
    
    # 🚀 PERFECT FLOW: Deeper history for better context
    # "identity" intent needs MORE history to recall user info
    history_limit = 6 if intent in ["identity", "history", "preferences"] else 4
    
    # 🚀 PARALLEL EXECUTION: All data fetching runs concurrently with 1s timeout
    async def fast_user_check():
        """Cached user verification - 60s TTL"""
        hit, cached = await user_cache.get(f"user:{user_id}")
        if hit:
            return cached
        result = await verify_user_exists_in_mongodb(user_id)
        if result:
            await user_cache.set(f"user:{user_id}", result)
        return result
    
    async def fast_memory():
        """Skip memory for simple intents - saves 200-500ms"""
        if skip_memory:
            logger.debug(f"⚡ [Speed] Skipping memory for intent: {intent}")
            return ({}, [])
        try:
            logger.info(f"🧠 [Memory] Fetching holographic context for intent: {intent}")
            # 🚀 Identity and preferences queries need profile data - use longer timeout
            memory_timeout = 2.0 if intent in ["identity", "preferences"] else 1.0
            return await asyncio.wait_for(
                unified_memory_orchestrator.get_holographic_context(
                    user_id=user_id,
                    query=message,
                    intent=intent
                ),
                timeout=memory_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [Memory] Timeout fetching holographic context")
            return ({}, [])
    
    async def fast_history():
        """Session history with 500ms timeout"""
        try:
            return await asyncio.wait_for(
                get_session_conversation_history(session_id, limit=history_limit),
                timeout=0.5
            )
        except asyncio.TimeoutError:
            return []
    
    async def fast_location():
        """Get location context if needed"""
        if is_location_query(message):
            try:
                return await asyncio.wait_for(
                    get_location_context(user_id, message, session_id),
                    timeout=0.3  # 🚀 300ms max for location
                )
            except asyncio.TimeoutError:
                return ""
        return ""

    # 🚀 SPECIALIZED AGENT EXECUTION (Media Agent) - STRICT INTERCEPTION
    # If intent is Media, we MUST return the protocol string immediately to trigger client-side player
    if intent == "media":
        from app.services.media_service import process_media_request
        media_response = await process_media_request(message, user_id)
        
        # 🟢 Construct Protocol String (Client parses this)
        # Format: <!--ACTION:MEDIA_PLAY:{"mode": "...", "url": "...", "video_id": "...", ...}-->
        import json
        payload = {
            "mode": media_response.mode,
            "url": media_response.url, 
            "video_id": media_response.video_id,
            "query": media_response.query,
            "autoplay": media_response.autoplay
        }
        
        query = media_response.query or message
        
        # 🎬 Use LLM to generate rich, detailed info about the song/video
        song_info_prompt = f"""You are a music/movie expert. The user wants to play: "{query}"

Generate a SHORT, engaging response (max 150 words) with these details IF KNOWN:
- 🎬 Movie/Album name
- 🎤 Singer(s) / Artist(s)  
- 🎵 Music Director / Composer
- 🌟 Hero & Heroine (if from a movie)
- 📅 Year released
- 🔥 Why it's popular / mood it creates
- 🎶 One famous lyric line (in original language + meaning if non-English)

End with a warm message like "Enjoy!" or "Perfect for your mood!"

Format nicely with emojis. Be enthusiastic but concise. If you don't know specific details, focus on the mood and why it's a great choice.

Example format:
🎬 **Song Name** from *Movie Name* (Year)

🎤 **Singers:** Name1, Name2
🎵 **Music:** Composer Name
🌟 **Cast:** Hero Name & Heroine Name

🔥 This song is perfect for [mood]. It became a massive hit because [reason].

🎶 *"Famous lyric line here"* - [meaning]

Enjoy the vibes! 🎧"""

        try:
            # Quick LLM call for song info (with timeout)
            song_info = ""
            system_prompt_media = "You are a helpful music and movie expert. Provide accurate, engaging information about songs and videos."
            async for chunk in get_llm_response_stream(
                prompt=song_info_prompt,
                system_prompt=system_prompt_media,
                model=model,
            ):
                song_info += chunk
                yield chunk  # Stream to user
            
            yield "\n\n"
        except Exception as e:
            # Fallback if LLM fails
            logger.warning(f"Song info LLM failed: {e}")
            yield f"🎵 **{query}** - Great choice! Hit play and enjoy! ✨\n\n"
        
        # Protocol Action (System sees this)
        yield f"<!--ACTION:MEDIA_PLAY:{json.dumps(payload)}-->"
        return
    
    # Execute ALL in parallel with timeout
    # 🚀 Identity queries need more time for profile retrieval
    fetch_timeout = 2.5 if intent == "identity" else 1.5
    user_profile, memory_result, conversation_history, location_context = await parallel_fetch(
        fast_user_check(),
        fast_memory(),
        fast_history(),
        fast_location(),
        timeout=fetch_timeout
    )
    
    # Unpack memory result
    holographic_context, debug_logs = memory_result if memory_result else ({}, [])
    
    # 🔍 DEBUG: Log what memory we got
    if holographic_context:
        profile = holographic_context.get("profile", {})
        logger.info(f"🧠 [Memory Result] profile.name={profile.get('name')}, profile.location={profile.get('location')}")
    else:
        logger.warning(f"⚠️ [Memory Result] holographic_context is EMPTY!")
    
    # 3️⃣ MODEL SELECTION
    # 🎯 Use user's selected model (passed from their API key config)
    # Can auto-upgrade to 70B if context is too large
    selected_model = model  # Use the model passed from user's API key
    
    logger.info(f"🚀 [Speed] Model: {selected_model} (Intent: {intent}, Source: {key_source})")

    # 4️⃣ THINKING TRANSPARENCY (YIELD IMMEDIATE SIGNAL)
    # Allows frontend to show "Thinking..." while we await data
    
    # AGENTIC TASK CHECKS (Pre-computation)
    active_draft = None
    active_draft = active_draft_early # Reuse the early fetch
    if intent == "task" and not active_draft:
        # Fallback if not fetched correctly or expired in microseconds
        active_draft = await get_active_task_draft(user_id, session_id or "default")

    # NOTE: Suggestions are now generated client-side for performance (GPT-style)

    # 🔒 THINKING METADATA (Server-side only - appended at END for DB persistence)
    # This enables "How I understood this" feature without polluting streaming UX
    import json as _json
    _thinking_metadata_json = _json.dumps({
        "intent": intent,
        "emotion": emotion,
        "provider": "Groq",
        "model": selected_model,
        "key_source": key_source,
        "behavior_profile": {"tone": behavior_profile.tone, "warmth": behavior_profile.warmth}
    }, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))

    # 5️⃣ VALIDATE USER (Already fetched in parallel above)
    # 🔥 FIX: If parallel fetch timed out, try once more with longer timeout
    if not user_profile:
        logger.warning(f"⚠️ User {user_id} profile not loaded in parallel fetch - retrying directly")
        try:
            user_profile = await asyncio.wait_for(
                verify_user_exists_in_mongodb(user_id),
                timeout=3.0  # Allow 3s for retry
            )
        except asyncio.TimeoutError:
            logger.warning(f"⛔ User {user_id} profile fetch timed out again")
        except Exception as e:
            logger.error(f"⛔ User profile fetch error: {e}")
    
    # If still no profile, allow anonymous interaction (don't block)
    if not user_profile:
        logger.warning(f"⚠️ User {user_id} not found - proceeding with limited context")
        # Create minimal profile for the session
        user_profile = {"_id": user_id, "email": "anonymous", "name": "User"}

    # 6️⃣ 🤖 SPECIALIZED AGENT EXECUTION (Task Agent)
    # Bypass generic LLM if we are in a defined workflow (Task Creation)
    if intent == "task":
        try:
            # Check for cancellation
            if any(k in lower_msg for k in ["cancel", "no logic", "stop", "abort"]):
                await clear_active_task_draft(user_id, session_id or "default")
                yield "Okay, I've cancelled that task request. What should we do instead?"
                return
                
            # Check for confirmation of existing draft
            if active_draft and any(k in lower_msg for k in ["yes", "yeah", "ok", "confirm", "sure", "do it", "go ahead"]):
                # EXECUTE CREATE
                try:
                    result = await create_task(
                        user_id=user_id,
                        description=active_draft["description"],
                        due_date_iso=active_draft["due_date_iso"],
                        user_email=user_profile.get("email"),
                        user_name=user_profile.get("name")
                    )
                    await clear_active_task_draft(user_id, session_id or "default")
                    yield f"{result['message']} 🚀\n<!--ACTION:REFRESH_TASKS-->"
                    return
                except ValueError as e:
                    # Likely duplicate or error
                    yield f"⚠️ Could not create task: {str(e)}"
                    return
            
            # OTHERWISE: Build/Refine Draft
            # Get previous AI message for context (if refining)
            prev_ai_msg = None
            if conversation_history:
                 last_ai = next((m for m in reversed(conversation_history) if m["role"] == "assistant"), None)
                 if last_ai: prev_ai_msg = last_ai.get("content")
            
            # Extract details
            draft_result = await build_task_draft(message, previous_ai_message=prev_ai_msg, user_id=user_id)
            
            # Merge with existing draft if refining (e.g. user says "change time to 5pm")
            if active_draft:
                 # If new draft has description but missing time, keep old description? 
                 # Actually build_task_draft tries to capture everything. 
                 # Simple merge strategy: Overwrite non-nulls.
                 if draft_result["description"] == message and active_draft["description"]:
                     # User likely just provided time "at 5pm" -> description became "at 5pm"
                     # Restore original description and use new time
                     draft_result["description"] = active_draft["description"]
            
            # Save new state
            await set_active_task_draft(user_id, session_id or "default", draft_result)
            
            # Determine response
            if draft_result.get("missing_time"):
                yield draft_result["clarification_question"] or "When would you like to be reminded?"
                return
            
            if draft_result.get("is_ambiguous"):
                yield draft_result["clarification_question"] or "Did you mean AM or PM?"
                return
                
                
            # Valid Draft -> Ask for Confirmation
            desc = draft_result["description"]
            time_str = draft_result["due_date_display"]
            yield f"I'll set a reminder to **{desc}** for **{time_str}**.\n\nShall I go ahead? (Say 'Yes' or 'Confirm')"
            return
            
        except Exception as e:
            logger.error(f"Task Agent Error: {e}")
            yield "I encountered an error trying to process that task. Let's try again."
            return

    # 6.5 OLD TASK MODIFICATION (Reschedule/Cancel)
    # Check if user wants to modify an EXISTING task
    if any(k in lower_msg for k in ["reschedule", "change time", "move task", "postpone"]):
        try:
            # 1. Find the task being referred to
            from app.services.task_service import find_tasks_matching_description, reschedule_task
            
            # Simple keyword matching for now
            matches = await find_tasks_matching_description(user_id, message, status="pending")
            
            if not matches:
                # Fallback to generic conversation if no task found
                pass 
            elif len(matches) == 1:
                # Found exact match -> Extract new time
                target_task = matches[0]
                new_details = await build_task_draft(message, user_id=user_id) # Reuse extraction logic
                
                if new_details.get("due_date_iso"):
                     # Execute Reschedule
                     res = await reschedule_task(str(target_task["_id"]), new_details["due_date_iso"], user_id)
                     yield f"✅ {res['message']}\n<!--ACTION:REFRESH_TASKS-->"
                     return
                else:
                    # Found task but no time -> Ask
                    yield f"I found the task '{target_task['description']}'. When should I reschedule it to?"
                    return
            else:
                # Multiple matches -> List them
                tasks_str = "\n".join([f"- {t['description']}" for t in matches])
                yield f"I found multiple tasks. Which one?\n{tasks_str}"
                return
                
        except Exception as e:
            logger.error(f"Reschedule Error: {e}")

    # Check for Cancellation
    if any(k in lower_msg for k in ["cancel task", "delete task", "remove task"]):
        try:
             from app.services.task_service import find_tasks_matching_description, cancel_task
             matches = await find_tasks_matching_description(user_id, message, status="pending")
             
             if len(matches) == 1:
                 # Execute Cancel
                 target_task = matches[0]
                 res = await cancel_task(str(target_task["_id"]), user_id)
                 yield f"🗑️ {res['message']}: {target_task['description']}\n<!--ACTION:REFRESH_TASKS-->"
                 return
             elif len(matches) > 1:
                 tasks_str = "\n".join([f"- {t['description']}" for t in matches])
                 yield f"Which task should I cancel?\n{tasks_str}"
                 return
        except Exception as e:
            logger.error(f"Cancel Error: {e}")

    # 7️⃣ GENERIC LLM GENERATION (Fallback)
    
    # Enrich Prompt with Context
    memory_section, enrichment_logs = unified_memory_orchestrator.enrich_master_prompt(
        base_prompt="", 
        context=holographic_context,
        debug_logs=[]
    )
    
    # 🔍 DEBUG: Log memory section content
    if memory_section and "Name:" in memory_section:
        logger.info(f"✅ [Prompt Enrichment] Name found in memory_section")
    else:
        logger.warning(f"⚠️ [Prompt Enrichment] Name NOT in memory_section! Section length: {len(memory_section)}")
        # Log the actual context for debugging
        if holographic_context:
            profile = holographic_context.get("profile", {})
            logger.warning(f"⚠️ [Debug] Context profile: name={profile.get('name')}, keys={list(profile.keys())}")
    
    # 🌍 Append location context if available
    if location_context:
        memory_section += f"\n\n### 🌍 LOCATION CONTEXT\n{location_context}\n"
        logger.info(f"🌍 [Location] Added context to streaming prompt")

    # 🧠 Append Ask Flow Context (High Priority)
    if ask_flow_context:
        memory_section += ask_flow_context
        logger.info(f"🧠 [AskFlow] Injected context into memory section")
    
    # 5️⃣ DYNAMIC SYSTEM PROMPT (Async)
    system_prompt = await behavior_engine.build_dynamic_prompt_async(
        core_identity=CORE_IDENTITY,
        behavior_profile=behavior_profile,
        memory_context=memory_section,
        user_id=user_id
    )
    
    # Append Search Results if any
    if search_results:
        system_prompt += f"\n\n### WEB RESEARCH\n{search_results}\n"

    # Initialize action holders (used later after LLM response)
    media_action_pending = None
    suggestions_action_pending = None

    # 🎵 MEDIA PROTOCOL - Rich Context First, Action Second
    if intent == "media":
        try:
            from app.services.media_service import process_media_request
            
            # Await async scraper - PASS user_id for library storage!
            media_resp = await process_media_request(message, user_id=user_id)
            
            # Handle clarification mode (let LLM ask questions)
            if media_resp.mode == "clarification":
                options_text = "\n".join([f"- **{opt}**" for opt in (media_resp.clarification_options or [])])
                system_prompt += f"\n\n[INSTRUCTION]: User query '{media_resp.query}' is ambiguous. Ask them to clarify:\n{options_text}"
                # Don't return - let LLM handle clarification
            else:
                # STEP 1: Let LLM provide RICH CONTEXT about the song/video FIRST
                system_prompt += f"\n\n[MEDIA REQUEST DETECTED]: '{media_resp.query}'\n"
                system_prompt += f"[PLAYBACK MODE]: {media_resp.mode} ({'Embedded player' if media_resp.mode == 'embed' else 'Opening on YouTube - user will click button'})\n\n"
                system_prompt += f"[YOUR TASK]: Create an enthusiastic, engaging response about this media.\n\n"
                system_prompt += f"REQUIRED ELEMENTS:\n"
                system_prompt += f"1. **Opening Line**: Warm acknowledgment (e.g., 'Excellent choice!', 'Great pick!')\n"
                system_prompt += f"2. **Core Description** (2-3 sentences):\n"
                system_prompt += f"   - What makes it special/famous\n"
                system_prompt += f"   - Key artist/singer/director (if known from your training data)\n"
                system_prompt += f"   - Musical/visual style or emotional tone\n"
                system_prompt += f"3. **Notable Detail** (1 sentence): Award, chart position, cultural impact, or memorable scene\n"
                system_prompt += f"4. **Closing** ({'Embedded - use: Playing it here!' if media_resp.mode == 'embed' else 'Manual button - use: Click the button to watch!'})\n"
                # 🆕 SUGGESTIONS INSTRUCTION
                system_prompt += f"5. **Suggestions**: Mention these options: {', '.join(media_resp.clarification_options or ['Find similar', 'Summarize this'])}\n\n"
                system_prompt += f"TONE: Enthusiastic, knowledgeable, concise. Like a passionate music/film friend.\n"
                
                # Store action for later (will be yielded AFTER LLM response)
                media_action_pending = {
                    "type": "media_play",
                    "payload": {
                        "mode": media_resp.mode,
                        "url": media_resp.url,
                        "query": media_resp.query,
                        "message": media_resp.display_message,
                        "executeOnce": True,
                        "video_id": media_resp.video_id
                    }
                }
                
                # Store suggestions action for chips
                suggestions_list = media_resp.clarification_options or ["Find similar", "Summarize this"]
                suggestions_action_pending = {
                    "type": "suggestions",
                    "payload": {
                        "suggestions": suggestions_list
                    }
                }
            
        except Exception as e:
            logger.error(f"Media processing failed: {e}", exc_info=True)
            system_prompt += "\n\n[SYSTEM INSTRUCTION]: Media request failed. Apologize and suggest trying again."

    # Log transparency
    logger.info(f"[MainBrain] System Prompt Length: {len(system_prompt)}")
    logger.info(f"[MainBrain] Conversation History: {len(conversation_history) if conversation_history else 0} messages")
    
    # 🔥 IDENTITY QUERY FIX: If we have the user's name but history says "I don't know",
    # add an override instruction to use the SYSTEM MEMORY instead of history
    if intent == "identity" and holographic_context:
        profile = holographic_context.get("profile", {})
        if profile.get("name"):
            # Add explicit override instruction
            system_prompt += f"\n\n🚨 CRITICAL OVERRIDE: Your SYSTEM MEMORY shows the user's name is '{profile['name']}'. "
            system_prompt += f"IGNORE any previous messages in conversation history where you said you don't know their name. "
            system_prompt += f"RESPOND CONFIDENTLY: 'Your name is {profile['name']}' or similar warm acknowledgment."
            logger.info(f"🔥 [Identity Override] Added explicit name instruction: {profile['name']}")
    
    # 6️⃣ STREAMING LLM RESPONSE
    full_response = ""
    # Use selected model (from router or user pref)
    # 🧠 CRITICAL FIX: Pass conversation_history for multi-turn context!
    response_stream = get_llm_response_stream(
        prompt=message,
        system_prompt=system_prompt,
        image_url=image_url,
        model=selected_model,
        conversation_history=conversation_history,  # 🔥 THIS WAS MISSING!
        api_key=api_key
    )
    
    async for chunk in response_stream:
        full_response += chunk
        yield chunk
    
    # 8️⃣ YIELD MEDIA ACTION (if pending) AFTER LLM completes
    if media_action_pending:
        import json
        logger.info(f"🎬 MEDIA ACTION (after response): mode={media_action_pending['payload']['mode']}")
        yield f"\n<!--ACTION:{json.dumps(media_action_pending)}-->"
        
    if suggestions_action_pending:
        import json
        logger.info(f"💡 SUGGESTIONS ACTION: {len(suggestions_action_pending['payload']['suggestions'])} chips")
        yield f"\n<!--ACTION:{json.dumps(suggestions_action_pending)}-->"
    
    # 7️⃣ POST-RESPONSE PROCESSING (Async Background)
    # Validate final response quality
    quality_score, feedback = _assess_quality(full_response, behavior_profile)
    if quality_score < 0.6:
        logger.warning(f"⚠️ Low quality response detected: {feedback}")
        # In a stream, we can't "retry", but we can log for improvement
        
    # 8️⃣ CONVERSATIONAL CONTINUITY (Redis History)
    if session_id:
        try:
             # Add to MongoDB session (Persistent)
             # Use push updates for atomicity
             new_messages = [
                 {"role": "user", "content": message, "timestamp": datetime.now(timezone.utc)},
                 {"role": "assistant", "content": full_response, "timestamp": datetime.now(timezone.utc)}
             ]
             await sessions_collection.update_one(
                 {"$or": [{"sessionId": session_id}, {"chat_id": session_id}]},
                 {
                     "$push": {"messages": {"$each": new_messages}},
                     "$set": {"last_updated": datetime.now(timezone.utc)}
                 }
             )
        except Exception as e:
            logger.error(f"Failed to update session history: {e}")
            
    # Add to Redis (Fast short-term context)
    await add_message_to_history(user_id, "user", message)
    await add_message_to_history(user_id, "assistant", full_response)

    # 🔒 THINKING METADATA (Append to end of stream)
    # This ensures "How I understood this" feature works for saved messages
    # Frontend filters this during streaming, but it's needed in final saved content
    yield f"\n\n<!--THINKING_DATA:{_thinking_metadata_json}-->"
        
    # 9️⃣ BACKGROUND LEARNING (Silent Observation)
    # Fire and forget: Analyze message + response for new facts/preferences
    # We do this AFTER yielding everything to keep latency low
    async def background_learning_task():
        try:
            # Only learn from high-value interactions
            if len(message) > 10 and len(full_response) > 20: 
                await extract_ongoing_insights(
                     user_id=user_id, 
                     message=message, 
                     ai_response=full_response
                 )
        except Exception as e:
            logger.error(f"Background learning failed: {e}")
            
    # Schedule background task
    asyncio.create_task(background_learning_task())


async def extract_ongoing_insights(user_id: str, message: str, ai_response: str = ""):
    """
    Background Task: Analyzes interaction for potential long-term memories.
    Uses Fast 8B Model to minimize cost/latency.
    """
    try:
        # Quick heuristic filter
        # We process more messages now because context (AI response) makes short answers meaningful ("Yes" -> "User confirms preference")
        if len(message) < 2: 
             return # Skip extremely short noise

        prompt = f"""
        Analyze this interaction and extract any new User Fact, Preference, or Relationship.
        Context:
        User: "{message}"
        AI: "{ai_response[:300]}..."
        
        Output JSON ONLY:
        {{
            "found": boolean,
            "type": "preference" | "fact" | "relationship",
            "content": "string summary"
        }}
        """
        
        raw_json = await get_llm_response(
            prompt=prompt, 
            system_prompt="You are a memory extraction system. Output strict JSON.",
            model="llama-3.1-8b-instant",
            timeout=10,
        )
        
        import json
        try:
            data = json.loads(raw_json)
            # Ensure data is a dict, not a list
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                logger.warning("[Silent Observation] Unexpected response type, skipping")
                return
                
            if data.get("found") and data.get("content"):
                mem_type_map = {
                    "preference": MemoryType.PREFERENCE,
                    "relationship": MemoryType.RELATIONSHIP,
                    "fact": MemoryType.SEMANTIC
                }
                mem_type = mem_type_map.get(data.get("type"), MemoryType.SEMANTIC)
                
                logger.info(f"🧠 [Silent Observation] Extracted {mem_type.value}: {data['content']}")
                await unified_memory_orchestrator.store_memory(
                    user_id=user_id,
                    memory_content=data["content"] if mem_type != MemoryType.RELATIONSHIP else ["DETECTED", data["content"]],
                    memory_type=mem_type,
                    metadata={"source": "silent_observation"}
                )
        except json.JSONDecodeError:
            logger.warning("[Silent Observation] Failed to parse JSON")
            
    except Exception as e:
        logger.warning(f"Silent observation failed: {e}")



