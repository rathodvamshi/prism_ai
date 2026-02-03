"""Debug script to check user profile data structure"""
import asyncio
import os
import sys

# Try loading env from multiple paths
env_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
    '.env'
]

for path in env_paths:
    if os.path.exists(path):
        from dotenv import load_dotenv
        load_dotenv(path)
        print(f"✅ Loaded env from: {path}")
        break

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

USER_ID = "6982054bb9c310ef60153fea"  # The user ID to check

async def main():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not found!")
        return
    
    # Parse database name from URI
    if "mongodb+srv://" in uri:
        parts = uri.split("/")
        if len(parts) >= 4:
            db_with_params = parts[3]
            db_name = db_with_params.split("?")[0]
        else:
            db_name = "prismdb"
    else:
        db_name = "prismdb"
    
    print(f"📊 Database: {db_name}")
    
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    
    users_collection = db["users"]
    
    try:
        user_obj_id = ObjectId(USER_ID)
        
        # Fetch the user document
        user = await users_collection.find_one({"_id": user_obj_id})
        
        if user:
            print("\n" + "="*60)
            print("📋 USER DOCUMENT STRUCTURE")
            print("="*60)
            
            for key, value in user.items():
                if key == "profile_picture" or key == "profilePicture":
                    # Truncate large base64 data
                    print(f"  {key}: <base64 image, length={len(str(value))}>")
                elif key == "profile" and isinstance(value, dict):
                    print(f"  {key}:")
                    for pk, pv in value.items():
                        if pk in ("profile_picture", "profilePicture"):
                            print(f"    {pk}: <base64 image>")
                        else:
                            print(f"    {pk}: {pv}")
                else:
                    print(f"  {key}: {value}")
            
            print("\n" + "="*60)
            print("🔑 KEY IDENTITY FIELDS")
            print("="*60)
            print(f"  name: {user.get('name', 'NOT SET')}")
            print(f"  nickname: {user.get('nickname', 'NOT SET')}")
            print(f"  age: {user.get('age', 'NOT SET')}")
            print(f"  occupation: {user.get('occupation', 'NOT SET')}")
            print(f"  location: {user.get('location', 'NOT SET')}")
            print(f"  city: {user.get('city', 'NOT SET')}")
            
            # Check nested profile
            profile = user.get('profile', {})
            if isinstance(profile, dict):
                print(f"\n  📍 Nested profile.location: {profile.get('location', 'NOT SET')}")
                print(f"  📍 Nested profile.city: {profile.get('city', 'NOT SET')}")
                print(f"  📍 Nested profile.state: {profile.get('state', 'NOT SET')}")
            
            print("\n" + "="*60)
            print("📝 INTERESTS & HOBBIES")
            print("="*60)
            print(f"  interests: {user.get('interests', [])}")
            print(f"  hobbies: {user.get('hobbies', [])}")
            
        else:
            print(f"❌ User {USER_ID} not found!")
            
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
