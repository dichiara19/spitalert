from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import AsyncSessionLocal
from scraper import scrape_all_hospitals
import os
from dotenv import load_dotenv
import logging
import sys
from datetime import datetime

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

scheduler = AsyncIOScheduler()

async def scheduled_scraping():
    """Task periodico per lo scraping dei dati ospedalieri."""
    try:
        async with AsyncSessionLocal() as session:
            await scrape_all_hospitals(session)
            logger.info("Scraping completato con successo")
    except Exception as e:
        logger.error(f"Errore durante lo scraping: {str(e)}")

def get_interval_seconds():
    """
    Ottiene l'intervallo di scraping dalle variabili d'ambiente.
    Restituisce l'intervallo in secondi, con fallback a 3600 (1 ora) in caso di errore.
    """
    try:
        interval = os.getenv("SCRAPING_INTERVAL", "3600").strip()
        
        if not interval.isdigit():
            raise ValueError(f"L'intervallo deve essere un numero intero positivo, ricevuto: {interval}")
            
        interval_value = int(interval)
        if interval_value <= 0:
            raise ValueError(f"L'intervallo deve essere maggiore di zero, ricevuto: {interval_value}")
            
        return interval_value
        
    except (ValueError, TypeError) as e:
        logger.error(f"Errore nel parsing dell'intervallo: {str(e)}")
        return 3600  # default value: 1 hour

def setup_scheduler():
    """Configura e avvia lo scheduler."""
    try:
        interval_seconds = get_interval_seconds()
        
        scheduler.add_job(
            scheduled_scraping,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id='hospital_scraping',
            name='Scraping periodico ospedali',
            replace_existing=True,
            next_run_time=datetime.now()  # run immediately
        )
        
        logger.info(f"Scheduler configurato con intervallo di {interval_seconds} secondi")
        scheduler.start()
        logger.info("Scheduler avviato con successo")
    except Exception as e:
        logger.error(f"Errore nella configurazione dello scheduler: {str(e)}")
        raise RuntimeError(f"Errore nella configurazione dello scheduler: {str(e)}")