import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Hospital
from scrapers import get_all_scrapers
import logging

logger = logging.getLogger(__name__)

async def update_hospital_data(db: AsyncSession, hospital_data: dict):
    """Aggiorna o crea un record ospedale nel database."""
    try:
        # Cerca l'ospedale per nome e reparto
        query = select(Hospital).where(
            Hospital.name == hospital_data["name"],
            Hospital.department == hospital_data["department"]
        )
        result = await db.execute(query)
        hospital = result.scalar_one_or_none()
        
        if not hospital:
            hospital = Hospital(**hospital_data)
            db.add(hospital)
            logger.info(f"Creato nuovo ospedale: {hospital_data['name']} - {hospital_data['department']}")
        else:
            for key, value in hospital_data.items():
                setattr(hospital, key, value)
            logger.info(f"Aggiornato ospedale: {hospital_data['name']} - {hospital_data['department']}")
        
        await db.commit()
        await db.refresh(hospital)
        return hospital
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento dei dati ospedale: {str(e)}")
        await db.rollback()
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