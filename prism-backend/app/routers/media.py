"""
Media Library API Routes
Provides endpoints for user's personal media history/library.
Uses MongoDB for persistence (replaces Neo4j for simplicity).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.utils.auth import get_current_user_from_session

router = APIRouter(prefix="/api/media", tags=["media"])


class FavoriteToggle(BaseModel):
    video_id: str


class DeleteMedia(BaseModel):
    video_id: str


@router.get("/library")
async def get_library(
    limit: int = 50,
    category: Optional[str] = None,
    favorites_only: bool = False,
    current_user = Depends(get_current_user_from_session)
):
    """
    Get user's media library (newest first).
    Uses MongoDB user_media_library collection.
    """
    from app.services.media_service import get_user_media_history
    
    library = await get_user_media_history(
        user_id=current_user.user_id,
        limit=limit,
        favorites_only=favorites_only
    )
    
    # Filter by category if specified
    if category and category != 'all':
        library = [m for m in library if m.get('category') == category]
    
    return {"library": library, "count": len(library)}


@router.get("/library/search")
async def search_library(
    q: str,
    current_user = Depends(get_current_user_from_session)
):
    """Search user's media library by title/query."""
    from app.services.media_service import get_from_user_library
    
    result = await get_from_user_library(
        user_id=current_user.user_id,
        query=q
    )
    
    # Return as list for consistency
    results = [result] if result else []
    
    return {"results": results, "count": len(results)}


@router.post("/library/favorite")
async def toggle_favorite(
    data: FavoriteToggle,
    current_user = Depends(get_current_user_from_session)
):
    """Toggle favorite status for a media item."""
    from app.services.media_service import toggle_media_favorite
    
    new_status = await toggle_media_favorite(
        user_id=current_user.user_id,
        video_id=data.video_id
    )
    
    return {"video_id": data.video_id, "is_favorite": new_status}


@router.get("/library/stats")
async def get_stats(current_user = Depends(get_current_user_from_session)):
    """Get library statistics."""
    from app.services.media_service import get_user_media_history
    
    # Get all media for stats
    library = await get_user_media_history(
        user_id=current_user.user_id,
        limit=1000
    )
    
    total_count = len(library)
    favorites_count = sum(1 for m in library if m.get('is_favorite'))
    total_plays = sum(m.get('play_count', 0) for m in library)
    
    # Category breakdown
    categories = {}
    for m in library:
        cat = m.get('category', 'other')
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "total_media": total_count,
        "favorites": favorites_count,
        "total_plays": total_plays,
        "categories": categories
    }


@router.delete("/library")
async def delete_media(
    video_id: str,
    current_user = Depends(get_current_user_from_session)
):
    """Remove media from library."""
    from app.services.media_service import delete_from_user_library
    
    success = await delete_from_user_library(
        user_id=current_user.user_id,
        video_id=video_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return {"success": True, "video_id": video_id}
