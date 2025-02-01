from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Hospital
from ..scrapers.hospital_codes import HospitalCode, HospitalRegistry
from ..database import get_db
import logging

logger = logging.getLogger(__name__)

# Definizione statica degli ospedali
HOSPITALS_DATA: Dict[HospitalCode, Dict[str, Any]] = {
    HospitalCode.PO_CERVELLO_ADULTI: {
        "name": "P.O. Cervello",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Via Trabucco, 180",
        "latitude": 38.154466,
        "longitude": 13.314139,
        "zip_code": "90146"
    },
    HospitalCode.PO_CERVELLO_PEDIATRICO: {
        "name": "P.O. Cervello",
        "department": "Pronto Soccorso Pediatrico",
        "city": "Palermo",
        "province": "PA",
        "address": "Via Trabucco, 180",
        "latitude": 38.154466,
        "longitude": 13.314139,
        "zip_code": "90146"
    },
    HospitalCode.PO_VILLA_SOFIA_ADULTI: {
        "name": "P.O. Villa Sofia",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Piazza Salerno, 1",
        "latitude": 38.154399,
        "longitude": 13.336450,
        "zip_code": "90146"
    }
}

async def get_existing_hospitals(db: AsyncSession) -> Dict[str, Hospital]:
    """
    Recupera gli ospedali esistenti dal database.
    
    Args:
        db: Sessione database
        
    Returns:
        Dict[str, Hospital]: Dizionario degli ospedali esistenti
    """
    query = select(Hospital)
    result = await db.execute(query)
    hospitals = result.scalars().all()
    return {f"{h.name}_{h.department}": h for h in hospitals}

async def init_hospitals() -> None:
    """
    Inizializza gli ospedali nel database se non esistono già.
    Registra anche i mapping nel HospitalRegistry.
    """
    async for db in get_db():
        try:
            # Recupera gli ospedali esistenti
            existing = await get_existing_hospitals(db)
            
            # Lista degli ospedali aggiunti in questa esecuzione
            added: List[str] = []
            updated: List[str] = []
            
            for code, data in HOSPITALS_DATA.items():
                hospital_key = f"{data['name']}_{data['department']}"
                
                if hospital_key in existing:
                    # Aggiorna i dati se necessario
                    hospital = existing[hospital_key]
                    was_updated = False
                    
                    for key, value in data.items():
                        if getattr(hospital, key) != value:
                            setattr(hospital, key, value)
                            was_updated = True
                    
                    if was_updated:
                        updated.append(hospital_key)
                        
                    # Registra il mapping anche se l'ospedale esisteva già
                    HospitalRegistry.register(hospital.id, code)
                    
                else:
                    # Crea nuovo ospedale
                    hospital = Hospital(**data)
                    db.add(hospital)
                    await db.flush()  # Per ottenere l'ID
                    
                    # Registra il mapping
                    HospitalRegistry.register(hospital.id, code)
                    added.append(hospital_key)
            
            if added or updated:
                await db.commit()
                
                if added:
                    logger.info(f"Aggiunti {len(added)} nuovi ospedali: {', '.join(added)}")
                if updated:
                    logger.info(f"Aggiornati {len(updated)} ospedali: {', '.join(updated)}")
            else:
                logger.info("Nessun nuovo ospedale da aggiungere")
                
        except Exception as e:
            await db.rollback()
            logger.error(f"Errore durante l'inizializzazione degli ospedali: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_hospitals()) 