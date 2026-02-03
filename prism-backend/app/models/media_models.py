"""
🎵 Media Play Feature - Data Models

Defines all data structures for the hybrid intent pipeline media play system.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class MediaEntities(BaseModel):
    """Extracted entities from user's media request"""
    query: str = Field(..., description="Main search query")
    artist: Optional[str] = Field(None, description="Artist name if mentioned")
    song_title: Optional[str] = Field(None, description="Song title if mentioned")
    media_type: Optional[Literal["song", "video", "music", "movie", "playlist", "unknown"]] = Field(
        None, description="Type of media requested"
    )
    language: Optional[str] = Field(None, description="Language preference (e.g., 'Telugu', 'English')")
    genre: Optional[str] = Field(None, description="Genre (e.g., 'melody', 'rock', 'lofi')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "shape of you",
                "artist": "ed sheeran",
                "song_title": "shape of you",
                "media_type": "song",
                "language": "english",
                "genre": None
            }
        }


class MediaIntent(BaseModel):
    """Complete media play intent with all metadata"""
    intent: Literal["media_play"] = "media_play"
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    action_mode: Literal["redirect", "inline"] = Field(
        "redirect", description="How to play the media"
    )
    entities: MediaEntities
    search_string: str = Field(..., description="Optimized search query for YouTube")
    detection_layer: Literal["regex", "nlp", "llm", "fallback"] = Field(
        "regex", description="Which layer detected the intent"
    )
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "media_play",
                "confidence": 0.95,
                "action_mode": "redirect",
                "entities": {
                    "query": "shape of you",
                    "artist": "ed sheeran",
                    "song_title": "shape of you",
                    "media_type": "song",
                    "language": "english"
                },
                "search_string": "shape of you ed sheeran official song",
                "detection_layer": "regex",
                "processing_time_ms": 0.8
            }
        }


class MediaResponse(BaseModel):
    """Response sent to frontend"""
    mode: Literal["link", "video"] = Field(
        ..., description="'link' for redirect, 'video' for inline"
    )
    url: Optional[str] = Field(None, description="Full URL for redirect mode")
    video_id: Optional[str] = Field(None, description="YouTube video ID for inline mode")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    message: str = Field(..., description="User-friendly message")
    query: str = Field(..., description="Original search query")
    cached: bool = Field(False, description="Whether result came from cache")
    cache_key: Optional[str] = Field(None, description="Cache key used")
    source: Literal["cache", "api", "scraper", "redirect", "fallback"] = Field(
        "redirect", description="Where the result came from"
    )
    execute_once: bool = Field(True, description="Whether frontend should auto-run this action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "link",
                "url": "https://www.youtube.com/results?search_query=shape+of+you+ed+sheeran",
                "message": "Opening 'Shape of You' on YouTube 🎵",
                "query": "shape of you",
                "cached": False,
                "source": "redirect"
            }
        }


class MediaPlayRequest(BaseModel):
    """Request to play media (for testing endpoint)"""
    query: str = Field(..., description="User's media request")
    mode: Optional[Literal["redirect", "inline"]] = Field(
        None, description="Preferred play mode (defaults to user settings)"
    )
    user_id: Optional[str] = Field(None, description="User ID for personalization")


class YouTubeCacheEntry(BaseModel):
    """Cached YouTube video data"""
    video_id: str
    query: str
    thumbnail_url: str
    title: Optional[str] = None
    cached_at: datetime = Field(default_factory=datetime.utcnow)
    hit_count: int = Field(default=0, description="Number of times this cache entry was used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "JGwWNGJdvx8",
                "query": "shape_of_you_ed_sheeran",
                "thumbnail_url": "https://img.youtube.com/vi/JGwWNGJdvx8/hqdefault.jpg",
                "title": "Ed Sheeran - Shape of You [Official Video]",
                "hit_count": 5
            }
        }
