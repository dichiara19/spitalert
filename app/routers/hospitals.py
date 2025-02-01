from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from ..database import get_db
from ..models import Hospital, HospitalStatus, HospitalHistory
from ..schemas import (
    Hospital as HospitalSchema,
    HospitalWithStatus,
    HospitalStats,
    HospitalCreate,
    HospitalStatusCreate
)
from datetime import datetime, timedelta

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
    query = select(Hospital)
    
    if city:
        query = query.filter(Hospital.city == city)
    if province:
        query = query.filter(Hospital.province == province)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    hospitals = result.scalars().all()
    
    return hospitals

@router.get("/stats", response_model=HospitalStats)
async def get_hospital_stats(db: AsyncSession = Depends(get_db)):
    """
    Recupera statistiche aggregate sugli ospedali.
    """
    # Totale ospedali
    total_query = select(func.count()).select_from(Hospital)
    total_result = await db.execute(total_query)
    total_hospitals = total_result.scalar()
    
    # Statistiche sullo stato attuale
    status_query = select(HospitalStatus)
    status_result = await db.execute(status_query)
    statuses = status_result.scalars().all()
    
    # Calcolo statistiche
    overcrowded = sum(1 for s in statuses if s.waiting_time > 120)  # più di 2 ore
    avg_waiting = sum(s.waiting_time for s in statuses) / len(statuses) if statuses else 0
    
    # Conteggio per colore
    colors = {}
    for s in statuses:
        colors[s.color_code] = colors.get(s.color_code, 0) + 1
    
    return HospitalStats(
        total_hospitals=total_hospitals,
        overcrowded_hospitals=overcrowded,
        average_waiting_time=avg_waiting,
        hospitals_by_color=colors
    )

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
    # Conversione del raggio in gradi (approssimazione)
    radius_degrees = radius / 111.0  # 1 grado ≈ 111 km
    
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
    query = select(Hospital).filter(Hospital.id == hospital_id)
    result = await db.execute(query)
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Ospedale non trovato")
    
    return hospital

@router.get("/{hospital_id}/history", response_model=List[HospitalHistory])
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