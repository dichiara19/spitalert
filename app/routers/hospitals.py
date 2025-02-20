from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from ..database import get_db
from ..models import Hospital, HospitalStatus, HospitalHistory
from ..schemas import (
    Hospital as HospitalSchema,
    HospitalWithStatus,
    HospitalStats,
    HospitalCreate,
    HospitalStatusCreate,
    HospitalHistory as HospitalHistorySchema,
    HospitalWithDetailedStatus,
    ColorCodeDistribution
)
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..scrapers import ScraperFactory
import logging

router = APIRouter()

@router.get("/", response_model=List[HospitalWithStatus])
async def get_hospitals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    city: Optional[str] = None,
    province: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Recupera la lista degli ospedali con il loro stato attuale.
    Supporta paginazione e filtri per città e provincia.
    """
    # base query with eager loading
    query = (
        select(Hospital)
        .options(selectinload(Hospital.current_status))
    )
    
    # apply filters
    if city:
        query = query.filter(Hospital.city == city)
    if province:
        query = query.filter(Hospital.province == province)
    
    # apply pagination
    query = query.offset(skip).limit(limit)
    
    # execute query
    result = await db.execute(query)
    hospitals = result.scalars().all()
    
    return hospitals

@router.get("/stats", response_model=HospitalStats)
async def get_hospital_stats(db: AsyncSession = Depends(get_db)):
    """
    Recupera statistiche aggregate sugli ospedali.
    """
    # total hospitals
    total_query = select(func.count()).select_from(Hospital)
    total_result = await db.execute(total_query)
    total_hospitals = total_result.scalar()
    
    # query to get the latest status for each hospital
    latest_status_query = (
        select(HospitalStatus)
        .join(Hospital)
        .options(selectinload(HospitalStatus.hospital))
        .distinct(HospitalStatus.hospital_id)
        .order_by(
            HospitalStatus.hospital_id,
            HospitalStatus.last_updated.desc()
        )
    )
    
    status_result = await db.execute(latest_status_query)
    statuses = status_result.scalars().all()
    
    # calculate statistics
    overcrowded = sum(1 for s in statuses if s.waiting_time > 120)  # more than 2 hours
    avg_waiting = sum(s.waiting_time for s in statuses) / len(statuses) if statuses else 0
    
    # count for color
    colors = {}
    for s in statuses:
        colors[s.color_code] = colors.get(s.color_code, 0) + 1
    
    return HospitalStats(
        total_hospitals=total_hospitals,
        overcrowded_hospitals=overcrowded,
        average_waiting_time=avg_waiting,
        hospitals_by_color=colors
    )

@router.get("/detailed", response_model=List[HospitalWithDetailedStatus])
async def get_hospitals_detailed(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db)
):
    """
    Recupera la lista degli ospedali con la distribuzione dettagliata dei codici colore.
    """
    # get hospitals with their current status
    query = (
        select(Hospital)
        .options(selectinload(Hospital.current_status))
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    hospitals = result.scalars().all()
    
    # for each hospital, get the color distribution
    for hospital in hospitals:
        if hospital.current_status:
            try:
                # create a scraper for the hospital
                scraper = ScraperFactory.create_scraper(
                    hospital_id=hospital.id,
                    config={}
                )
                
                # try to get the color distribution directly from the scraper
                try:
                    distribution = await scraper.get_color_distribution()
                    if distribution:
                        hospital.current_status.color_distribution = distribution
                        continue
                except Exception as e:
                    logging.debug(f"Impossibile ottenere la distribuzione colori direttamente: {str(e)}")
                
                # if the scraper has HTML selectors, use traditional HTML parsing
                if hasattr(scraper, 'hospital_selectors'):
                    # get raw data from the site
                    html = await scraper.get_page(scraper.BASE_URL)
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # select the hospital container
                    selector = scraper.hospital_selectors.get(scraper.hospital_code)
                    hospital_div = soup.select_one(selector)
                    
                    if hospital_div:
                        # extract counts for each color code
                        distribution = ColorCodeDistribution(
                            white=scraper._extract_number(hospital_div, ".olo-codice-grey .olo-number-codice"),
                            green=scraper._extract_number(hospital_div, ".olo-codice-green .olo-number-codice"),
                            blue=scraper._extract_number(hospital_div, ".olo-codice-azure .olo-number-codice"),
                            orange=scraper._extract_number(hospital_div, ".olo-codice-orange .olo-number-codice"),
                            red=scraper._extract_number(hospital_div, ".olo-codice-red .olo-number-codice")
                        )
                        
                        # add the distribution to the current status
                        hospital.current_status.color_distribution = distribution
                
            except Exception as e:
                # log the error but continue with the next hospital
                logging.error(f"Errore nel recupero della distribuzione colori per l'ospedale {hospital.id}: {str(e)}")
                continue
    
    return hospitals

@router.get("/nearby", response_model=List[HospitalWithStatus])
async def get_nearby_hospitals(
    lat: float = Query(..., description="Latitudine"),
    lon: float = Query(..., description="Longitudine"),
    radius: float = Query(10.0, description="Raggio in km"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trova gli ospedali nel raggio specificato dalle coordinate date.
    Utilizza la formula di Haversine per il calcolo della distanza.
    """
    # conversion of radius to degrees (approximation)
    radius_degrees = radius / 111.0  # 1 degree ≈ 111 km
    
    query = select(Hospital).filter(
        func.sqrt(
            func.pow(Hospital.latitude - lat, 2) +
            func.pow(Hospital.longitude - lon, 2)
        ) <= radius_degrees
    )
    
    result = await db.execute(query)
    hospitals = result.scalars().all()
    return hospitals

