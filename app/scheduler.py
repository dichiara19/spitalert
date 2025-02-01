from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .services.scraper_service import ScraperService
from .database import get_db
from .config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton scheduler
scheduler = AsyncIOScheduler()

async def scrape_all_hospitals():
    """Job per lo scraping di tutti gli ospedali."""
    async for db in get_db():
        try:
            service = ScraperService(db)
            results = await service.scrape_all_hospitals()
            logger.info(f"Scraping completato: {sum(results.values())}/{len(results)} successi")
        except Exception as e:
            logger.error(f"Errore durante lo scraping: {str(e)}", exc_info=True)

def setup_scheduler():
    """Configura e avvia lo scheduler."""
    if not settings.SCRAPE_ENABLED:
        logger.info("Scheduler disabilitato dalle configurazioni")
        return
        
    # Log del valore di SCRAPE_INTERVAL
    logger.info(f"SCRAPE_INTERVAL configurato: {settings.SCRAPE_INTERVAL} secondi")
    
    # Converti l'intervallo da secondi a minuti
    minutes_interval = settings.SCRAPE_INTERVAL // 60
    
    # Esegui lo scraping secondo l'intervallo configurato
    scheduler.add_job(
        scrape_all_hospitals,
        CronTrigger(minute=f"*/{minutes_interval}"),  # Usa i minuti invece dei secondi
        id="scrape_hospitals",
        replace_existing=True,
        max_instances=1  # Evita esecuzioni sovrapposte
    )
    scheduler.start()
    logger.info(
        f"Scheduler avviato - Intervallo: {minutes_interval} minuti"
    ) 