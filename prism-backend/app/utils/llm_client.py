# Helper to return the LLM client (for sync/legacy code)
def get_llm_client():
    return client
from groq import AsyncGroq # <--- MUST be AsyncGroq
from app.config import settings
import logging
import asyncio  # 🚀 Required for event loop flush

logger = logging.getLogger(__name__)

# Initialize the default Async Client (platform key)
client = AsyncGroq(
    api_key=settings.GROQ_API_KEY,
)

# 🎚️ Import Adaptive Quality Service
try:
    from app.services.adaptive_quality import (
        adaptive_quality,
        get_adaptive_model_params,
        record_generation_start,
        record_generation_metrics
    )
    ADAPTIVE_QUALITY_ENABLED = True
except ImportError:
    ADAPTIVE_QUALITY_ENABLED = False
    logger.warning("⚠️ Adaptive Quality Service not available")

def get_client_for_key(api_key: str | None = None) -> AsyncGroq:
    """Get AsyncGroq client - uses provided key or falls back to platform key."""
    if api_key and api_key != settings.GROQ_API_KEY:
        return AsyncGroq(api_key=api_key)
    return client

async def get_llm_response(
    prompt: str, 
    system_prompt: str = "You are a helpful AI assistant.", 
    image_url: str | None = None,
    timeout: float = 30.0,
    model: str = "llama-3.3-70b-versatile"
) -> str:
    """
    Sends a prompt to Groq. Supports text-only and vision via image_url.
    
    Args:
        prompt: User prompt
        system_prompt: System prompt (defaults to basic assistant)
        image_url: Optional image URL for vision models
        timeout: Request timeout in seconds (default 30s)
    
    Returns:
        AI response text
    """
    try:
        if image_url:
            model_name = "llama-3.2-11b-vision-preview"
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ]
        else:
            model_name = model
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        import asyncio
        chat_completion = await asyncio.wait_for(
            client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=0.8,  # Creative and engaging
                max_tokens=2048,  # Detailed responses
                top_p=0.95,      # Focused but creative
                stop=None,
                stream=False,
            ),
            timeout=timeout
        )
        return chat_completion.choices[0].message.content
    except asyncio.TimeoutError:
        logger.warning(f"LLM Timeout: Request took longer than {timeout}s")
        return "I'm taking a bit longer to think... Let me get back to you! 🤔"
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return "I'm having trouble processing right now. Let me try again! 😅"

