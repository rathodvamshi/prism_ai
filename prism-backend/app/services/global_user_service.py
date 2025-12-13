"""
🌍 Global User Profile Service
Manages historical user data that persists even after account deletion
"""

from datetime import datetime
from app.db.mongo_client import users_global_collection
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


async def add_user_to_global(user_data: dict) -> dict:
    """
    Add or update user in global collection when they sign up
    This data is preserved even if user deletes their account
    If user signs up again with same email, updates existing record instead of duplicating
    """
    try:
        user_id = str(user_data.get("_id", user_data.get("user_id")))
        email = user_data.get("email")
        
        if not email:
            raise ValueError("Email is required for global user record")
        
        # Check if user already exists in global collection
        existing_global_user = await users_global_collection.find_one({"email": email})
        
        if existing_global_user:
            # User is signing up again (returning user)
            logger.info(f"User {email} already exists in global collection - updating record")
            
            # Update existing record: mark as active again, add new signup timestamp
            update_data = {
                "userId": user_id,  # Update with new user ID
                "name": user_data.get("name", existing_global_user.get("name", "")),
                "profile": user_data.get("profile", existing_global_user.get("profile", {})),
                "deleted": False,  # Mark as active again
                "updated_at": datetime.now(),
                "last_signup": datetime.now()
            }
            
            # Add to signup history
            result = await users_global_collection.update_one(
                {"email": email},
                {
                    "$set": update_data,
                    "$push": {
                        "signup_history": {
                            "userId": user_id,
                            "timestamp": datetime.now(),
                            "type": "re-signup"
                        }
                    }
                }
            )
            
            logger.info(f"Updated existing global user record: {email}")
            return {"success": True, "user_id": user_id, "email": email, "returning_user": True}
        
        else:
            # New user - create first global record
            global_user_data = {
                "userId": user_id,
                "email": email,
                "name": user_data.get("name", ""),
                "profile": user_data.get("profile", {}),
                "created_at": user_data.get("created_at", datetime.now()),
                "updated_at": datetime.now(),
                "deleted": False,
                "deletion_history": [],
                "signup_history": [{
                    "userId": user_id,
                    "timestamp": datetime.now(),
                    "type": "first-signup"
                }],
                "first_seen": datetime.now()
            }
            
            # Insert new global user
            result = await users_global_collection.insert_one(global_user_data)
            
            logger.info(f"New user added to global collection: {email}")
            return {"success": True, "user_id": user_id, "email": email, "returning_user": False}
        
    except Exception as e:
        logger.error(f"Error adding user to global collection: {e}")
        raise


async def mark_user_deleted_in_global(user_id: str, email: str, deletion_reason: str = "user_requested") -> dict:
    """
    Mark user as deleted in global collection without removing the record
    Preserves user history for analytics and compliance
    """
    try:
        deletion_record = {
            "deleted_at": datetime.now(),
            "reason": deletion_reason,
            "user_id": user_id
        }
        
        result = await users_global_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "deleted": True,
                    "last_deletion": datetime.now(),
                    "updated_at": datetime.now()
                },
                "$push": {"deletion_history": deletion_record}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"User marked as deleted in global collection: {email}")
            return {"success": True, "marked_deleted": True}
        else:
            logger.warning(f"User not found in global collection: {email}")
            return {"success": False, "marked_deleted": False}
            
    except Exception as e:
        logger.error(f"Error marking user as deleted in global: {e}")
        raise


async def update_global_user_profile(email: str, profile_updates: dict) -> dict:
    """
    Update user profile data in global collection
    """
    try:
        result = await users_global_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "profile": profile_updates,
                    "updated_at": datetime.now()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Global user profile updated: {email}")
            return {"success": True, "updated": True}
        else:
            return {"success": False, "updated": False, "reason": "User not found"}
            
    except Exception as e:
        logger.error(f"Error updating global user profile: {e}")
        raise


async def get_global_user_stats() -> dict:
    """
    Get statistics about global users
    """
    try:
        total_users = await users_global_collection.count_documents({})
        active_users = await users_global_collection.count_documents({"deleted": False})
        deleted_users = await users_global_collection.count_documents({"deleted": True})
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "deleted_users": deleted_users
        }
        
    except Exception as e:
        logger.error(f"Error getting global user stats: {e}")
        return {"error": str(e)}
