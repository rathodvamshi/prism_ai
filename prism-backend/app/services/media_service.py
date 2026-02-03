from pydantic import BaseModel
from typing import Literal, Optional, List, Dict, Any
import re
import random
import httpx
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- MODELS ---
class MediaResponse(BaseModel):
    mode: Literal['embed', 'redirect', 'clarification']
    display_message: str
    url: str
    query: str
    autoplay: bool = True
    confidence: float = 1.0
    video_id: Optional[str] = None  # NEW: for embed mode
    clarification_options: Optional[List[str]] = None  # NEW: for clarification mode

# --- CONFIGURATION ---

LANGUAGE_MAP = {
    # Languages
    "hindi": ["hindi", "bollywood"],
    "telugu": ["telugu", "tollywood"],
    "tamil": ["tamil", "kollywood"],
    "punjabi": ["punjabi", "bhangra"],
    "malayalam": ["malayalam", "mollywood"],
    "kannada": ["kannada", "sandalwood"],
    "korean": ["k-pop", "korean"],
    
    # Hindi transliterations
    "gane": "songs",
    "gana": "song",
    "gaane": "songs",
    "geet": "songs",
    "mera": "my",
    "tera": "your",
    "pyar": "love",
    
    # Telugu
    "paatalu": "songs",
    "paata": "song",
    "geethalu": "songs",
    "naa": "my",
    
    # Tamil
    "pattu": "song",
    "paadal": "song",
    "isai": "music",
    
    # Common
    "video": "video",
    "trailer": "trailer",
    "film": "movie",
    "cinema": "movie",
    
    # Artists
    "arijit": "arijit singh",
    "shreya": "shreya ghoshal",
    "ar rahman": "ar rahman",
}

# 2. Content Types & Context Rules
CONTENT_RULES = {
    "visual_high": ["trailer", "teaser", "scene", "clip", "short film", "movie clip", "official video", "lyric video", "lyrics video"],
    "audio_high": ["song", "songs", "music", "audio", "playlist", "album", "soundtrack", "ost", "lofi", "radio", "mix", "track", "singer", "artist"]
}

EXPLICIT_EMBED_TRIGGERS = [
    "here", "in chat", "inside", "embed", "play here", "inline", "in the chat",
    "show here", "watch here", "listen here", "right here", "in this chat", "playlist", "chat"
]

AMBIGUOUS_TERMS = {
    "gravity": ["movie by Alfonso Cuarón", "song by John Mayer", "scientific concept"],
    "titanic": ["1997 James Cameron movie", "documentary about the ship"],
    "inception": ["Christopher Nolan movie", "concept explanation"],
    "matrix": ["movie trilogy", "mathematics tutorial"],
    "avatar": ["James Cameron 2009 movie", "The Last Airbender series"],
}

RESPONSES = {
    "embed": [
        "Playing **{query}** right here. 🎬",
        "Here's **{query}** for you! ✨",
        "Embedding **{query}** now... 🍿"
    ],
    "redirect": [
        "Opening **{query}** on YouTube... 🚀",
        "Taking you to **{query}**... 🎵",
        "Launching **{query}** in a new tab! 🔎"
    ],
    "clarification": [
        "I found multiple matches for **{query}**. Which one?",
        "**{query}** could mean a few things. Can you clarify?"
    ]
}

# --- YOUTUBE SCRAPER ---

