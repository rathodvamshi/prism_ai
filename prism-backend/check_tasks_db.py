"""Quick script to check tasks in MongoDB - uses user_tasks collection"""
import asyncio
from app.db.mongo_client import tasks_collection


async def check_tasks():
    # Get ALL tasks (most recent) from user_tasks collection
    cursor = tasks_collection.find({}).sort("created_at", -1).limit(10)
    all_tasks = await cursor.to_list(length=10)
    
    print(f"\n📋 Database: prismdb | Collection: user_tasks")
    print(f"📋 Found {len(all_tasks)} tasks (all status):")
    for t in all_tasks:
        desc = t.get("description", "No desc")
        due = t.get("due_date", "No date")
        status = t.get("status", "unknown")
        created = t.get("created_at", "No created_at")
        email_status = t.get("email_status", "unknown")
        user = t.get("userId", "No user")
        print(f"  - {desc}")
        print(f"    Due: {due} | Status: {status} | Email: {email_status}")
        print(f"    Created: {created} | User: {user}")
        print()


if __name__ == "__main__":
    asyncio.run(check_tasks())
