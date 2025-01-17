import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import Hospital
from scrapers import get_all_scrapers

async def update_hospital_data(db: AsyncSession, hospital_data: dict):
    """Aggiorna o crea un record ospedale nel database."""
    hospital = await db.get(
        Hospital,
        (hospital_data["name"], hospital_data["department"])
    )
    
    if not hospital:
        hospital = Hospital(**hospital_data)
        db.add(hospital)
    else:
        for key, value in hospital_data.items():
            setattr(hospital, key, value)
    
    await db.commit()
    await db.refresh(hospital)

async def scrape_all_hospitals(db: AsyncSession):
    """Esegue lo scraping utilizzando tutti gli scraper disponibili."""
    scrapers = get_all_scrapers()
    all_results = []
    
    for scraper in scrapers:
        try:
            hospitals_data = await scraper.scrape()
            for hospital_data in hospitals_data:
                await update_hospital_data(db, hospital_data)
            all_results.extend(hospitals_data)
        except Exception as e:
            print(f"Errore con lo scraper {scraper.name}: {str(e)}")
    
    return all_results 