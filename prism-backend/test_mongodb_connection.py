#!/usr/bin/env python3
"""
🔍 MONGODB CONNECTION TESTER

Quick test script to verify MongoDB Atlas connection
Run this to debug connection issues before starting the main server
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import quote_plus

def encode_password_in_uri(uri: str) -> str:
    """
    URL-encode password in MongoDB URI to handle special characters
    """
    if '@' in uri and uri.count('@') > 1:
        # Find the credentials part
        parts = uri.split('@')
        if len(parts) >= 3:
            # mongodb+srv://user:pass@host becomes ['mongodb+srv://user:pass', 'host']
            protocol_user_pass = parts[0]
            host_parts = '@'.join(parts[1:])
            
            # Extract password from credentials
            if ':' in protocol_user_pass:
                protocol_user = protocol_user_pass.rsplit(':', 1)[0]
                raw_password = protocol_user_pass.rsplit(':', 1)[1]
                encoded_password = quote_plus(raw_password)
                return f"{protocol_user}:{encoded_password}@{host_parts}"
    
    return uri

async def test_mongodb_connection():
    """Test MongoDB Atlas connection with detailed error reporting"""
    
    print("🧪 MongoDB Connection Test Starting...")
    print("=" * 50)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("❌ No MONGO_URI found in environment")
        return False
    
    print(f"📍 Original URI: {mongo_uri[:50]}...")
    
    # Encode password if needed
    encoded_uri = encode_password_in_uri(mongo_uri)
    print(f"🔧 Using URI: {encoded_uri[:50]}...")
    
    try:
        print("\n🔌 Creating MongoDB client...")
        client = AsyncIOMotorClient(
            encoded_uri,
            serverSelectionTimeoutMS=10000,  # 10 seconds
            connectTimeoutMS=10000,
            socketTimeoutMS=5000,
            retryWrites=True,
            retryReads=True
        )
        
        print("📋 Testing basic connection...")
        # Test connection with timeout
        await asyncio.wait_for(client.admin.command('ping'), timeout=15)
        print("✅ Ping successful!")
        
        print("📊 Getting server info...")
        server_info = await client.admin.command('serverStatus')
        print(f"✅ Connected to MongoDB {server_info.get('version', 'Unknown')}")
        
        print("🗂️  Testing database operations...")
        db = client.prism_ai_dev
        
        # Test collection access
        test_collection = db.test_connection
        
        # Insert test document
        result = await test_collection.insert_one({"test": "connection", "timestamp": "now"})
        print(f"✅ Test document inserted: {result.inserted_id}")
        
        # Read test document
        doc = await test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Test document retrieved: {doc['test']}")
        
        # Clean up test document
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document cleaned up")
        
        # Test collections listing
        collections = await db.list_collection_names()
        print(f"📚 Available collections: {len(collections)}")
        for col in collections[:5]:  # Show first 5
            print(f"   - {col}")
        
        client.close()
        print("\n🎉 MongoDB connection test PASSED!")
        return True
        
    except asyncio.TimeoutError:
        print("❌ Connection timeout - check network and credentials")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        
        # Provide helpful debugging info
        if "authentication failed" in str(e).lower():
            print("💡 Check username and password in MONGO_URI")
        elif "network" in str(e).lower():
            print("💡 Check internet connection and MongoDB Atlas network access")
        elif "dns" in str(e).lower():
            print("💡 Check cluster URL and DNS resolution")
        
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_mongodb_connection())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)