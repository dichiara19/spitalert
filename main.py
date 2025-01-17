from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, init_db, Hospital
from scheduler import setup_scheduler
from typing import List
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="SpiTAlert API")

class HospitalResponse(BaseModel):
    id: int
    name: str
    department: str
    total_patients: int
    waiting_patients: int
    red_code: int
    orange_code: int
    azure_code: int
    green_code: int
    white_code: int
    overcrowding_index: float
    last_updated: datetime
    
    class Config:
        from_attributes = True

@app.on_event("startup")
async def startup_event():
    await init_db()
    setup_scheduler()

@app.get("/hospitals/", response_model=List[HospitalResponse])
async def get_hospitals(db: AsyncSession = Depends(get_db)):
    """Recupera la lista di tutti gli ospedali attivi."""
    query = select(Hospital).filter(Hospital.is_active == True)
    result = await db.execute(query)
    hospitals = result.scalars().all()
    return hospitals

@app.get("/hospitals/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(hospital_id: int, db: AsyncSession = Depends(get_db)):
    """Recupera i dettagli di un ospedale specifico."""
    query = select(Hospital).filter(Hospital.id == hospital_id, Hospital.is_active == True)
    result = await db.execute(query)
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Ospedale non trovato")
    
    return hospital

@app.get("/hospitals/department/{department}", response_model=List[HospitalResponse])
async def get_hospitals_by_department(department: str, db: AsyncSession = Depends(get_db)):
    """Recupera gli ospedali filtrati per reparto."""
    query = select(Hospital).filter(
        Hospital.department == department,
        Hospital.is_active == True
    )
    result = await db.execute(query)
    hospitals = result.scalars().all()
    return hospitals

@app.get("/hospitals/stats/overcrowded", response_model=List[HospitalResponse])
async def get_overcrowded_hospitals(threshold: float = 100.0, db: AsyncSession = Depends(get_db)):
    """Recupera gli ospedali con indice di sovraffollamento superiore alla soglia."""
    query = select(Hospital).filter(
        Hospital.overcrowding_index > threshold,
        Hospital.is_active == True
    )
    result = await db.execute(query)
    hospitals = result.scalars().all()
    return hospitals

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 