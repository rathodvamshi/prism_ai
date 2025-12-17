"""
✅ System Verification Script
Checks if everything is ready for production email system
"""
import asyncio
import sys
from datetime import datetime

async def verify_system():
    print("\n" + "="*70)
    print("🔍 PRISM EMAIL SYSTEM - Production Readiness Check")
    print("="*70 + "\n")
    
    issues = []
    warnings = []
    
    # 1. Check SendGrid
    print("1️⃣ Checking SendGrid configuration...")
    from app.config import settings
    if not settings.SENDGRID_API_KEY or settings.SENDGRID_API_KEY == "":
        issues.append("❌ SENDGRID_API_KEY not set in .env")
    else:
        print(f"   ✅ SendGrid API key found: {settings.SENDGRID_API_KEY[:10]}...")
    
    if not settings.SENDER_EMAIL or "@" not in settings.SENDER_EMAIL:
        issues.append("❌ SENDER_EMAIL not configured")
    else:
        print(f"   ✅ Sender email: {settings.SENDER_EMAIL}")
    
    # 2. Check Redis
    print("\n2️⃣ Checking Redis connection...")
    try:
        from app.db.redis_client import redis_client
        result = await redis_client.ping()
        if result:
            print("   ✅ Redis connection successful")
        else:
            issues.append("❌ Redis ping failed")
    except Exception as e:
        issues.append(f"❌ Redis connection failed: {e}")
    
    # 3. Check MongoDB
    print("\n3️⃣ Checking MongoDB connection...")
    try:
        from app.db.mongo_client import tasks_collection
        count = await tasks_collection.count_documents({})
        print(f"   ✅ MongoDB connected ({count} tasks in database)")
    except Exception as e:
        issues.append(f"❌ MongoDB connection failed: {e}")
    
    # 4. Check indexes
    print("\n4️⃣ Checking database indexes...")
    try:
        from app.db.mongo_client import tasks_collection
        indexes = await tasks_collection.index_information()
        
        has_status_due = any("status" in str(idx) and "due_date" in str(idx) for idx in indexes.values())
        if has_status_due:
            print("   ✅ Performance indexes found")
        else:
            warnings.append("⚠️  No performance indexes (run: python add_indexes.py)")
    except Exception as e:
        warnings.append(f"⚠️  Could not check indexes: {e}")
    
    # 5. Check email worker file
    print("\n5️⃣ Checking email worker...")
    import os
    if os.path.exists("email_worker.py"):
        print("   ✅ email_worker.py exists")
    else:
        issues.append("❌ email_worker.py not found")
    
    # 6. Check startup script
    print("\n6️⃣ Checking startup script...")
    if os.path.exists("start_production.bat"):
        print("   ✅ start_production.bat exists")
    else:
        warnings.append("⚠️  start_production.bat not found")
    
    # Results
    print("\n" + "="*70)
    print("📊 VERIFICATION RESULTS")
    print("="*70 + "\n")
    
    if issues:
        print("❌ CRITICAL ISSUES (must fix):")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS (recommended to fix):")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not issues and not warnings:
        print("✅ ALL CHECKS PASSED!")
        print("\n🚀 System is ready for production!")
        print("\n📝 Next steps:")
        print("   1. Run: start_production.bat")
        print("   2. Test with: 'Remind me to test in 2 minutes'")
        print("   3. Check email inbox")
        return True
    elif not issues:
        print("✅ SYSTEM READY (with warnings)")
        print("\n🚀 You can run the system, but consider fixing warnings")
        print("\n📝 Next steps:")
        print("   1. Run: start_production.bat")
        print("   2. Test with: 'Remind me to test in 2 minutes'")
        return True
    else:
        print("❌ SYSTEM NOT READY")
        print("\n🔧 Please fix critical issues before running")
        return False

if __name__ == "__main__":
    result = asyncio.run(verify_system())
    sys.exit(0 if result else 1)
