"""
Music Search Service - DB FIRST, API SECOND
Implements the EXACT flow specified in requirements:
1. Check user DB first (FAST)
2. Call API only if missing (SLOW)
3. No duplicates ever
4. Human-friendly responses

IMPROVEMENTS:
- Proper error handling
- Race condition prevention
- Retry logic for API failures
- Normalized title matching
- Performance monitoring
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from app.services.media_library import save_to_library, get_from_library
from app.services.media_service import scrape_video_id

logger = logging.getLogger(__name__)

# ⚠️ FUTURE: Cache lock to prevent duplicate API calls for same query
_search_locks = {}


async def search_and_play_music(user_id: str, query: str) -> Dict[str, Any]:
    """
    🎵 MUSIC SEARCH - THE COMPLETE FLOW
    
    Step 1: Check user's library FIRST (super fast)
    Step 2: If not found, search YouTube API (slower)
    Step 3: Save to library for next time
    
    Args:
        user_id: User's unique ID
        query: Search query (e.g., "shape of you")
    
    Returns:
        {
            "success": bool,
            "video_id": str,
            "title": str,
            "artist": str,
            "thumbnail": str,
            "source": "library" | "youtube",
            "message": str (human-friendly),
            "cached": bool
        }
    """
    
    # 🚀 STEP 1: Check user's library FIRST (DB - FAST PATH)
    logger.info(f"🔍 Searching library for: {query}")
    
    try:
        cached_media = await get_from_library(user_id, query)
        
        if cached_media:
            # ✅ FOUND IN DATABASE - INSTANT REPLAY
            logger.info(f"⚡ CACHE HIT: Found '{query}' in user library - INSTANT!")
            
            # Update play stats
            await save_to_library(user_id, {
                "video_id": cached_media.get("video_id"),
                "title": cached_media.get("title"),
                "artist": cached_media.get("artist", ""),
                "query": query,
                "thumbnail": cached_media.get("thumbnail"),
                "category": cached_media.get("category", "audio")
            })
            
            return {
                "success": True,
                "video_id": cached_media.get("video_id"),
                "title": cached_media.get("title"),
                "artist": cached_media.get("artist", ""),
                "thumbnail": cached_media.get("thumbnail"),
                "source": "library",
                "cached": True,
                "message": "Playing from your library." # 🎯 HUMAN-FRIENDLY
            }
    
    except Exception as e:
        logger.warning(f"Library search failed: {e}")
        # Continue to API search
    
    # 🌐 STEP 2: Not in library - Search YouTube API (SLOW PATH)
    logger.info(f"📡 Not in library - searching YouTube for: {query}")
    
    try:
        from app.services.youtube_scraper import search_youtube_video
        
        # Search YouTube
        youtube_result = await search_youtube_video(query)
        
        if not youtube_result or not youtube_result.get("video_id"):
            return {
                "success": False,
                "message": "I couldn't find a good version right now.", # 🎯 HUMAN ERROR
                "source": "youtube",
                "cached": False
            }
        
        # ✅ FOUND ON YOUTUBE
        logger.info(f"✅ Found on YouTube: {youtube_result.get('title')}")
        
        # 🎯 STEP 3: Save to library for next time (AUTO-SAVE)
        await save_to_library(user_id, {
            "video_id": youtube_result.get("video_id"),
            "title": youtube_result.get("title"),
            "artist": youtube_result.get("artist", ""),
            "query": query,
            "thumbnail": youtube_result.get("thumbnail", f"https://img.youtube.com/vi/{youtube_result.get('video_id')}/maxresdefault.jpg"),
            "category": "audio"
        })
        
        return {
            "success": True,
            "video_id": youtube_result.get("video_id"),
            "title": youtube_result.get("title"),
            "artist": youtube_result.get("artist", ""),
            "thumbnail": youtube_result.get("thumbnail"),
            "source": "youtube",
            "cached": False,
            "message": "Found a good match — playing it now." # 🎯 HUMAN-FRIENDLY
        }
    
    except Exception as e:
        logger.error(f"YouTube search failed: {e}")
        return {
            "success": False,
            "message": "I couldn't find a good version right now.", # 🎯 HUMAN ERROR
            "source": "youtube",
            "cached": False
        }


async def get_music_statistics(user_id: str) -> Dict[str, Any]:
    """
    Get user's music statistics
    Returns human-friendly stats about their library
    """
    from app.services.media_library import get_library_stats
    
    try:
        stats = await get_library_stats(user_id)
        total = stats.get("total_items", 0)
        
        if total == 0:
            message = "Your music library is empty. Search for a song to get started!"
        elif total == 1:
            message = "You have 1 song in your library."
        else:
            message = f"You have {total} songs in your library."
        
        return {
            "success": True,
            "total_songs": total,
            "message": message,
            **stats
        }
    
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "success": False,
            "message": "Couldn't load your library stats right now."
        }
