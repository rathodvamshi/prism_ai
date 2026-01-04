#!/usr/bin/env python3
"""
🏥 MongoDB Health Check and Connection Monitor

This script helps diagnose and monitor MongoDB connection issues.
Run this when experiencing timeout errors to get detailed diagnostics.

Usage:
    python mongodb_health_check.py
"""

import asyncio
import time
from datetime import datetime
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, NetworkTimeout
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_async_connection():
    """Test async MongoDB connection (used by main app)"""
    print("\n" + "=" * 60)
    print("🔍 TESTING ASYNC MONGODB CONNECTION")
    print("=" * 60)
    
    try:
        from app.config import settings
        from app.db.mongo_client import _sanitize_mongo_uri, _build_client
        
        print(f"🔗 Connection URI: {settings.MONGO_URI.split('@')[1] if '@' in settings.MONGO_URI else 'local'}")
        
        # Test with different timeout values
        timeout_tests = [5, 10, 30, 60]  # seconds
        
        for timeout_ms in timeout_tests:
            print(f"\n⏱️  Testing with {timeout_ms}s timeout...")
            start_time = time.time()
            
            try:
                client = AsyncIOMotorClient(
                    _sanitize_mongo_uri(settings.MONGO_URI),
                    serverSelectionTimeoutMS=timeout_ms * 1000,
                    connectTimeoutMS=timeout_ms * 1000,
                )
                
                # Test connection
                await asyncio.wait_for(client.admin.command('ping'), timeout=timeout_ms + 5)
                elapsed = time.time() - start_time
                print(f"   ✅ Success in {elapsed:.2f}s")
                client.close()
                return True
                
            except (ServerSelectionTimeoutError, NetworkTimeout, asyncio.TimeoutError) as e:
                elapsed = time.time() - start_time
                print(f"   ❌ Failed in {elapsed:.2f}s: {type(e).__name__}")
                if hasattr(client, 'close'):
                    client.close()
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"   ⚠️  Unexpected error in {elapsed:.2f}s: {e}")
                if hasattr(client, 'close'):
                    client.close()
        
        return False
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_sync_connection():
    """Test sync MongoDB connection (used by Celery)"""
    print("\n" + "=" * 60)
    print("🔍 TESTING SYNC MONGODB CONNECTION (CELERY)")
    print("=" * 60)
    
    try:
        from app.config import settings
        from app.tasks.email_tasks import _mask_uri
        
        # Test the same sanitization logic used by email tasks
        from urllib.parse import urlparse, quote_plus
        import re
        
        def sanitize_mongo_uri_test(uri: str) -> str:
            """Test version of URI sanitization"""
            if '@' not in uri:
                return uri
                
            # Split at the @ symbol to separate credentials from host
            before_at, after_at = uri.rsplit('@', 1)
            protocol_and_creds = before_at
            
            # Extract username and password
            if '//' in protocol_and_creds:
                protocol, creds = protocol_and_creds.split('//', 1)
                protocol = protocol + '//'
            else:
                protocol = ''
                creds = protocol_and_creds
            
            if ':' in creds:
                username, password = creds.split(':', 1)
            else:
                username = creds
                password = ''
            
            # URL encode the credentials
            encoded_username = quote_plus(username)
            encoded_password = quote_plus(password) if password else ''
            
            # Rebuild URI
            if encoded_password:
                sanitized_uri = f"{protocol}{encoded_username}:{encoded_password}@{after_at}"
            else:
                sanitized_uri = f"{protocol}{encoded_username}@{after_at}"
                
            return sanitized_uri
        
        original_uri = settings.MONGO_URI
        sanitized_uri = sanitize_mongo_uri_test(original_uri)
        
        print(f"📊 Original URI (masked): {_mask_uri(original_uri)}")
        print(f"🔧 Sanitized URI (masked): {_mask_uri(sanitized_uri)}")
        
        # Test connection with various timeouts
        timeout_tests = [10, 30, 60]  # seconds
        
        for timeout in timeout_tests:
            print(f"\n⏱️  Testing sync connection with {timeout}s timeout...")
            start_time = time.time()
            
            try:
                client = MongoClient(
                    sanitized_uri,
                    serverSelectionTimeoutMS=timeout * 1000,
                    connectTimeoutMS=timeout * 1000,
                    socketTimeoutMS=timeout * 1000,
                    retryWrites=True,
                    retryReads=True,
                )
                
                # Test connection
                client.admin.command('ping', maxTimeMS=timeout * 1000)
                elapsed = time.time() - start_time
                print(f"   ✅ Success in {elapsed:.2f}s")
                client.close()
                return True
                
            except (ServerSelectionTimeoutError, NetworkTimeout) as e:
                elapsed = time.time() - start_time
                print(f"   ❌ Failed in {elapsed:.2f}s: {type(e).__name__}")
                try:
                    client.close()
                except:
                    pass
                    
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"   ⚠️  Unexpected error in {elapsed:.2f}s: {e}")
                try:
                    client.close()
                except:
                    pass
        
        return False
        
    except Exception as e:
        print(f"❌ Sync connection test failed: {e}")
        return False