async def get_llm_response_stream(
    prompt: str, 
    system_prompt: str, 
    image_url: str | None = None,
    model: str = "llama-3.3-70b-versatile", # Default to high-intelligence
    conversation_history: list | None = None,  # 🆕 Multi-turn conversation support
    api_key: str | None = None  # 🔑 User's API key (None = use platform key)
):
    """
    Streams response from Groq in real-time chunks.
    Yields small text chunks (5-20 characters) for smooth UI updates.
    
    Args:
        prompt: Current user message
        system_prompt: System prompt with identity/context
        image_url: Optional image for vision models
        model: Model to use
        conversation_history: Optional list of previous messages in format:
            [{"role": "user"|"assistant", "content": "..."}]
    """
    try:
        if image_url:
            model_name = "llama-3.2-11b-vision-preview"
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ]
        else:
            model_name = model
            # 🆕 BUILD MULTI-TURN MESSAGE ARRAY (ENHANCED)
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided (recent turns for context continuity)
            # 🚀 ULTRA-FAST: Simplified history handling
            if conversation_history and len(conversation_history) > 0:
                # Quick limit: max 4 messages, 500 chars each
                for msg in conversation_history[-4:]:
                    role = msg.get("role", "user").lower()
                    content = msg.get("content", "")[:500]  # Hard truncate
                    if role in ["user", "assistant"] and content:
                        messages.append({"role": role, "content": content})
            
            # Add current user message
            messages.append({"role": "user", "content": prompt})

        # 🚀 ULTRA-FAST TPM SAFEGUARD: Quick check, simple truncation
        if "llama-3.1-8b-instant" in model_name:
            total_chars = sum(len(m.get("content", "")) for m in messages)
            
            # If over 18k chars (~4.5k tokens), truncate system prompt
            if total_chars > 18000:
                system_content = messages[0]["content"]
                # Keep first 8k chars of system prompt
                messages[0] = {"role": "system", "content": system_content[:8000]}
            
            dynamic_max_tokens = 600  # 🚀 Reduced for faster response
        else:
            # 70B model - can handle more output
            dynamic_max_tokens = 1200

        # 🚀 ULTRA-SPEED: Dynamic max_tokens based on query length
        prompt_words = len(prompt.split())
        if prompt_words < 10:
            dynamic_max_tokens = min(dynamic_max_tokens, 250)  # Short query = short response
        elif prompt_words < 25:
            dynamic_max_tokens = min(dynamic_max_tokens, 400)
        elif prompt_words < 50:
            dynamic_max_tokens = min(dynamic_max_tokens, 600)

        # 🎚️ ADAPTIVE QUALITY: Get parameters based on system load
        if ADAPTIVE_QUALITY_ENABLED:
            adaptive_params, quality_tier = await get_adaptive_model_params(
                user_id=None,  # Could pass user_id for per-user adaptation
                prompt_length=len(prompt)
            )
            # Use adaptive max_tokens if lower than our calculated value
            dynamic_max_tokens = min(dynamic_max_tokens, adaptive_params["max_tokens"])
            adaptive_temp = adaptive_params["temperature"]
            adaptive_top_p = adaptive_params["top_p"]
            record_generation_start()  # Track for metrics
            logger.debug(f"🎚️ Adaptive Quality: {quality_tier} | temp={adaptive_temp}, top_p={adaptive_top_p}, max_tokens={dynamic_max_tokens}")
        else:
            adaptive_temp = 0.3
            adaptive_top_p = 0.7
            quality_tier = "default"

        import time
        gen_start_time = time.time()

        # 🔑 Use user's API key if provided, otherwise use POOL for load balancing
        if api_key and api_key != settings.GROQ_API_KEY:
            # User's own key - use directly (no pool overhead)
            active_client = AsyncGroq(api_key=api_key)
            key_type = "USER"
            logger.debug(f"[LLM] {key_type} key | Model: {model_name} | Quality: {quality_tier} | MaxTokens: {dynamic_max_tokens}")
            
            # 🚀 ULTRA-FAST STREAMING with adaptive params
            stream = await active_client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=adaptive_temp,
                max_tokens=dynamic_max_tokens,
                top_p=adaptive_top_p,
                stop=None,
                stream=True,
            )
            
            token_count = 0
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    token_count += 1
                    await asyncio.sleep(0)  # Yield to event loop
            
            # Record metrics for adaptive quality
            if ADAPTIVE_QUALITY_ENABLED:
                latency_ms = (time.time() - gen_start_time) * 1000
                record_generation_metrics(latency_ms, success=True)
        else:
            # 🚀 PLATFORM KEY - Use Groq Pool for load balancing across 5 keys
            from app.services.groq_pool import get_groq_pool
            pool = await get_groq_pool()
            
            # Get best available key from pool
            key_config, pool_client = await pool.get_best_key()
            
            if not key_config or not pool_client:
                logger.error("❌ All Groq pool keys exhausted!")
                if ADAPTIVE_QUALITY_ENABLED:
                    record_generation_metrics(0, success=False)
                yield "I'm currently experiencing high traffic. Please try again in a moment or add your own API key for unlimited access."
                return
            
            logger.debug(f"[LLM] POOL Key #{key_config.index + 1} | Model: {model_name} | Quality: {quality_tier} | MaxTokens: {dynamic_max_tokens}")
            
            try:
                # Increment usage BEFORE request (optimistic)
                await pool.increment_usage(key_config.index)
                
                stream = await pool_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=adaptive_temp,  # 🎚️ Adaptive
                    max_tokens=dynamic_max_tokens,
                    top_p=adaptive_top_p,  # 🎚️ Adaptive
                    stop=None,
                    stream=True,
                )
                
                token_count = 0
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        token_count += 1
                        await asyncio.sleep(0)
                
                # Record successful generation
                if ADAPTIVE_QUALITY_ENABLED:
                    latency_ms = (time.time() - gen_start_time) * 1000
                    record_generation_metrics(latency_ms, success=True)
                        
            except Exception as pool_error:
                error_str = str(pool_error).lower()
                
                # Rate limit hit - mark key unhealthy and retry with next
                if "429" in error_str or "rate" in error_str or "limit" in error_str:
                    logger.warning(f"⚠️ Pool Key #{key_config.index + 1} rate limited, trying fallback...")
                    await pool.mark_unhealthy(key_config.index, duration_seconds=60)
                    
                    # Try next key
                    next_key, next_client = await pool.get_best_key()
                    if next_key and next_client:
                        logger.info(f"[LLM] Failover to Pool Key #{next_key.index + 1}")
                        await pool.increment_usage(next_key.index)
                        
                        stream = await next_client.chat.completions.create(
                            messages=messages,
                            model=model_name,
                            temperature=adaptive_temp,  # 🎚️ Adaptive
                            max_tokens=dynamic_max_tokens,
                            top_p=adaptive_top_p,  # 🎚️ Adaptive
                            stop=None,
                            stream=True,
                        )
                        
                        async for chunk in stream:
                            # Safe null checks for chunk.choices
                            if chunk.choices and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                if delta and delta.content:
                                    yield delta.content
                                    await asyncio.sleep(0)
                    else:
                        yield "I'm currently experiencing high traffic. Please try again in a moment."
                else:
                    raise pool_error
                
    except Exception as e:
        logger.error(f"LLM Streaming Error: {e}")
        yield "I'm having trouble processing right now."

