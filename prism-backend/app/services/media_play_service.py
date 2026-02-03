"""
🎵 Media Play Service - Hybrid Intent Pipeline

3-Layer Architecture for speed and accuracy:
1. Layer 1: Regex (0-1ms, $0 cost) - Pattern matching
2. Layer 2: NLP (20-50ms, Low cost) - Entity extraction
3. Layer 3: LLM (800ms, Med cost) - Fallback for complex queries

Performance Target: <100ms for 90% of requests
Cost Target: <$0.01 per 100 requests
"""

import re
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from app.models.media_models import MediaIntent, MediaEntities, MediaResponse
from app.utils.llm_client import get_llm_response
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class MediaPlayService:
    """
    Hybrid intent pipeline for media play requests.
    Fast, accurate, and cost-effective media detection and processing.
    """
    
    # Regex patterns for Layer 1 - Ultra-fast matching
    TRIGGER_PATTERNS = [
        r"^(play|watch|listen to|listen|open)\s+(.+)",
        r"^(youtube|yt)\s+(.+)",
    ]
    
    # Strict Triggers for Inline Play (Must require explicit location)
    # Order matters: specific phrases first, generic words last
    INLINE_TRIGGERS = [
        "play here", "watch here", "listen here", "open here",
        "play in chat", "in chat", "play inside", "inside",
        "play this here", "play here only",
        " here", "here "  # Handle "play X here" and "here play X"
    ]
    
    # Entity extraction keywords for Layer 2
    MEDIA_TYPE_KEYWORDS = {
        "song": ["song", "track", "music", "tune", "melody"],
        "video": ["video", "clip", "vlog"],
        "movie": ["movie", "film", "cinema"],
        "playlist": ["playlist", "mix", "compilation"],
    }
    
    LANGUAGE_KEYWORDS = [
        "telugu", "hindi", "english", "tamil", "kannada", 
        "malayalam", "punjabi", "bengali", "marathi", "korean"
    ]
    
    GENRE_KEYWORDS = [
        "lofi", "lo-fi", "lo fi", "melody", "rock", "pop", 
        "jazz", "classical", "hip hop", "rap", "edm", "blues"
    ]
    
    def __init__(self):
        self.cache = cache_service
    
    async def process_media_request(
        self, 
        user_input: str, 
        mode: str = "redirect",
        user_id: Optional[str] = None
    ) -> MediaResponse:
        """
        Main entry point - processes media request through 3-layer pipeline.
        
        Args:
            user_input: User's message (e.g., "play shape of you")
            mode: "redirect" or "inline" (default passed from controller, but overridden by query)
            user_id: Optional user ID for personalization
        
        Returns:
            MediaResponse with video URL or ID
        """
        start_time = time.time()
        clean_input = user_input.lower().strip()
        
        # 1️⃣ INLINE VS REDIRECT MODE DETECTION (CRITICAL)
        # Default to redirect
        play_mode = "redirect"
        
        # Detect inline mode using substring/token matching
        # We check provided triggers. For single words like "here", strictly check boundaries if possible,
        # but our list includes space-padded versions to be safe (" here", "here ").
        for trigger in self.INLINE_TRIGGERS:
            if trigger in clean_input:
                play_mode = "inline"
                # Remove the location trigger to get the clean query
                clean_input = clean_input.replace(trigger, " ")
                # We continue checking? No, one trigger is enough.
                break
        
        # Clean up extra spaces
        clean_input = " ".join(clean_input.split())

        # Remove common command words to isolate the query
        # We perform this removal AFTER mode detection
        clean_input = re.sub(r"^(play|watch|listen to|listen|open)\s+", "", clean_input).strip()
        
        # If input became empty (e.g. user just said "play here"), provide a default fallback
        if not clean_input:
            clean_input = "trending music"

        user_input_for_search = clean_input
        
        try:
            # Layer 1: Regex detection
            intent = await self._layer1_regex_match(user_input_for_search)
            
            if not intent:
                # Layer 2: NLP entity extraction
                intent = await self._layer2_nlp_extract(user_input_for_search)
            
            if not intent or intent.confidence < 0.7:
                # Layer 3: LLM fallback
                intent = await self._layer3_llm_fallback(user_input_for_search)
            
            if not intent:
                # Fallback: Generic search
                intent = MediaIntent(
                    confidence=0.5,
                    action_mode=play_mode,
                    entities=MediaEntities(query=user_input_for_search),
                    search_string=user_input_for_search,
                    detection_layer="fallback"
                )
            
            # 2️⃣ FORCE MODE
            # We enforce the detected mode regardless of what layers thought
            intent.action_mode = play_mode
            
            # Calculate processing time
            intent.processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"🎵 Media intent detected: {intent.entities.query} | Mode: {play_mode} | "
                f"Layer: {intent.detection_layer} ({intent.processing_time_ms:.2f}ms)"
            )
            
            # 3️⃣ ACTION LOGIC & RESPONSE GENERATION
            response = await self._generate_media_response(intent, user_id=user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Media play service error: {e}")
            # Fallback to simple redirect
            return MediaResponse(
                mode="link",
                url=f"https://www.youtube.com/results?search_query={quote_plus(user_input)}",
                message=f"Opening '{user_input}' on YouTube 🎬",
                query=user_input,
                cached=False,
                source="fallback"
            )
    
    async def _layer1_regex_match(self, text: str) -> Optional[MediaIntent]:
        """Layer 1: Ultra-fast regex pattern matching (<1ms)"""
        text_lower = text.lower().strip()
        
        for pattern in self.TRIGGER_PATTERNS:
            match = re.match(pattern, text_lower, re.IGNORECASE)
            if match:
                query = match.group(2).strip()
                entities = MediaEntities(query=query)
                
                # Check for "X by Y" pattern
                artist_match = re.search(r"(.+?)\s+(by|from)\s+(.+)", query, re.IGNORECASE)
                if artist_match:
                    entities.song_title = artist_match.group(1).strip()
                    entities.artist = artist_match.group(3).strip()
                
                search_string = self.build_search_query(entities)
                
                return MediaIntent(
                    confidence=0.9,
                    action_mode="redirect", # Will be overridden
                    entities=entities,
                    search_string=search_string,
                    detection_layer="regex"
                )
        return None
    
    async def _layer2_nlp_extract(self, text: str) -> Optional[MediaIntent]:
        """Layer 2: NLP-based entity extraction (20-50ms)"""
        text_lower = text.lower().strip()
        entities = MediaEntities(query=text)
        confidence = 0.6
        
        # Extract media type
        for media_type, keywords in self.MEDIA_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                entities.media_type = media_type
                confidence += 0.1
                break
        
        # Extract language
        for lang in self.LANGUAGE_KEYWORDS:
            if lang in text_lower:
                entities.language = lang
                confidence += 0.1
                break
        
        # Extract genre
        for genre in self.GENRE_KEYWORDS:
            if genre in text_lower:
                entities.genre = genre
                confidence += 0.1
                break
        
        # Extract artist
        artist_match = re.search(r"\b(by|from)\s+([a-z0-9\s]+)", text_lower, re.IGNORECASE)
        if artist_match:
            entities.artist = artist_match.group(2).strip()
            confidence += 0.1
        
        if confidence > 0.6:
            search_string = self.build_search_query(entities)
            return MediaIntent(
                confidence=min(confidence, 0.95),
                action_mode="redirect",
                entities=entities,
                search_string=search_string,
                detection_layer="nlp"
            )
        return None
    
    async def _layer3_llm_fallback(self, text: str) -> Optional[MediaIntent]:
        """Layer 3: LLM-based smart extraction (~800ms)"""
        try:
            prompt = f"""Extract media information. Return ONLY JSON:
            Query: "{text}"
            Fields: query, artist, song_title, media_type, language, genre.
            """
            
            llm_response = await get_llm_response(prompt, system_prompt="Return valid JSON only.")
            
            import json
            try:
                extracted = json.loads(llm_response.strip())
                entities = MediaEntities(
                    query=extracted.get("query", text),
                    artist=extracted.get("artist"),
                    song_title=extracted.get("song_title"),
                    media_type=extracted.get("media_type"),
                    language=extracted.get("language"),
                    genre=extracted.get("genre")
                )
                search_string = self.build_search_query(entities)
                return MediaIntent(
                    confidence=0.85,
                    action_mode="redirect",
                    entities=entities,
                    search_string=search_string,
                    detection_layer="llm"
                )
            except Exception as e:
                logger.error(f"❌ LLM JSON parse error: {e}")
                return None
        except Exception as e:
            logger.error(f"❌ LLM request failed: {e}")
            return None
    
    def build_search_query(self, entities: MediaEntities) -> str:
        """
        Build YouTube search query.
        Rule: <query> <artist?> <language?> <media_type?>
        """
        parts = []
        
        # Main Query / Title
        if entities.song_title:
            parts.append(entities.song_title)
        else:
            parts.append(entities.query)
            
        # Artist
        if entities.artist:
            parts.append(entities.artist)
            
        # Language
        if entities.language:
            parts.append(entities.language)
            
        # Media Type (Modifiers)
        if entities.media_type:
            if entities.media_type == "song":
                parts.append("official song")
            elif entities.media_type == "video":
                parts.append("official video")
            elif entities.media_type == "movie":
                parts.append("full movie")
            elif entities.media_type == "playlist":
                parts.append("playlist")
            else:
                parts.append(entities.media_type)
        
        # Genre (if available and not already in query)
        if entities.genre and entities.genre.lower() not in " ".join(parts).lower():
            parts.append(entities.genre)
            
        # Join and clean
        return " ".join(filter(None, parts))
    
    async def _generate_media_response(self, intent: MediaIntent, user_id: Optional[str] = None) -> MediaResponse:
        """
        Generates the final response based on Mode (Inline vs Redirect)
        Also saves to user's media library for history.
        """
        from app.services.youtube_service import youtube_service
        from app.services.media_service import save_to_user_media_library
        import asyncio
        
        query_display = intent.entities.song_title or intent.entities.query
        
        # ▶️ CASE A: INLINE PLAY MODE
        if intent.action_mode == "inline":
            # 🛡️ Inline Playback Optimization
            # Official videos often have embedding disabled. We prefer "lyrics" or clean search for inline.
            # We modify the search string JUST for the ID lookup, preserving original for display.
            search_string_for_id = intent.search_string
            if "official" in search_string_for_id and "lyrics" not in search_string_for_id:
                 # Replace restrictive "official" terms with "lyrics" for better embed success
                 search_string_for_id = search_string_for_id.replace("official song", "lyrics").replace("official video", "lyrics")
            
            # If still generic, maybe append lyrics to ensure music match
            if "lyrics" not in search_string_for_id and intent.entities.media_type == "song":
                 search_string_for_id += " lyrics"

            # Search for actual video ID with optimized query
            video_id = await youtube_service.get_video_id(search_string_for_id)
            
            if video_id:
                # Success: Embed found
                message = f"Playing {query_display} here 🎶"
                if intent.entities.artist:
                    message = f"Playing {query_display} by {intent.entities.artist} here 🎶"
                
                # 🚀 AUTO-SAVE to user's library (fire and forget)
                if user_id:
                    asyncio.create_task(save_to_user_media_library(user_id, {
                        "video_id": video_id,
                        "title": query_display.title(),
                        "query": intent.entities.query,
                        "category": "audio" if intent.entities.media_type == "song" else "video"
                    }))
                    
                return MediaResponse(
                    mode="video",
                    url=f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1&rel=0",
                    video_id=video_id,
                    message=message,
                    query=intent.entities.query,
                    cached=True,
                    source="api",
                    execute_once=True
                )
            
            # Fallback if no video found: switch to Redirect
            logger.warning(f"⚠️ Video ID not found for inline request '{intent.search_string}'. Falling back to redirect.")
        
        # 🔁 CASE B: REDIRECT MODE (Default or Fallback)
        # First, try to get video_id for better UX and library storage
        video_id = None
        try:
            video_id = await youtube_service.get_video_id(intent.search_string)
        except Exception as e:
            logger.warning(f"⚠️ Failed to get video_id for redirect: {e}")
        
        if video_id:
            # We have a video_id - use direct watch URL instead of search
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # 🚀 AUTO-SAVE to user's library
            if user_id:
                asyncio.create_task(save_to_user_media_library(user_id, {
                    "video_id": video_id,
                    "title": query_display.title(),
                    "query": intent.entities.query,
                    "category": "audio" if intent.entities.media_type == "song" else "video"
                }))
            
            message = f"Opening {query_display} on YouTube 🎬"
            if intent.entities.artist:
                message = f"Opening {query_display} by {intent.entities.artist} on YouTube 🎬"
                
            return MediaResponse(
                mode="link",
                url=watch_url,
                video_id=video_id,
                message=message,
                query=intent.entities.query,
                cached=True,
                source="api",
                execute_once=True
            )
        
        # No video_id found - fallback to search URL
        encoded_query = quote_plus(intent.search_string)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        message = f"Opening {query_display} on YouTube 🎬"
        if intent.entities.artist:
            message = f"Opening {query_display} by {intent.entities.artist} on YouTube 🎬"
            
        return MediaResponse(
            mode="link",
            url=search_url,
            message=message,
            query=intent.entities.query,
            cached=False,
            source="redirect",
            execute_once=True
        )

    def normalize_query(self, query: str) -> str:
        """Normalize query for caching."""
        return re.sub(r'\s+', '_', re.sub(r'[^\w\s]', '', query.lower().strip()))


# Global instance
media_play_service = MediaPlayService()
