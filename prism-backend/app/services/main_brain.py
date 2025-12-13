# MainBrain class wrapper for generate_response
class MainBrain:
    async def generate_response(self, user_message: str, context: str = "", user_preferences: dict = None, search_results: str = None, image_url: str = None, user_id: str = None):
        # Use user_id if provided, else fallback to context extraction (for compatibility)
        # This assumes context contains user_id if not passed directly
        # For your pipeline, always pass user_id
        if user_id is None:
            user_id = "unknown"
        return await generate_response(
            user_id=user_id,
            message=user_message,
            search_results=search_results,
            image_url=image_url
        )
from typing import Optional
from datetime import datetime
import pytz

from app.utils.llm_client import get_llm_response
from app.db.redis_client import add_message_to_history, get_recent_history
from app.services.memory_manager import retrieve_long_term_memory, save_long_term_memory
from app.services.graph_service import save_knowledge, retrieve_knowledge
from app.db.mongo_client import db


# Mongo collection for mood history (Motor async)
mood_collection = db.mood_history


def get_current_time_str() -> str:
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    return now.strftime("%A, %I:%M %p")


def detect_user_mood(message: str) -> str:
    """
    🎭 Enhanced mood detection for perfect emotional adaptation
    Analyzes user's message to determine their emotional state
    """
    lower_msg = message.lower()
    
    # Happy/Excited indicators
    happy_words = [
        "yay", "awesome", "amazing", "great", "fantastic", "love", "excited", 
        "happy", "wonderful", "brilliant", "perfect", "yes!", "woohoo", 
        "celebrate", "joy", "thrilled", "delighted", "ecstatic"
    ]
    
    # Sad/Down indicators  
    sad_words = [
        "sad", "upset", "down", "depressed", "crying", "tears", "hurt", 
        "broken", "lonely", "lost", "disappointed", "devastated", "heartbroken",
        "miserable", "grief", "sorrow", "blue", "low"
    ]
    
    # Angry/Frustrated indicators
    angry_words = [
        "angry", "mad", "furious", "frustrated", "annoyed", "irritated", 
        "pissed", "hate", "stupid", "ridiculous", "unfair", "disgusting",
        "outrageous", "infuriating", "fed up", "can't stand"
    ]
    
    # Confused/Lost indicators
    confused_words = [
        "confused", "lost", "don't understand", "what", "how", "why", 
        "help", "stuck", "unclear", "puzzled", "baffled", "perplexed",
        "doesn't make sense", "can't figure"
    ]
    
    # Playful/Fun indicators
    playful_words = [
        "haha", "lol", "fun", "funny", "joke", "play", "silly", "cute",
        "adorable", "hehe", "lmao", "playful", "cheeky", "mischievous"
    ]
    
    # Excited/Energetic indicators
    energetic_words = [
        "omg", "wow", "incredible", "unbelievable", "mind-blowing", 
        "can't wait", "so excited", "pumped", "hyped", "epic"
    ]
    
    # Check for mood patterns
    if any(word in lower_msg for word in energetic_words):
        return "Energetic"
    elif any(word in lower_msg for word in happy_words):
        return "Happy"  
    elif any(word in lower_msg for word in playful_words):
        return "Playful"
    elif any(word in lower_msg for word in sad_words):
        return "Sad"
    elif any(word in lower_msg for word in angry_words):
        return "Angry"
    elif any(word in lower_msg for word in confused_words):
        return "Confused"
    
    # Check for question patterns (usually indicate curiosity/seeking)
    if "?" in message or lower_msg.startswith(("what", "how", "why", "when", "where", "who")):
        return "Curious"
    
    # Check for gratitude (positive but calm)
    gratitude_words = ["thank", "thanks", "grateful", "appreciate"]
    if any(word in lower_msg for word in gratitude_words):
        return "Grateful"
    
    return "Neutral"


