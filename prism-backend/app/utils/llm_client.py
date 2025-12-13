# Helper to return the LLM client (for sync/legacy code)
def get_llm_client():
    return client
from groq import AsyncGroq # <--- MUST be AsyncGroq
from app.config import settings

# Initialize the Async Client
client = AsyncGroq(
    api_key=settings.GROQ_API_KEY,
)

async def get_llm_response(prompt: str, system_prompt: str, image_url: str | None = None) -> str:
    """
    Sends a prompt to Groq. Supports text-only and vision via image_url.
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
            model_name = "llama-3.3-70b-versatile"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=model_name,
            temperature=0.8,  # Slightly higher for more creative, energetic responses
            max_tokens=2048,  # More tokens for detailed, warm responses
            top_p=0.95,      # Slight reduction for more focused responses
            stop=None,
            stream=False,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return "I'm having trouble seeing or thinking right now."

async def get_llm_response_stream(prompt: str, system_prompt: str, image_url: str | None = None):
    """
    Streams response from Groq in real-time chunks.
    Yields small text chunks (5-20 characters) for smooth UI updates.
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
            model_name = "llama-3.3-70b-versatile"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        stream = await client.chat.completions.create(
            messages=messages,
            model=model_name,
            temperature=0.8,
            max_tokens=2048,
            top_p=0.95,
            stop=None,
            stream=True,  # Enable streaming
        )
        
        # Stream chunks to frontend
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        print(f"LLM Streaming Error: {e}")
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