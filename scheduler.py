from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import AsyncSessionLocal
from scraper import scrape_all_hospitals
import os
from dotenv import load_dotenv

load_dotenv()

scheduler = AsyncIOScheduler()

async def scheduled_scraping():
    """Task periodico per lo scraping dei dati ospedalieri."""
    async with AsyncSessionLocal() as session:
        await scrape_all_hospitals(session)

def setup_scheduler():
    """Configura e avvia lo scheduler."""
    interval_seconds = int(os.getenv("SCRAPING_INTERVAL", 3600))
    
    scheduler.add_job(
        scheduled_scraping,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id='hospital_scraping',
        name='Scraping periodico ospedali',
        replace_existing=True
    )
    
    scheduler.start() 