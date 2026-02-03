"""
Media Library Service - Toggle Favorite Function
"""
from app.db.neo4j_client import get_neo4j_driver
import logging

logger = logging.getLogger(__name__)


async def toggle_favorite(user_id: str, video_id: str) -> bool:
    """
    Toggle favorite status for a media item
    
    Args:
        user_id: User's unique ID
        video_id: YouTube video ID
    
    Returns:
        New favorite status (True/False)
    """
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - cannot toggle favorite")
        return False
    
    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id, video_id: $video_id})
                SET m.is_favorite = NOT COALESCE(m.is_favorite, false)
                RETURN m.is_favorite as is_favorite
            """, {
                "user_id": user_id,
                "video_id": video_id
            })
            
            record = await result.single()
            if record:
                new_status = record["is_favorite"]
                logger.info(f"{'⭐ Favorited' if new_status else '💔 Unfavorited'}: {video_id}")
                return new_status
            return False
                
    except Exception as e:
        logger.error(f"❌ Failed to toggle favorite: {e}")
        return False