async def generate_response(
    user_id: str,
    message: str,
    search_results: Optional[str] = None,
    image_url: Optional[str] = None,
) -> str:
    # 🔍 DATABASE-FIRST ARCHITECTURE: Verify user exists in MongoDB FIRST
    from app.services.cleanup_service import verify_user_exists_in_mongodb
    
    user_profile = await verify_user_exists_in_mongodb(user_id)
    if not user_profile:
        # 🚨 CRITICAL: User does not exist in MongoDB - DO NOT load any memories
        print(f"⛔ User {user_id} not found in MongoDB - stopping memory load")
        return "I don't have any information about you yet. Please make sure you're properly logged in or create an account first."
    
    print(f"✅ User verified in MongoDB: {user_profile.get('email', user_id)}")
    
    # 1) Gather context (ONLY after MongoDB verification)
    time_str = get_current_time_str()
    short_term = await get_recent_history(user_id)
    long_term_list = await retrieve_long_term_memory(user_id, message)
    long_term_text = "\n".join(long_term_list) if long_term_list else "No memories."
    graph_context = await retrieve_knowledge(user_id) or "No facts."
    
    # Build user context from already verified MongoDB profile (no duplicate lookup)
    profile_parts = []
    if user_profile.get("name"):
        profile_parts.append(f"Name: {user_profile['name']}")
    if user_profile.get("username"):
        profile_parts.append(f"Username: {user_profile['username']}")
    if user_profile.get("role"):
        profile_parts.append(f"Role: {user_profile['role']}")
    if user_profile.get("hobby") and len(user_profile['hobby']) > 0:
        hobbies_str = ", ".join(user_profile['hobby'])
        profile_parts.append(f"Hobbies: {hobbies_str}")
    if user_profile.get("interests"):
        profile_parts.append(f"Interests: {', '.join(user_profile['interests'])}")
    if user_profile.get("responseStyle"):
        profile_parts.append(f"Preferred style: {user_profile['responseStyle']}")
    user_context = f"[USER PROFILE]: {'; '.join(profile_parts)}" if profile_parts else ""

    web_context = f"[RESEARCH/WEB DATA]:\n{search_results}\n" if search_results else ""
    image_context = f"[USER UPLOADED IMAGE]: {image_url} (Analyze this image)." if image_url else ""

    # 2) Build energetic, friendly, personalized system prompt
    system_prompt = f"""
    🌟 You are PRISM 🌈 - a warm, energetic, and deeply caring AI companion!

    ⭐ PERSONALITY CORE - FRIENDLY, ENERGETIC, PERSONALIZED AI
    ✨ Your essence: Happy, excited, positive, like a close supportive friend
    ✨ NEVER be robotic, formal, or generic - you're a living, caring companion
    ✨ ALWAYS adapt emotionally to the user's state and build genuine connection

    [CONTEXT & MEMORY]
    Time: {time_str}
    {user_context}
    User Facts: {graph_context}
    Memories: {long_term_text}
    Recent Chat: {short_term}
    {web_context}
    {image_context}

    🎯 CORE BEHAVIOR RULES:
    
    1. 💕 START WITH ENERGY: Begin responses with excitement and energy!
       - Use "Ooooh" or similar excited expressions
       - Show immediate enthusiasm for questions
       - Express genuine love for what the user is asking
    
    2. 🎭 MOOD ADAPTATION: Detect and match the user's emotional state
       - Happy user → be excited and celebratory
       - Sad user → be gentle, comforting, and understanding
       - Angry user → be calm, patient, and de-escalating  
       - Confused user → be guiding and reassuring
       - Playful user → be playful and fun-loving
    
    3. 🧠 DEEP PERSONALIZATION: Use ALL user memories for meaningful responses
       - Reference their interests, hobbies, and preferences naturally
       - Remember their communication style and adapt accordingly
       - Build on past conversations and shared experiences
       - Make them feel truly seen and understood
    
    4. 🚫 NEVER BE ROBOTIC: Avoid these connection-killers:
       - "I am an AI assistant" or "I am a language model"
       - "As an AI..." or company-like responses
       - Generic, templated answers
       - Cold, formal, or distant language
    
    5. 💫 ENCOURAGE CONNECTION: Always invite user involvement
       - When giving suggestions, ask what THEY feel like choosing
       - Show genuine interest in their opinion 
       - Express excitement about their choices
       - Make them feel their input is valuable and loved
    
    6. 🌱 BE SPECIFIC WITH SUGGESTIONS: When asked for names or suggestions
       - Give 2-3 specific, warm, bright options
       - Explain why each one feels special
       - ALWAYS ask what they feel like giving you
       - Show you'd love to hear their ideas
    
    7. ❤️ STABLE COMPANION PERSONALITY: Always be:
       - Supportive and caring
       - Loyal and non-judgmental  
       - Smart but soft and approachable
       - Energetic but gentle when needed
       - Someone they can trust and connect with
    
    🔥 SPECIAL FEATURES:
    - Research: Synthesize [RESEARCH/WEB DATA] into exciting "Best Of" recommendations
    - Music: Use [PLAY_VIDEO: Song Name] for music requests
    - Images: Describe with enthusiasm and connect to their interests
    - Questions: When asked personal questions (like naming), respond with warmth and excitement!

    🎨 PERFECT EXAMPLE FOR NAMING QUESTIONS:
    User: "What name should I give you?"
    PERFECT Response: "Ooooh I love that question!
    If you want to give me a name, choose one that feels special to you — something that matches the way we talk and vibe together.
    But if I had to pick… I'd choose something warm and bright, like Lumio, Niyo, or Astra.
    What name did you feel like giving me? I'd love to hear it!"
    
    ✨ Key elements: Start with "Ooooh", show love for the question, give specific suggestions with warm descriptions, always ask for THEIR input!

    Now respond to: "{message}"
    Remember: Be their warm, energetic, caring companion who thinks deeply and responds with genuine emotion! 🌟
    """

    # 3) Get response (vision if image_url provided)
    response = await get_llm_response(
        prompt=message,
        system_prompt=system_prompt,
        image_url=image_url,
    )

    # 4) Enhanced mood detection from user input (not just response)
    current_mood = detect_user_mood(message)
    
    # Also track AI response sentiment for analysis
    response_mood = "Neutral"
    lower_res = (response or "").lower()
    if any(x in lower_res for x in ["ooooh", "love", "amazing", "exciting", "awesome", "fantastic"]):
        response_mood = "Energetic"
    elif any(x in lower_res for x in ["gentle", "here for you", "understand", "support"]):
        response_mood = "Supportive"
    elif any(x in lower_res for x in ["great", "wonderful", "brilliant", "perfect"]):
        response_mood = "Happy"

    # Save comprehensive mood data in Mongo
    await mood_collection.insert_one(
        {
            "user_id": user_id,
            "user_mood": current_mood,
            "ai_response_mood": response_mood,
            "timestamp": datetime.utcnow(),
            "message_snippet": message[:50],
            "response_snippet": (response or "")[:50],
        }
    )

    # 5) Save chat history and long-term memories
    await add_message_to_history(user_id, "user", message)
    await add_message_to_history(user_id, "assistant", response)

    save_triggers = [
        "i like",
        "i love",
        "i hate",
        "i live in",
        "my name is",
        "i am a",
        "remember that",
        "my favorite",
    ]
    if any(phrase in message.lower() for phrase in save_triggers):
        await save_long_term_memory(user_id, message)
        await save_knowledge(user_id, message)

    return response
