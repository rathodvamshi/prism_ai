"""
Neo4j Aura Connection Diagnostic Tool
Tests network connectivity, DNS resolution, and authentication
"""

import asyncio
import socket
import ssl
from urllib.parse import urlparse
from neo4j import AsyncGraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j Aura credentials
NEO4J_URI = "neo4j+s://46945710.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "AtNi7QOzQAc5zKA2HtFCAoIJN2YWyHGi_3BnpppsfvU"

def test_dns_resolution():
    """Test DNS resolution for Neo4j Aura"""
    print("\n" + "="*60)
    print("1️⃣ Testing DNS Resolution")
    print("="*60)
    
    try:
        parsed = urlparse(NEO4J_URI)
        hostname = parsed.hostname or "46945710.databases.neo4j.io"
        
        print(f"🔍 Resolving hostname: {hostname}")
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ DNS Resolution SUCCESS: {hostname} → {ip_address}")
        return True, hostname
    except socket.gaierror as e:
        print(f"❌ DNS Resolution FAILED: {e}")
        print(f"💡 Possible fixes:")
        print(f"   - Check your internet connection")
        print(f"   - Verify DNS settings (try Google DNS: 8.8.8.8)")
        print(f"   - Check if firewall is blocking DNS queries")
        return False, None
    except Exception as e:
        print(f"❌ DNS Error: {e}")
        return False, None

def test_tcp_connection(hostname):
    """Test TCP connection to Neo4j port"""
    print("\n" + "="*60)
    print("2️⃣ Testing TCP Connection")
    print("="*60)
    
    port = 7687  # Neo4j bolt port
    
    try:
        print(f"🔌 Connecting to {hostname}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP Connection SUCCESS on port {port}")
            return True
        else:
            print(f"❌ TCP Connection FAILED (error code: {result})")
            print(f"💡 Possible fixes:")
            print(f"   - Check if port {port} is blocked by firewall")
            print(f"   - Verify Neo4j Aura instance is running")
            print(f"   - Check if your IP is whitelisted in Neo4j Aura")
            return False
    except socket.timeout:
        print(f"❌ Connection TIMEOUT")
        print(f"💡 Network may be blocking the connection")
        return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_ssl_connection(hostname):
    """Test SSL/TLS connection"""
    print("\n" + "="*60)
    print("3️⃣ Testing SSL/TLS Connection")
    print("="*60)
    
    port = 7687
    
    try:
        print(f"🔐 Testing SSL connection to {hostname}:{port}")
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                print(f"✅ SSL/TLS Connection SUCCESS")
                print(f"   Protocol: {ssock.version()}")
                cert = ssock.getpeercert()
                print(f"   Certificate issued to: {cert.get('subject', 'N/A')}")
                return True
    except ssl.SSLError as e:
        print(f"❌ SSL/TLS Error: {e}")
        print(f"💡 SSL certificate validation failed")
        return False
    except Exception as e:
        print(f"❌ SSL Connection Error: {e}")
        return False

async def test_neo4j_driver():
    """Test Neo4j driver connection and authentication"""
    print("\n" + "="*60)
    print("4️⃣ Testing Neo4j Driver Connection")
    print("="*60)
    
    driver = None
    try:
        print(f"🚀 Connecting to Neo4j Aura...")
        print(f"   URI: {NEO4J_URI}")
        print(f"   User: {NEO4J_USER}")
        
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_timeout=30
        )
        
        # Verify connectivity
        await driver.verify_connectivity()
        print(f"✅ Neo4j Driver Connection SUCCESS")
        
        # Test a simple query
        print(f"\n🔍 Running test query...")
        async with driver.session() as session:
            result = await session.run("RETURN 1 as num")
            record = await result.single()
            print(f"✅ Query Execution SUCCESS: {record['num']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Neo4j Connection FAILED: {e}")
        print(f"\n💡 Possible fixes:")
        print(f"   - Verify username and password are correct")
        print(f"   - Check if database is online in Neo4j Aura console")
        print(f"   - Ensure your IP is whitelisted (0.0.0.0/0 for testing)")
        print(f"   - Try using neo4j+ssc:// instead of neo4j+s://")
        return False
    finally:
        if driver:
            await driver.close()

async def test_connection_timeout():
    """Test with shorter timeout to diagnose network issues"""
    print("\n" + "="*60)
    print("5️⃣ Testing Connection with Timeout")
    print("="*60)
    
    driver = None
    try:
        print(f"⏱️ Testing with 5-second timeout...")
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=5
        )
        
        await driver.verify_connectivity()
        print(f"✅ Connection established within timeout")
        return True
        
    except asyncio.TimeoutError:
        print(f"❌ Connection TIMEOUT")
        print(f"💡 Network latency is too high or connection is blocked")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if driver:
            await driver.close()

async def main():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("🔧 Neo4j Aura Connection Diagnostic")
    print("="*60)
    
    results = []
    
    # Test 1: DNS Resolution
    dns_ok, hostname = test_dns_resolution()
    results.append(("DNS Resolution", dns_ok))
    
    if not dns_ok:
        print("\n⚠️ DNS resolution failed. Cannot proceed with further tests.")
        return
    
    # Test 2: TCP Connection
    tcp_ok = test_tcp_connection(hostname)
    results.append(("TCP Connection", tcp_ok))
    
    # Test 3: SSL Connection
    ssl_ok = test_ssl_connection(hostname)
    results.append(("SSL/TLS Connection", ssl_ok))
    
    # Test 4: Neo4j Driver
    driver_ok = await test_neo4j_driver()
    results.append(("Neo4j Driver", driver_ok))
    
    # Test 5: Connection Timeout
    timeout_ok = await test_connection_timeout()
    results.append(("Timeout Test", timeout_ok))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests PASSED! Neo4j connection is working correctly.")
    else:
        print("\n⚠️ Some tests FAILED. Check the output above for details.")
        print("\n📝 Quick fixes to try:")
        print("   1. Whitelist your IP in Neo4j Aura console (0.0.0.0/0 for testing)")
        print("   2. Verify database is running in Neo4j Aura")
        print("   3. Check Windows Firewall settings")
        print("   4. Try using a VPN if corporate network blocks Neo4j ports")
        print("   5. Use neo4j+ssc:// URI if SSL verification fails")

if __name__ == "__main__":
    asyncio.run(main())
