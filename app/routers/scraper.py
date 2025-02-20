from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import httpx
import asyncio
from typing import Dict

from ..database import get_db
from .. import models, schemas
from ..services.scraper_service import ScraperService
from ..scrapers.factory import ScraperFactory

router = APIRouter()

async def scrape_hospital_data(hospital_id: int) -> dict:
    """
    Funzione di esempio per lo scraping dei dati di un ospedale.
    In produzione, questa funzione dovrà essere implementata per ogni ospedale specifico.
    """
    # Simulazione di una richiesta HTTP
    await asyncio.sleep(1)  # Simula il tempo di risposta
    return {
        "hospital_id": hospital_id,
        "available_beds": 10,  # Dati di esempio
        "waiting_time": 30     # Dati di esempio
    }

async def update_hospital_data(db: AsyncSession, hospital_id: int):
    """
    Aggiorna i dati di un ospedale nel database.
    """
    data = await scrape_hospital_data(hospital_id)
    
    # Aggiorna lo stato corrente
    status = models.HospitalStatus(
        hospital_id=data["hospital_id"],
        available_beds=data["available_beds"],
        waiting_time=data["waiting_time"]
    )
    db.add(status)
    
    # Salva nella storia
    history = models.HospitalHistory(
        hospital_id=data["hospital_id"],
        available_beds=data["available_beds"],
        waiting_time=data["waiting_time"]
    )
    db.add(history)
    
    await db.commit()

@router.post("/run", response_model=Dict[str, bool])
async def run_scrapers(db: AsyncSession = Depends(get_db)):
    """
    Esegue lo scraping per tutti gli ospedali registrati.
    
    Returns:
        Dict[str, bool]: Risultati dello scraping per ogni ospedale
    """
    service = ScraperService(db)
    results = await service.scrape_all_hospitals()
    return results

@router.post("/run/{hospital_id}", response_model=bool)
async def run_hospital_scraper(
    hospital_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Esegue lo scraping per un singolo ospedale.
    
    Args:
        hospital_id: ID dell'ospedale
        
    Returns:
        bool: True se lo scraping è avvenuto con successo, False altrimenti
    """
    service = ScraperService(db)
    success = await service.scrape_hospital(hospital_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Errore durante lo scraping dell'ospedale {hospital_id}"
        )
    
    return success

@router.get("/available", response_model=Dict[str, str])
async def get_available_scrapers():
    """
    Restituisce la lista degli scraper disponibili.
    
    Returns:
        Dict[str, str]: Dizionario con i codici degli ospedali e i nomi degli scraper
    """
    return ScraperFactory.get_available_scrapers() 