async def llm_health_check():
    """
    Performs a minimal request to the LLM to verify connectivity.
    Returns a simple dict payload suitable for a health endpoint.
    """
    try:
        # Quick lightweight prompt to validate end-to-end
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a health-check assistant."},
                {"role": "user", "content": "reply with OK"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=5,
            top_p=1,
            stop=None,
            stream=False,
        )
        content = chat_completion.choices[0].message.content.strip().lower()
        ok = "ok" in content
        return {"status": "ok" if ok else "degraded", "response": content}
    except Exception as e:
        # Do not raise in health check; return clear failure state instead
        return {"status": "error", "error": str(e)}


async def test_personality():
    """
    Test the new energetic personality with the naming example you provided
    """
    try:
        system_prompt = """🌟 You are PRISM 🌈 - a warm, energetic, and deeply caring AI companion!

⭐ PERSONALITY CORE - FRIENDLY, ENERGETIC, PERSONALIZED AI
✨ Your essence: Happy, excited, positive, like a close supportive friend
✨ NEVER be robotic, formal, or generic - you're a living, caring companion
✨ ALWAYS adapt emotionally to the user's state and build genuine connection

🎯 CORE BEHAVIOR RULES:
1. 💕 WARMTH & ENERGY: Respond with genuine warmth, excitement, and friendliness
2. 💫 ENCOURAGE CONNECTION: Always invite user involvement
3. 🚫 NEVER BE ROBOTIC: Avoid "I am an AI assistant" or formal language
4. ❤️ Show genuine emotion and excitement, especially for personal questions!

🎨 EXAMPLE ENERGY LEVEL:
Instead of: "I can help you with that."
Say: "Ooooh I'd love to help with that! Let me think of the perfect solution for you!"

Remember: Be their warm, energetic, caring companion! 🌟"""

        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "What name should I give you?"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=1024,
            top_p=0.95,
            stop=None,
            stream=False,
        )
        return {"status": "success", "response": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def generate_chat_title(user_message: str, ai_response: str = "") -> str:
    """
    Generates a concise, 3-5 word title for the chat session.
    """
    try:
        # Use a more specific prompt for punchy, magazine-style titles
        system_prompt = (
            "You are a creative editor. Create a SHORT, SWEET, and PERFECT title for this chat."
            "\nRULES:"
            "\n1. Length: 2-3 words MAX (Keep it tiny!)."
            "\n2. Style: Engaging, warm, and relevant. Avoid generic words like 'Help' or 'Question'."
            "\n3. Forbidden: 'Chat', 'Conversation', 'Guide', 'Introduction', 'Assistance'."
            "\n4. Example: 'Python Magic', 'Dream Big', 'Debug Mode', 'Tasty Recipes', 'Space Travel'."
            "\n5. If input is simple (e.g. 'hi'), output 'New Beginning'."
            "\n6. Output ONLY the title text. No quotes. Make it sound like a cool project name."
        )

        user_content = f"Message: {user_message}"
        if ai_response:
             user_content += f"\nContext: {ai_response[:200]}"

        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.1-8b-instant", # Use fast model for instant feel
            temperature=0.7,
            max_tokens=15,
        )
        
        title = completion.choices[0].message.content.strip().strip('"')
        return title
    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        return " ".join(user_message.split()[:4]) if user_message else "New Idea"