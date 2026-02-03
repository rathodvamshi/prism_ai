import asyncio
from app.db.redis_client import redis_client
from app.config import settings

async def clear_locks():
    print("🚀 Connecting to Redis...")
    # Initialize the client pool
    await redis_client.ping()
    print("✅ Connected.")

    # Find all active generation keys
    keys = await redis_client.keys("active_generation:*")
    count = len(keys)
    
    if count == 0:
        print("✅ No active locks found. System is clean.")
    else:
        print(f"⚠️ Found {count} stuck locks. Clearing them...")
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            await redis_client.delete(key)
            print(f"   - Deleted {key}")
        print("✅ All locks cleared.")

    # Also clear any orphaned generations just in case
    gen_keys = await redis_client.keys("generation:*")
    # We won't delete all generations, just the ones that are likely stuck, but simplest is to just clear active locks for now.
    
    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(clear_locks())
