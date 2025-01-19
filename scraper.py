import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Hospital, get_or_create_hospital
from scrapers import get_all_scrapers
import logging

logger = logging.getLogger(__name__)

async def update_hospital_data(db: AsyncSession, hospital_data: dict):
    """Aggiorna o crea un record ospedale nel database."""
    try:
        name = hospital_data.pop("name")
        department = hospital_data.pop("department")
        
        hospital = await get_or_create_hospital(
            db,
            name=name,
            department=department,
            **hospital_data
        )
        
        logger.info(f"Aggiornato ospedale: {name} - {department}")
        return hospital
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento dei dati ospedale: {str(e)}")
        raise

async def scrape_all_hospitals(db: AsyncSession):
    """Esegue lo scraping utilizzando tutti gli scraper disponibili."""
    scrapers = get_all_scrapers()
    all_results = []
    
    for scraper in scrapers:
        try:
            logger.info(f"Avvio scraping per {scraper.name}")
            hospitals_data = await scraper.scrape()
            for hospital_data in hospitals_data:
                await update_hospital_data(db, hospital_data)
            all_results.extend(hospitals_data)
            logger.info(f"Scraping completato per {scraper.name}")
        except Exception as e:
            logger.error(f"Errore con lo scraper {scraper.name}: {str(e)}")
    
    return all_results 