async def continuous_monitoring(duration_minutes=5):
    """Continuously monitor MongoDB connection for specified duration"""
    print("\n" + "=" * 60)
    print(f"📊 CONTINUOUS MONITORING ({duration_minutes} minutes)")
    print("=" * 60)
    
    try:
        from app.db.mongo_client import _build_client
        
        client = _build_client()
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        success_count = 0
        failure_count = 0
        
        while time.time() < end_time:
            try:
                await asyncio.wait_for(client.admin.command('ping'), timeout=10)
                success_count += 1
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Connection OK ({success_count} successes)")
                
            except Exception as e:
                failure_count += 1
                print(f"❌ {datetime.now().strftime('%H:%M:%S')} - Connection FAILED: {type(e).__name__} ({failure_count} failures)")
            
            await asyncio.sleep(30)  # Check every 30 seconds
        
        client.close()
        
        total_checks = success_count + failure_count
        success_rate = (success_count / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n📈 MONITORING RESULTS:")
        print(f"   Total checks: {total_checks}")
        print(f"   Successes: {success_count}")
        print(f"   Failures: {failure_count}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        return success_rate > 80  # Consider healthy if > 80% success rate
        
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        return False

def print_network_diagnostics():
    """Print network and DNS diagnostics"""
    print("\n" + "=" * 60)
    print("🌐 NETWORK DIAGNOSTICS")
    print("=" * 60)
    
    try:
        from app.config import settings
        from urllib.parse import urlparse
        
        # Extract hostname from MongoDB URI
        parsed = urlparse(settings.MONGO_URI)
        hostname = parsed.hostname
        
        if hostname:
            print(f"🔗 MongoDB hostname: {hostname}")
            
            # Test DNS resolution
            try:
                import socket
                ip = socket.gethostbyname(hostname)
                print(f"🌐 DNS resolution: {hostname} -> {ip}")
            except Exception as e:
                print(f"❌ DNS resolution failed: {e}")
            
            # Test network connectivity (ping-like)
            try:
                import socket
                sock = socket.create_connection((hostname, parsed.port or 27017), timeout=10)
                sock.close()
                print(f"✅ Network connectivity: OK")
            except Exception as e:
                print(f"❌ Network connectivity failed: {e}")
        
    except Exception as e:
        print(f"❌ Network diagnostics failed: {e}")

async def main():
    """Main health check routine"""
    print("🏥 MONGODB HEALTH CHECK STARTED")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Network diagnostics
    print_network_diagnostics()
    
    # Test sync connection (Celery)
    sync_ok = test_sync_connection()
    
    # Test async connection (main app)
    async_ok = await test_async_connection()
    
    # If basic tests pass, run continuous monitoring
    if async_ok:
        print(f"\n🎉 Basic connections successful! Running continuous monitoring...")
        monitoring_ok = await continuous_monitoring(2)  # 2 minutes
    else:
        monitoring_ok = False
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 HEALTH CHECK SUMMARY")
    print("=" * 60)
    print(f"Sync Connection (Celery): {'✅ OK' if sync_ok else '❌ FAILED'}")
    print(f"Async Connection (Main): {'✅ OK' if async_ok else '❌ FAILED'}")
    print(f"Continuous Monitoring: {'✅ STABLE' if monitoring_ok else '❌ UNSTABLE'}")
    
    if not (sync_ok and async_ok):
        print("\n💡 RECOMMENDATIONS:")
        print("1. Check MongoDB Atlas cluster status")
        print("2. Verify network connectivity and firewall rules")
        print("3. Check if IP address is whitelisted in Atlas")
        print("4. Consider increasing timeout values")
        print("5. Check MongoDB Atlas connection limits")
        
    print(f"\n🏁 Health check completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())