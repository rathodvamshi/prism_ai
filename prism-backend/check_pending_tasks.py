"""Quick script to check pending tasks in MongoDB"""
import asyncio
from datetime import datetime
from app.db.mongo_client import tasks_collection

async def check_tasks():
    print("\n🔍 Checking pending tasks in MongoDB...")
    print("=" * 70)
    
    tasks = []
    async for task in tasks_collection.find({"status": "pending"}).sort("due_date", 1):
        tasks.append(task)
    
    if not tasks:
        print("❌ No pending tasks found")
        return
    
    print(f"✅ Found {len(tasks)} pending task(s):\n")
    
    now = datetime.utcnow()
    for i, task in enumerate(tasks, 1):
        task_id = task.get('_id')
        description = task.get('description', 'N/A')
        due_date = task.get('due_date')
        user_email = task.get('user_email', 'N/A')
        
        time_diff = (due_date - now).total_seconds() if due_date else None
        
        print(f"Task #{i}")
        print(f"  📋 ID: {task_id}")
        print(f"  📝 Description: {description}")
        print(f"  📧 Email: {user_email}")
        print(f"  ⏰ Due: {due_date}")
        
        if time_diff is not None:
            if time_diff < 0:
                print(f"  ⚠️  OVERDUE by {abs(time_diff):.0f} seconds")
            else:
                print(f"  ⏳ Due in {time_diff:.0f} seconds ({time_diff/60:.1f} minutes)")
        print()
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(check_tasks())