async def scrape_video_id(query: str) -> Optional[str]:
    """
    Lightweight async YouTube scraper.
    Extracts first video ID from search results.
    Returns None if fails.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://www.youtube.com/results",
                params={"search_query": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                follow_redirects=True
            )
            
        if response.status_code != 200:
            logger.warning(f"YouTube search returned {response.status_code}")
            return None
        
        # Method 1: Look for videoId in ytInitialData JSON
        pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
        match = re.search(pattern, response.text)
        
        if match:
            video_id = match.group(1)
            logger.info(f"✅ Scraped video ID: {video_id} for query: {query}")
            return video_id
        
        # Method 2: Fallback - look for /watch?v= links
        pattern2 = r'/watch\?v=([a-zA-Z0-9_-]{11})'
        match2 = re.search(pattern2, response.text)
        
        if match2:
            video_id = match2.group(1)
            logger.info(f"✅ Scraped video ID (method 2): {video_id} for query: {query}")
            return video_id
            
        logger.warning(f"❌ Could not extract video ID for: {query}")
        return None
        
    except httpx.TimeoutException:
        logger.error(f"⏱️ Scraper timeout for: {query}")
        return None
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        return None

# --- INTENT ANALYSIS ---

def clean_media_query(text: str) -> str:
    """
    Clean and normalize media query input.
    Removes stray quotes, punctuation, and normalizes whitespace.
    """
    import re
    
    # Remove stray quotes (single and double)
    text = text.replace('"', '').replace("'", '').replace('`', '')
    
    # Remove common punctuation that shouldn't be in search
    text = re.sub(r'[^\w\s\-]', ' ', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def analyze_intent(user_text: str):
    """Analyzes user input and returns structured analysis"""
    # 🧹 CLEAN INPUT FIRST - remove stray quotes and punctuation
    clean_text = clean_media_query(user_text.lower())
    
    # Detect explicit embed request
    explicit_mode = None
    for trigger in EXPLICIT_EMBED_TRIGGERS:
        if trigger in clean_text:
            explicit_mode = "embed"
            clean_text = clean_text.replace(trigger, "").strip()
            break
    
    # Normalize language
    words = clean_text.split()
    normalized_words = []
    
    for word in words:
        lower_word = word.lower()
        if lower_word in LANGUAGE_MAP:
            mapped = LANGUAGE_MAP[lower_word]
            if isinstance(mapped, str):
                normalized_words.append(mapped)
            else:
                normalized_words.append(word)
        else:
            normalized_words.append(word)
    
    normalized_query = " ".join(normalized_words)
    
    # C. Detect Content Type (Audio vs Visual) - CHECK AUDIO FIRST!
    content_type = "neutral"
    
    # First check for audio markers (songs should be detected early)
    for audio_term in CONTENT_RULES["audio_high"]:
        if audio_term in normalized_query:
            content_type = "audio"
            break
    
    # Only check visual if not already audio
    if content_type == "neutral":
        for visual_term in CONTENT_RULES["visual_high"]:
            if visual_term in normalized_query:
                content_type = "visual"
                break
    
    # D. Clean Noise Words
    noise_words = ["play", "watch", "listen to", "listen", "open", "can you", "please", "i want to", "show me", "find", "search"]
    final_query = normalized_query
    for noise in noise_words:
        final_query = final_query.replace(noise, "").strip()
    
    # E. Smart Content Type Fallback
    # If content_type is still neutral and query is short (likely a song name)
    # Default to "audio" (most media requests are music)
    if content_type == "neutral" and len(final_query.split()) <= 3:
        content_type = "audio"  # Assume song/music
        logger.info(f"💡 Defaulting to audio for short query: '{final_query}'")
    
    # Confidence scoring
    confidence = 1.0
    ambiguity_options = None
    
    query_words = final_query.lower().split()
    for word in query_words:
        if word in AMBIGUOUS_TERMS:
            confidence = 0.3
            ambiguity_options = AMBIGUOUS_TERMS[word]
            break
    
    if len(final_query.split()) <= 1 and content_type == "neutral":
        confidence *= 0.6
    
    if explicit_mode or content_type != "neutral":
        confidence = min(1.0, confidence + 0.3)
    
    if not final_query or len(final_query.strip()) == 0:
        final_query = "trending music"
        confidence = 0.7
    
    logger.info(f"🧠 INTENT ANALYSIS: query='{final_query}', content_type={content_type}, explicit_mode={explicit_mode}, confidence={confidence}")
    
    return {
        "query": final_query,
        "explicit_mode": explicit_mode,
        "content_type": content_type,
        "confidence": confidence,
        "ambiguity_options": ambiguity_options
    }

def decide_mode(analysis: dict) -> str:
    """
    Decides embed vs redirect based on analysis.
    
    LOGIC:
    1. User says "here" → EMBED (highest priority)
    2. Visual content (trailer) → EMBED  
    3. Audio content (song) → REDIRECT (default for music)
    4. Default → REDIRECT
    """
    # 1. Explicit user override (highest priority) -> Only way to get EMBED mode
    if analysis["explicit_mode"] == "embed":
        logger.info("🎯 Mode: EMBED (explicit trigger detected)")
        return "embed"
    
    # 2. DEFAULT to REDIRECT for everything else
    # Even trailers/visuals should open in new tab unless user says "play here"
    logger.info("🎯 Mode: REDIRECT (default rule)")
    return "redirect"

def generate_friendly_response(query: str, mode: str) -> str:
    """Generates concierge-style response"""
    template = random.choice(RESPONSES[mode])
    return template.format(query=query.title())

def generate_suggestions(query: str, content_type: str) -> List[str]:
    """Generate contextual suggestions based on content type"""
    if content_type == "audio":
        return [
            "Play more songs",
            "Show similar artists",
            "Create playlist"
        ]
    elif content_type == "visual":
        return [
            "Play full version",
            "Show similar videos",
            "Watch related content"
        ]
    else:
        return [
            "Play something else",
            "Refine search",
            "Try different genre"
        ]

# --- MAIN ENTRY POINT ---

async def save_to_user_media_library(user_id: str, video_data: Dict[str, Any]) -> bool:
    """
    Save played media to user's personal library in MongoDB.
    Deduplicates by (user_id, video_id) - one entry per user per video.
    Updates play_count on repeat plays.
    """
    if not user_id or not video_data.get("video_id"):
        return False
    
    try:
        from app.db.mongo_client import user_media_library_collection
        
        video_id = video_data["video_id"]
        now = datetime.now(timezone.utc)
        
        # Upsert: insert if new, update play_count if exists
        result = await user_media_library_collection.update_one(
            {"user_id": user_id, "video_id": video_id},
            {
                "$set": {
                    "title": video_data.get("title", ""),
                    "query": video_data.get("query", ""),
                    "thumbnail": video_data.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
                    "channel": video_data.get("channel", ""),
                    "category": video_data.get("category", "audio"),
                    "last_played_at": now,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "video_id": video_id,
                    "is_favorite": False,
                    "added_at": now
                },
                "$inc": {"play_count": 1}
            },
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"✅ New media added to library: {video_id} for user {user_id[:8]}...")
        else:
            logger.info(f"✅ Media play count updated: {video_id} for user {user_id[:8]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save to user library: {e}")
        return False


async def get_from_user_library(user_id: str, query: str) -> Optional[Dict[str, Any]]:
    """
    Check if user has played media matching this query before.
    Returns cached video if found (instant, no API needed).
    
    Search priority:
    1. Exact video_id match
    2. Title contains query
    3. Query field matches
    """
    if not user_id:
        return None
    
    try:
        from app.db.mongo_client import user_media_library_collection
        
        normalized_query = query.lower().strip()
        
        # Try to find in user's library
        # First, try title search (most common)
        result = await user_media_library_collection.find_one({
            "user_id": user_id,
            "$or": [
                {"title": {"$regex": normalized_query, "$options": "i"}},
                {"query": {"$regex": normalized_query, "$options": "i"}}
            ]
        }, sort=[("play_count", -1)])  # Prefer most played
        
        if result:
            logger.info(f"⚡ User library HIT: {result.get('title')} (plays: {result.get('play_count', 0)})")
            return {
                "video_id": result["video_id"],
                "title": result.get("title", query),
                "thumbnail": result.get("thumbnail"),
                "channel": result.get("channel"),
                "play_count": result.get("play_count", 1),
                "is_favorite": result.get("is_favorite", False)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ User library lookup error: {e}")
        return None


async def process_media_request(query: str, user_id: Optional[str] = None) -> MediaResponse:
    """
    Main entry point for media requests.
    
    Flow:
    1. Check user's personal library (instant if found)
    2. Check global MongoDB cache (fast if found)
    3. Analyze intent & decide mode
    4. Fetch from YouTube API/Scraper
    5. Auto-save to user library (async, non-blocking)
    """
    # 🧹 CLEAN QUERY FIRST - remove stray quotes and normalize
    query = clean_media_query(query)
    
    logger.info(f"🎬 MEDIA REQUEST: '{query}' (user: {user_id})")
    
    # STEP 0: Check user's personal library first (INSTANT if found)
    if user_id:
        try:
            cached_media = await get_from_user_library(user_id, query)
            
            if cached_media and cached_media.get("video_id"):
                video_id = cached_media['video_id']
                title = cached_media.get('title', query)
                
                logger.info(f"⚡ USER LIBRARY HIT: {title} - Skipping API!")
                
                # Update play count (fire and forget)
                asyncio.create_task(save_to_user_media_library(user_id, {
                    "video_id": video_id,
                    "title": title,
                    "query": query,
                    "thumbnail": cached_media.get("thumbnail"),
                    "channel": cached_media.get("channel")
                }))
                
                # Return instantly from library
                return MediaResponse(
                    mode="redirect",
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    display_message=f"Playing **{title}** from your library! 🎵",
                    query=query,
                    autoplay=False,
                    confidence=1.0,
                    video_id=video_id
                )
        except Exception as e:
            logger.warning(f"Library check failed (continuing with API): {e}")
    
    # STEP 1: Analyze intent
    analysis = analyze_intent(query)
    
    # 2. Check for ambiguity
    if analysis["confidence"] < 0.5 and analysis["ambiguity_options"]:
        return MediaResponse(
            mode="clarification",
            url="",
            display_message=f"I found multiple matches for **{analysis['query']}**. Which one did you mean?",
            query=analysis['query'],
            autoplay=False,
            confidence=analysis["confidence"],
            clarification_options=analysis["ambiguity_options"]
        )
    
    # 3. Decide mode
    mode = decide_mode(analysis)
    logger.info(f"🎯 MODE DECISION: {mode} (content_type={analysis['content_type']}, explicit={analysis['explicit_mode']})")
    final_query = analysis["query"]
    
    # 4. FETCH VIDEO ID (Using Robust Service)
    # This handles Cache -> API -> Scraper waterfall
    from app.services.youtube_service import youtube_service
    video_id = await youtube_service.get_video_id(final_query)

    # 5. DECISION LOGIC (Embed vs Redirect)
    # If explicit "in chat" request -> Force EMBED if we have an ID
    if mode == "embed":
         if video_id:
            # SUCCESS: Embed with video ID
            # NOTE: We use the WATCH URL (standard) so ReactPlayer can handle embedding/cookies correctly
            return MediaResponse(
                mode="embed",
                url=f"https://www.youtube.com/watch?v={video_id}",
                display_message=generate_friendly_response(final_query, "embed"),
                query=final_query,
                autoplay=True,
                confidence=analysis["confidence"],
                video_id=video_id,
                clarification_options=generate_suggestions(final_query, analysis["content_type"]) # Pass suggestions here if needed
            )
         else:
             # FAIL: Explicit embed requested but no ID found -> Fallback to redirect search
             logger.warning(f"⚠️ Embed requested but ID not found for: {final_query}")
             mode = "redirect"

    # 6. REDIRECT LOGIC (Default or Fallback)
    if mode == "redirect":
        if video_id:
            # SUCCESS: Direct video link
            logger.info(f"📤 REDIRECT MODE: video_id={video_id}")
            
            # 🚀 AUTO-SAVE to user's library (fire and forget - non-blocking)
            if user_id:
                asyncio.create_task(save_to_user_media_library(user_id, {
                    "video_id": video_id,
                    "title": final_query.title(),
                    "query": final_query,
                    "category": analysis.get("content_type", "audio")
                }))
            
            return MediaResponse(
                mode="redirect",
                url=f"https://www.youtube.com/watch?v={video_id}",
                display_message=f"Opening **{final_query.title()}** on YouTube... 🎵",
                query=final_query,
                autoplay=False,
                confidence=analysis["confidence"],
                video_id=video_id
            )
        else:
             # FALLBACK: General Search Results
            logger.info(f"📤 FALLBACK MODE: search_query={final_query}")
            return MediaResponse(
                mode="redirect",
                url=f"https://www.youtube.com/results?search_query={final_query}",
                display_message=f"Here are the search results for **{final_query.title()}** 🔎",
                query=final_query,
                autoplay=False,
                confidence=analysis["confidence"]
            )


# --- USER MEDIA LIBRARY API HELPERS ---

async def get_user_media_history(user_id: str, limit: int = 50, favorites_only: bool = False) -> List[Dict[str, Any]]:
    """
    Get user's media library/history.
    Returns list of played media sorted by last_played_at (newest first).
    """
    if not user_id:
        return []
    
    try:
        from app.db.mongo_client import user_media_library_collection
        
        query_filter = {"user_id": user_id}
        if favorites_only:
            query_filter["is_favorite"] = True
        
        cursor = user_media_library_collection.find(
            query_filter,
            {"_id": 0, "user_id": 0}  # Exclude these fields
        ).sort("last_played_at", -1).limit(limit)
        
        results = await cursor.to_list(length=limit)
        
        # Format dates and field names for frontend
        for item in results:
            if "last_played_at" in item:
                item["last_played"] = item["last_played_at"].isoformat() if item["last_played_at"] else None
            if "added_at" in item:
                item["added_at"] = item["added_at"].isoformat() if item["added_at"] else None
            # Map play_count to plays for frontend compatibility
            if "play_count" in item:
                item["plays"] = item["play_count"]
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Failed to get user media history: {e}")
        return []


async def toggle_media_favorite(user_id: str, video_id: str) -> bool:
    """Toggle favorite status for a media item. Returns new favorite status."""
    if not user_id or not video_id:
        return False
    
    try:
        from app.db.mongo_client import user_media_library_collection
        
        # Get current status
        item = await user_media_library_collection.find_one(
            {"user_id": user_id, "video_id": video_id}
        )
        
        if not item:
            return False
        
        new_status = not item.get("is_favorite", False)
        
        await user_media_library_collection.update_one(
            {"user_id": user_id, "video_id": video_id},
            {"$set": {"is_favorite": new_status, "updated_at": datetime.now(timezone.utc)}}
        )
        
        return new_status
        
    except Exception as e:
        logger.error(f"❌ Failed to toggle favorite: {e}")
        return False


async def delete_from_user_library(user_id: str, video_id: str) -> bool:
    """Delete a media item from user's library."""
    if not user_id or not video_id:
        return False
    
    try:
        from app.db.mongo_client import user_media_library_collection
        
        result = await user_media_library_collection.delete_one(
            {"user_id": user_id, "video_id": video_id}
        )
        
        return result.deleted_count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to delete from library: {e}")
        return False


# Synchronous wrapper for compatibility
def process_media_request_sync(user_text: str) -> MediaResponse:
    """Sync wrapper - runs async scraper in event loop"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - create task
            return asyncio.create_task(process_media_request(user_text))
        else:
            return loop.run_until_complete(process_media_request(user_text))
    except:
        # Fallback: if async fails, just do redirect
        analysis = analyze_intent(user_text)
        return MediaResponse(
            mode="redirect",
            url=f"https://www.youtube.com/results?search_query={analysis['query']}",
            display_message=generate_friendly_response(analysis['query'], "redirect"),
            query=analysis['query'],
            autoplay=False
        )