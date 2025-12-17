"""
Simple Neo4j Authentication Test
Tests if credentials are correct and database is accessible
"""

from neo4j import GraphDatabase
import sys

# Connection details
URI = "neo4j+s://46945710.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "AtNi7QOzQAc5zKA2HtFCAoIJN2YWyHGi_3BnpppsfvU"

print("\n" + "="*60)
print("🔐 Neo4j Authentication & Database Test")
print("="*60)

print(f"\n📍 Connecting to: {URI}")
print(f"👤 User: {USER}")

try:
    # Create driver with explicit settings
    driver = GraphDatabase.driver(
        URI,
        auth=(USER, PASSWORD),
        connection_timeout=30,
        max_connection_lifetime=3600
    )
    
    print("\n1️⃣ Testing driver creation...")
    print("✅ Driver created successfully")
    
    print("\n2️⃣ Verifying connectivity...")
    driver.verify_connectivity()
    print("✅ Connectivity verified!")
    
    print("\n3️⃣ Running test query...")
    with driver.session() as session:
        result = session.run("RETURN 'Hello Neo4j!' AS message, datetime() AS time")
        record = result.single()
        print(f"✅ Query successful!")
        print(f"   Message: {record['message']}")
        print(f"   Server time: {record['time']}")
    
    print("\n4️⃣ Testing database info...")
    with driver.session() as session:
        result = session.run("CALL dbms.components() YIELD name, versions, edition")
        for record in result:
            print(f"✅ Database info:")
            print(f"   Name: {record['name']}")
            print(f"   Version: {record['versions']}")
            print(f"   Edition: {record['edition']}")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("Neo4j Aura connection is working correctly!")
    print("="*60)
    
    driver.close()
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ CONNECTION FAILED!")
    print(f"Error: {e}")
    print("\n" + "="*60)
    print("💡 TROUBLESHOOTING STEPS:")
    print("="*60)
    
    error_str = str(e).lower()
    
    if "authentication" in error_str or "unauthorized" in error_str:
        print("\n🔐 AUTHENTICATION ERROR")
        print("   ❌ Username or password is incorrect")
        print("   ✅ Fix:")
        print("      1. Go to https://console.neo4j.io/")
        print("      2. Select your database")
        print("      3. Go to 'Access' or 'Connection' tab")
        print("      4. Reset password and update .env file")
        
    elif "routing" in error_str or "unable to retrieve" in error_str:
        print("\n🗺️ ROUTING INFORMATION ERROR")
        print("   ❌ Can't access database routing table")
        print("   ✅ Possible causes:")
        print("      1. Database is PAUSED or STOPPED")
        print("      2. Your IP is not whitelisted")
        print("      3. Database doesn't exist at this URI")
        print("\n   ✅ Fixes:")
        print("      1. Check database status: https://console.neo4j.io/")
        print("      2. Resume database if paused")
        print("      3. Whitelist IP: Add 0.0.0.0/0 in IP Allowlist")
        print("      4. Verify database ID in URI is correct")
        
    elif "connection" in error_str or "timeout" in error_str:
        print("\n🌐 NETWORK/FIREWALL ERROR")
        print("   ❌ Can't establish connection")
        print("   ✅ Fix:")
        print("      1. Check Windows Firewall")
        print("      2. Try different network")
        print("      3. Contact IT if on corporate network")
        
    else:
        print(f"\n❓ UNKNOWN ERROR")
        print(f"   Full error: {e}")
        print(f"\n   ✅ General fixes:")
        print(f"      1. Verify database is running")
        print(f"      2. Check Neo4j Aura console")
        print(f"      3. Whitelist your IP")
        print(f"      4. Try: NEO4J_URI=neo4j+ssc://... (bypass SSL)")
    
    print("\n" + "="*60)
    sys.exit(1)
