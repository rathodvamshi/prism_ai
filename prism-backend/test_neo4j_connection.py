import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    print(f"🔍 Testing Neo4j Connection...")
    print(f"   URI: {uri}")
    print(f"   User: {user}")
    
    if not uri:
        print("❌ Error: NEO4J_URI is not set in .env")
        return

    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        print("⏳ Attempting to connect...")
        await driver.verify_connectivity()
        print("✅ Connected to Neo4j successfully!")
        await driver.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        if "getaddrinfo failed" in str(e):
            print("   👉 DNS Error: The Instance ID in your URI is likely incorrect.")

if __name__ == "__main__":
    asyncio.run(test_connection())
