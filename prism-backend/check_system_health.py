import asyncio
import os
import sys
import socket
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.db.redis_client import redis_client
from app.db.neo4j_client import neo4j_client
from app.db.neo4j_client import neo4j_client
# We need to import motor for MongoDB check if we want to do it raw, 
# or use the connection pool if available. 
# Let's use a simple motor client for the test to be independent.
from motor.motor_asyncio import AsyncIOMotorClient

async def check_dns(hostname):
    try:
        addr = socket.gethostbyname(hostname)
        return True, addr
    except Exception as e:
        return False, str(e)

async def check_redis():
    print(f"\n[1/4] 🔴 Checking Redis...")
    try:
        if await redis_client.ping():
            print("   ✅ Redis is CONNECTED and responding.")
            return True
        else:
            print("   ❌ Redis ping failed.")
            return False
    except Exception as e:
        print(f"   ❌ Redis connection error: {e}")
        return False

async def check_mongodb():
    print(f"\n[2/4] 🍃 Checking MongoDB...")
    uri = settings.MONGO_URI
    if not uri:
        print("   ❌ MONGO_URI is missing.")
        return False
    
    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
        # Force a connection
        await client.admin.command('ping')
        print("   ✅ MongoDB is CONNECTED and responding.")
        return True
    except Exception as e:
        print(f"   ❌ MongoDB connection error: {e}")
        return False

async def check_neo4j():
    print(f"\n[3/4] 🕸️ Checking Neo4j...")
    uri = settings.NEO4J_URI
    if not uri:
        print("   ❌ NEO4J_URI is missing.")
        return False
    
    # Extract hostname
    try:
        # uri format: neo4j+s://hostname:port or neo4j://hostname:port
        hostname = uri.split("://")[1].split(":")[0]
        print(f"   🔹 Resolving hostname: {hostname}")
        
        dns_ok, dns_result = await check_dns(hostname)
        if not dns_ok:
            print(f"   ❌ DNS Resolution Failed for '{hostname}': {dns_result}")
            print("      👉 Please check your NEO4J_URI in .env. The Instance ID is likely incorrect.")
            return False
        else:
            print(f"   ✅ DNS Resolved: {dns_result}")
            
    except Exception as e:
        print(f"   ⚠️ Could not parse URI for DNS check: {e}")

    # Now check actual driver
    if await neo4j_client.verify_connectivity():
        print("   ✅ Neo4j is CONNECTED and responding.")
        return True
    else:
        print("   ❌ Neo4j driver connectivity check failed.")
        return False

async def check_pinecone():
    print(f"\n[4/4] 🌲 Checking Pinecone...")
    # Vector memory service initializes on import/startup, let's check its status
    if not settings.PINECONE_API_KEY:
        print("   ⚠️ PINECONE_API_KEY is missing. Skipping.")
        return None
        
    try:
        # Import class locally to avoid circular imports or init issues
        from app.services.vector_memory_service import VectorMemoryService
        
        # Instantiate service (it connects in __init__)
        vm = VectorMemoryService()
        
        # The service has an 'index' attribute if connected
        if vm.index:
            stats = vm.index.describe_index_stats()
            print(f"   ✅ Pinecone is CONNECTED. Index stats: {stats}")
            return True
        else:
            print("   ❌ Pinecone index not accessible.")
            return False
    except Exception as e:
        print(f"   ❌ Pinecone error: {e}")
        return False

async def main():
    print("🏥 SYSTEM HEALTH CHECK")
    print("======================")
    
    results = {
        "redis": await check_redis(),
        "mongo": await check_mongodb(),
        "neo4j": await check_neo4j(),
        "pinecone": await check_pinecone()
    }
    
    print("\n📊 SUMMARY")
    print("==========")
    all_good = True
    for service, status in results.items():
        if status is True:
            icon = "✅"
        elif status is False:
            icon = "❌"
            all_good = False
        else:
            icon = "⚠️" # Skipped/Unknown
            
        print(f"{icon} {service.upper()}")
        
    if all_good:
        print("\n✨ ALL SYSTEMS OPERATIONAL")
    else:
        print("\n⚠️ SOME SYSTEMS ARE DOWN. The app will run, but with reduced functionality.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
