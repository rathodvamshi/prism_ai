"""
🎬 YouTube Service - API Integration with Persistent Caching

Handles YouTube Data API v3 integration with:
- MongoDB persistent cache (30-day TTL) - survives restarts
- Redis hot cache (48-hour TTL) - fast access
- Fallback to scraper if API fails
- Auto-switch to redirect mode if quota exceeded
- Query normalization for better cache hits
- User media library integration

Performance: <5ms (MongoDB hit), <50ms (Redis hit), <500ms (API call)
Cost: 100 units per search (free tier = 10,000 units/day = 100 searches/day)
"""

import os
import logging
import hashlib
import json
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from app.models.media_models import YouTubeCacheEntry
from app.db.redis_client import redis_client

logger = logging.getLogger(__name__)


class YouTubeService:
    """
    YouTube integration with intelligent caching and fallback strategies.
    
    Cache Hierarchy:
    1. Redis (hot cache) - 48 hours TTL, fastest access
    2. MongoDB (persistent cache) - 30 days TTL, survives restarts
    3. YouTube API - when cache misses
    4. Scraper - fallback when API fails
    """
    
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.redis_cache_ttl = int(os.getenv("MEDIA_CACHE_TTL", "172800"))  # 48 hours
        self.mongo_cache_ttl_days = 30  # 30 days in MongoDB
        self.use_scraper_fallback = os.getenv("MEDIA_USE_SCRAPER_FALLBACK", "true").lower() == "true"
        self.quota_exceeded = False  # Flag to track if quota is exhausted
    
    async def get_video_id(self, search_query: str, user_id: Optional[str] = None) -> Optional[str]:
        """
        Get YouTube video ID for a search query.
        
        Strategy (Waterfall):
        1. Check Redis cache (hot, fast)
        2. Check MongoDB cache (persistent, medium)
        3. Try YouTube API (if not quota exceeded)
        4. Fall back to scraper
        5. Return None (will use redirect mode)
        
        Args:
            search_query: Normalized search query
            user_id: Optional user ID for personalization
        
        Returns:
            Video ID or None
        """
        try:
            # Step 1: Check Redis cache (hot cache)
            cached_id = await self._fetch_from_redis_cache(search_query)
            if cached_id:
                logger.info(f"✅ Redis Cache HIT for query: '{search_query[:30]}...'")
                return cached_id
            
            # Step 2: Check MongoDB cache (persistent cache)
            mongo_result = await self._fetch_from_mongo_cache(search_query)
            if mongo_result:
                video_id = mongo_result.get("video_id")
                if video_id:
                    logger.info(f"✅ MongoDB Cache HIT for query: '{search_query[:30]}...'")
                    # Warm up Redis cache for next time
                    await self._cache_to_redis(search_query, video_id)
                    return video_id
            
            logger.info(f"❌ Cache MISS for query: '{search_query[:30]}...'")
            
            # Step 3: Try API (if we have a key and quota not exceeded)
            if self.api_key and not self.quota_exceeded:
                video_data = await self._fetch_from_api_with_metadata(search_query)
                if video_data and video_data.get("video_id"):
                    video_id = video_data["video_id"]
                    # Cache the result in both Redis and MongoDB
                    await self._cache_video_data(search_query, video_data)
                    return video_id
            else:
                if not self.api_key:
                    logger.warning("⚠️ YouTube API Key (YOUTUBE_API_KEY) is missing. Skipping API.")
                elif self.quota_exceeded:
                    logger.warning("⚠️ YouTube API quota exceeded. Skipping API.")
            
            # Step 4: Try scraper fallback
            if self.use_scraper_fallback:
                video_id = await self._fetch_from_scraper(search_query)
                if video_id:
                    # Cache the result (basic metadata only)
                    await self._cache_video_data(search_query, {
                        "video_id": video_id,
                        "title": search_query.title(),
                        "source": "scraper"
                    })
                    return video_id
            
            # Step 5: No video ID found
            logger.warning(f"⚠️ Could not find video ID for: '{search_query}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ YouTube service error: {e}")
            return None
    
    async def _fetch_from_redis_cache(self, query: str) -> Optional[str]:
        """Fetch video ID from Redis (hot cache)."""
        try:
            cache_key = self._get_cache_key(query)
            data = await redis_client.get(cache_key)
            if data:
                try:
                    if data.startswith("{"):
                        entry = json.loads(data)
                        return entry.get("video_id")
                    else:
                        return data  # Plain string
                except:
                    return data if not data.startswith("{") else None
            return None
        except Exception as e:
            logger.error(f"❌ Redis cache error: {e}")
            return None
    
    async def _fetch_from_mongo_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch video data from MongoDB (persistent cache)."""
        try:
            from app.db.mongo_client import media_cache_collection
            
            normalized_query = self.normalize_query(query)
            
            # Find by normalized query
            result = await media_cache_collection.find_one({
                "normalized_query": normalized_query,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            if result:
                # Update hit count
                await media_cache_collection.update_one(
                    {"_id": result["_id"]},
                    {"$inc": {"hit_count": 1}, "$set": {"last_accessed": datetime.now(timezone.utc)}}
                )
                return result
            
            return None
        except Exception as e:
            logger.error(f"❌ MongoDB cache error: {e}")
            return None
    
    async def _cache_to_redis(self, query: str, video_id: str):
        """Cache video ID to Redis."""
        try:
            cache_key = self._get_cache_key(query)
            cache_entry = {
                "video_id": video_id,
                "query": query,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            await redis_client.setex(cache_key, self.redis_cache_ttl, json.dumps(cache_entry))
        except Exception as e:
            logger.error(f"❌ Redis cache write error: {e}")
    
    async def _cache_video_data(self, query: str, video_data: Dict[str, Any]):
        """Cache video data to both Redis and MongoDB."""
        video_id = video_data.get("video_id")
        if not video_id:
            return
        
        # 1. Cache to Redis (hot cache)
        await self._cache_to_redis(query, video_id)
        
        # 2. Cache to MongoDB (persistent cache)
        try:
            from app.db.mongo_client import media_cache_collection
            
            normalized_query = self.normalize_query(query)
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=self.mongo_cache_ttl_days)
            
            cache_doc = {
                "video_id": video_id,
                "query": query,
                "normalized_query": normalized_query,
                "title": video_data.get("title", query.title()),
                "channel": video_data.get("channel", ""),
                "thumbnail": video_data.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
                "duration": video_data.get("duration"),
                "description": video_data.get("description", ""),
                "source": video_data.get("source", "api"),
                "cached_at": now,
                "expires_at": expires_at,
                "last_accessed": now,
                "hit_count": 1
            }
            
            # Upsert - update if exists, insert if not
            await media_cache_collection.update_one(
                {"normalized_query": normalized_query},
                {"$set": cache_doc},
                upsert=True
            )
            
            logger.info(f"✅ Cached video to MongoDB: {video_id} for '{query[:30]}...'")
            
        except Exception as e:
            logger.error(f"❌ MongoDB cache write error: {e}")
    
    async def _fetch_from_api_with_metadata(self, search_query: str) -> Optional[Dict[str, Any]]:
        """
        Fetch BEST video from YouTube Data API v3 with full metadata.
        Returns dict with video_id, title, channel, thumbnail, etc.
        """
        try:
            import httpx
            
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "id,snippet",
                "q": search_query,
                "type": "video",
                "maxResults": 5,  # Scan top 5 for the best one
                "key": self.api_key,
                "videoEmbeddable": "true",
                "fields": "items(id(videoId),snippet(title,channelTitle,description,thumbnails))"
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 403:
                    logger.error("🚫 YouTube API quota exceeded - switching to redirect mode")
                    self.quota_exceeded = True
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                if items and len(items) > 0:
                    best_item = self._smart_select_video_with_metadata(items, search_query)
                    if best_item:
                        video_id = best_item["id"]["videoId"]
                        snippet = best_item["snippet"]
                        
                        # Get best thumbnail
                        thumbnails = snippet.get("thumbnails", {})
                        thumbnail = (
                            thumbnails.get("maxres", {}).get("url") or
                            thumbnails.get("high", {}).get("url") or
                            thumbnails.get("medium", {}).get("url") or
                            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                        )
                        
                        logger.info(f"✅ API selected BEST video: {video_id}")
                        return {
                            "video_id": video_id,
                            "title": snippet.get("title", search_query.title()),
                            "channel": snippet.get("channelTitle", ""),
                            "description": snippet.get("description", ""),
                            "thumbnail": thumbnail,
                            "source": "api"
                        }
                
                logger.warning(f"⚠️ API returned no results for: '{search_query}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ YouTube API error: {e}")
            return None
    
    def _smart_select_video_with_metadata(self, items: list, query: str) -> Optional[dict]:
        """
        Intelligently select the best video from a list of candidates.
        Returns the full item dict (not just ID).
        """
        best_item = None
        best_score = -1
        
        query_lower = query.lower()
        
        for item in items:
            title = item["snippet"]["title"].lower()
            channel = item["snippet"]["channelTitle"].lower()
            
            score = 0
            
            # CRITERIA 1: Official Sources (Huge Boost)
            if "vevo" in channel or "official" in channel or "topic" in channel:
                score += 50
            
            # CRITERIA 2: Title Keywords
            if "official video" in title or "official music video" in title:
                score += 40
            elif "official audio" in title or "official lyric" in title:
                score += 20
                
            # CRITERIA 3: Punish "Cover", "Live", "Remix" (unless requested)
            if "cover" in title and "cover" not in query_lower:
                score -= 30
            if "live" in title and "live" not in query_lower:
                score -= 20
            if "review" in title or "reaction" in title:
                score -= 50
                
            # CRITERIA 4: Relevance (First results are natively more relevant)
            score += (5 - items.index(item)) * 2
            
            if score > best_score:
                best_score = score
                best_item = item
                
        return best_item

    def _smart_select_video(self, items: list, query: str) -> str:
        """
        Intelligently select the best video from a list of candidates.
        """
        best_video = None
        best_score = -1
        
        query_lower = query.lower()
        
        for item in items:
            title = item["snippet"]["title"].lower()
            channel = item["snippet"]["channelTitle"].lower()
            desc = item["snippet"].get("description", "").lower()
            vid_id = item["id"]["videoId"]
            
            score = 0
            
            # CRITERIA 1: Official Sources (Huge Boost)
            if "vevo" in channel or "official" in channel or "topic" in channel:
                score += 50
            
            # CRITERIA 2: Title Keywords
            if "official video" in title or "official music video" in title:
                score += 40
            elif "official audio" in title or "official lyric" in title:
                score += 20 # Good, but video is better
                
            # CRITERIA 3: Punish "Cover", "Live", "Remix" (unless requested)
            if "cover" in title and "cover" not in query_lower:
                score -= 30
            if "live" in title and "live" not in query_lower:
                score -= 20
            if "review" in title or "reaction" in title:
                score -= 50
                
            # CRITERIA 4: Relevance (First results are natively more relevant)
            # We give a small decay based on position
            score += (5 - items.index(item)) * 2
            
            # Debug log
            logger.debug(f"🔍 Scored '{title}': {score}")
            
            if score > best_score:
                best_score = score
                best_video = vid_id
                
        return best_video
    
    async def _fetch_from_scraper(self, search_query: str) -> Optional[str]:
        """
        Fetch video ID using direct HTML scraping (Fallback).
        Replaces flaky 'youtubesearchpython' library which has dependency issues.
        
        Strategy:
        1. Access YouTube search results page via HTTP
        2. Regex extract video IDs from the embedded JSON
        """
        try:
            import httpx
            
            # Mimic a browser request to avoid immediate bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                     logger.warning(f"⚠️ Scraper HTTP {response.status_code} for: '{search_query}'")
                     return None
                
                html = response.text
                
                # Regex to find video IDs: look for "videoId":"..." pattern
                # This finds IDs inside the ytInitialData JSON blob
                video_ids = re.findall(r'"videoId":"([^"]{11})"', html)
                
                # Iterate and find first unique valid ID
                seen = set()
                for vid in video_ids:
                    if vid not in seen:
                        # Basic validation (11 chars standard)
                        if len(vid) == 11:
                            logger.info(f"✅ Scraper found video ID: {vid}")
                            return vid
                        seen.add(vid)
            
            logger.warning(f"⚠️ Scraper found no valid IDs for: '{search_query}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ Scraper error: {e}")
            return None
    
    async def _cache_video_id(self, query: str, video_id: str):
        """
        Cache video ID in Redis with metadata.
        """
        try:
            cache_key = self._get_cache_key(query)
            
            cache_entry = YouTubeCacheEntry(
                video_id=video_id,
                query=query,
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                cached_at=datetime.utcnow(),
                hit_count=1
            )
            
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_entry.dict(), default=str)
            )
            
            logger.info(f"✅ Cached video ID: {video_id} for query: '{query[:30]}...'")
        except Exception as e:
            logger.error(f"❌ Cache write error: {e}")
    
    def _get_cache_key(self, query: str) -> str:
        """
        Generate cache key from query.
        """
        query_normalized = self.normalize_query(query)
        if len(query_normalized) > 100:
            query_hash = hashlib.md5(query_normalized.encode()).hexdigest()[:16]
            return f"media:video:v3:{query_hash}"
        return f"media:video:v3:{query_normalized}"
    
    def normalize_query(self, query: str) -> str:
        """
        Normalize query for better cache hit rates.
        """
        normalized = query.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = normalized.replace('lo_fi', 'lofi')
        normalized = normalized.replace('lo_fi', 'lofi')
        return normalized
    
    def build_redirect_url(self, search_query: str) -> str:
        """
        Build YouTube search URL (redirect mode).
        """
        search_encoded = search_query.replace(' ', '+')
        return f"https://www.youtube.com/results?search_query={search_encoded}"
    
    def get_thumbnail_url(self, video_id: str, quality: str = "hqdefault") -> str:
        """
        Get YouTube thumbnail URL.
        """
        return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    
    def get_embed_url(self, video_id: str, autoplay: bool = True) -> str:
        """
        Get YouTube embed URL (for inline mode).
        """
        autoplay_param = "1" if autoplay else "0"
        return f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay={autoplay_param}"


# Global instance
youtube_service = YouTubeService()
