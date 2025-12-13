from app.db.mongo_client import tasks_collection
from app.utils.llm_client import get_llm_response
from datetime import datetime
import json

# ⚠️ MUST BE 'async def'
async def extract_task_details(message: str) -> dict:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    system_prompt = f"""
    You are a task extractor. 
    Current Time: {current_time}
    
    Extract the 'task_description' and 'due_date' (YYYY-MM-DD HH:MM format) from the user message.
    If no time is specified, set due_date to null.
    
    Return ONLY valid JSON. Example:
    {{
        "task_description": "Call mom",
        "due_date": "2025-12-12 10:00"
    }}
    """
    
    # This will now work because get_llm_response is async
    response = await get_llm_response(prompt=message, system_prompt=system_prompt)
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        json_str = response[start:end]
        return json.loads(json_str)
    except:
        return {"task_description": message, "due_date": None}

# ⚠️ MUST BE 'async def'
async def create_task(user_id: str, message: str):
    # This will now work because extract_task_details is async
    details = await extract_task_details(message)
    
    task_doc = {
        "user_id": user_id,
        "description": details.get("task_description"),
        "due_date": details.get("due_date"),
        "status": "pending",
        "created_at": datetime.now()
    }
    
    # This will now work because insert_one is async
    await tasks_collection.insert_one(task_doc)
    
    return f"✅ Task Saved: {task_doc['description']} (Due: {task_doc['due_date']})"