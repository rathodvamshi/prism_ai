"""Clear Redis queue keys for email worker"""
import asyncio
from app.db.redis_client import redis_client

async def clear_redis():
    keys_to_delete = [
        'email:queue:send',
        'email:rate:global',
    ]
    
    for key in keys_to_delete:
        await redis_client.delete(key)
        print(f"✅ Deleted: {key}")
    
    print("\n✅ Redis cleared - ready to start fresh")

if __name__ == "__main__":
    asyncio.run(clear_redis())
