from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.email_service import send_email_notification
from app.services.search_service import search_web
from datetime import datetime

scheduler = AsyncIOScheduler()

async def morning_briefing_job():
    """
    The job that runs every morning.
    """
    print("⏰ Running Morning Briefing...")
    
    # 1. Get Info
    date_str = datetime.now().strftime("%A, %d %B")
    news = await search_web("Top tech news headlines today", max_results=3)
    weather = await search_web("Weather in Hyderabad today", max_results=1)
    
    # 2. Compose Message
    message = f"""
    Subject: 🌞 Morning Briefing: {date_str}
    
    Good Morning! Here is your start to the day:
    
    🌤️ **Weather**:
    {weather}
    
    📰 **Top News**:
    {news}
    
    Have a productive day! - PRISM 🌈
    """
    
    # 3. Send (Hardcoded user email for now, in production loop through users)
    # You can call your email service here.
    # await send_email_notification(message) 
    print(message) # Printing to console for testing

def start_scheduler():
    # Schedule to run every day at 8:00 AM
    scheduler.add_job(morning_briefing_job, 'cron', hour=8, minute=0)
    scheduler.start()