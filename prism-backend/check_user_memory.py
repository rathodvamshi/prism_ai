"""
🔍 DEBUG SCRIPT: Check user memory data in MongoDB

This script checks what profile data exists for a user to diagnose
why memory recall might be failing.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
USER_ID = "6982054bb9c310ef60153fea"  # Replace with your user ID

async def check_user_memory():
    """Check all memory-related data for a user"""
    print(f"🔍 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.prismdb
    
    # Collections to check
    users_collection = db.users
    memory_collection = db.memory
    
    print(f"\n{'='*60}")
    print(f"🔍 CHECKING USER: {USER_ID}")
    print(f"{'='*60}")
    
    # 1. Check users_collection
    print(f"\n📋 USERS COLLECTION:")
    try:
        user_obj_id = ObjectId(USER_ID)
        user = await users_collection.find_one({"_id": user_obj_id})
        
        if user:
            print(f"  ✅ User found!")
            print(f"  📌 name: {user.get('name')}")
            print(f"  📌 email: {user.get('email')}")
            print(f"  📌 age: {user.get('age')}")
            print(f"  📌 occupation: {user.get('occupation')}")
            print(f"  📌 nickname: {user.get('nickname')}")
            print(f"  📌 interests: {user.get('interests')}")
            print(f"  📌 hobbies: {user.get('hobbies')}")
            print(f"  📌 profile: {user.get('profile')}")
            print(f"  📌 profile_updated_at: {user.get('profile_updated_at')}")
        else:
            print(f"  ❌ User NOT found in users collection!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 2. Check memory_collection
    print(f"\n📋 MEMORY COLLECTION:")
    try:
        memories = await memory_collection.find({"userId": USER_ID}).to_list(length=20)
        
        if memories:
            print(f"  ✅ Found {len(memories)} memory entries:")
            for i, mem in enumerate(memories):
                print(f"\n  [{i+1}] Memory Entry:")
                print(f"      type: {mem.get('type')}")
                print(f"      text/value: {mem.get('text') or mem.get('value')}")
                print(f"      category: {mem.get('category')}")
                print(f"      confidence: {mem.get('confidence')}")
                print(f"      created_at: {mem.get('created_at')}")
        else:
            print(f"  ℹ️ No entries in memory collection for this user")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Check complete!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_user_memory())