@router.get("/{hospital_id}", response_model=HospitalWithStatus)
async def get_hospital(hospital_id: int, db: AsyncSession = Depends(get_db)):
    """
    Recupera i dettagli di un singolo ospedale con il suo stato attuale.
    """
    # load the hospital and its current status in a single query
    query = (
        select(Hospital)
        .options(selectinload(Hospital.current_status))
        .filter(Hospital.id == hospital_id)
    )
    result = await db.execute(query)
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Ospedale non trovato")
    
    return hospital

@router.get("/{hospital_id}/history", response_model=List[HospitalHistorySchema])
async def get_hospital_history(
    hospital_id: int,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """
    Recupera lo storico degli stati di un ospedale negli ultimi giorni specificati.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(HospitalHistory).filter(
        HospitalHistory.hospital_id == hospital_id,
        HospitalHistory.scraped_at >= cutoff_date
    ).order_by(HospitalHistory.scraped_at.desc())
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    if not history:
        raise HTTPException(status_code=404, detail="Nessuno storico trovato per questo ospedale")
    
    return history

@router.get("/{hospital_id}/detailed", response_model=HospitalWithDetailedStatus)
async def get_hospital_detailed(hospital_id: int, db: AsyncSession = Depends(get_db)):
    """
    Recupera i dettagli di un singolo ospedale con la distribuzione dettagliata dei codici colore.
    """
    # load the hospital and its current status
    query = (
        select(Hospital)
        .options(selectinload(Hospital.current_status))
        .filter(Hospital.id == hospital_id)
    )
    result = await db.execute(query)
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Ospedale non trovato")
        
    if hospital.current_status:
        # for each hospital, get the color distribution
        for hospital in [hospital]:
            if hospital.current_status:
                try:
                    # create a scraper for the hospital
                    scraper = ScraperFactory.create_scraper(
                        hospital_id=hospital.id,
                        config={}
                    )
                    
                    # try to get the color distribution directly from the scraper
                    try:
                        distribution = await scraper.get_color_distribution()
                        if distribution:
                            hospital.current_status.color_distribution = distribution
                            continue
                    except Exception as e:
                        logging.debug(f"Impossibile ottenere la distribuzione colori direttamente: {str(e)}")
                    
                    # if the scraper has HTML selectors, use traditional HTML parsing
                    if hasattr(scraper, 'hospital_selectors'):
                        # get raw data from the site
                        html = await scraper.get_page(scraper.BASE_URL)
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # select the hospital container
                        selector = scraper.hospital_selectors.get(scraper.hospital_code)
                        hospital_div = soup.select_one(selector)
                        
                        if hospital_div:
                            # extract counts for each color code
                            distribution = ColorCodeDistribution(
                                white=scraper._extract_number(hospital_div, ".olo-codice-grey .olo-number-codice"),
                                green=scraper._extract_number(hospital_div, ".olo-codice-green .olo-number-codice"),
                                blue=scraper._extract_number(hospital_div, ".olo-codice-azure .olo-number-codice"),
                                orange=scraper._extract_number(hospital_div, ".olo-codice-orange .olo-number-codice"),
                                red=scraper._extract_number(hospital_div, ".olo-codice-red .olo-number-codice")
                            )
                            
                            # add the distribution to the current status
                            hospital.current_status.color_distribution = distribution
                    
                except Exception as e:
                    # log the error but continue with the next hospital
                    logging.error(f"Errore nel recupero della distribuzione colori per l'ospedale {hospital.id}: {str(e)}")
                    continue
    
    return hospital 