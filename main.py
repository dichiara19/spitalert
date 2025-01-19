from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, init_db, Hospital
from scheduler import setup_scheduler
from typing import List
from pydantic import BaseModel
from datetime import datetime
import logging
import sys
import os

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SpitAlert API",
    description="API per il monitoraggio del sovraffollamento nei pronto soccorso",
    version="1.0.0"
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specificare domini consentiti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

async def initialize_application():
    """Inizializza l'applicazione in modo sicuro."""
    try:
        logger.info("Verifica configurazione ambiente...")
        env = os.getenv("ENVIRONMENT", "development")
        logger.info(f"Ambiente: {env}")
        
        logger.info("Inizializzazione del database...")
        if not await init_db():
            raise RuntimeError("Inizializzazione del database fallita")
        
        logger.info("Avvio dello scheduler...")
        setup_scheduler()
        
        logger.info("Inizializzazione completata con successo")
        return True
    except Exception as e:
        logger.error(f"Errore fatale durante l'inizializzazione: {str(e)}")
        return False

@app.on_event("startup")
async def startup_event():
    """Gestisce l'avvio dell'applicazione."""
    if not await initialize_application():
        logger.critical("Impossibile avviare l'applicazione. Arresto in corso...")
        sys.exit(1)

@app.get("/")
async def health_check():
    """Endpoint di health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

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
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 