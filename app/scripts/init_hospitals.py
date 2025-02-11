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
        "longitude": 13.314139
    },
    HospitalCode.PO_CERVELLO_PEDIATRICO: {
        "name": "P.O. Cervello",
        "department": "Pronto Soccorso Pediatrico",
        "city": "Palermo",
        "province": "PA",
        "address": "Via Trabucco, 180",
        "latitude": 38.154466,
        "longitude": 13.314139
    },
    HospitalCode.PO_VILLA_SOFIA_ADULTI: {
        "name": "P.O. Villa Sofia",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Piazza Salerno, 1",
        "latitude": 38.154399,
        "longitude": 13.336450
    },
    HospitalCode.POLICLINICO_PALERMO: {
        "name": "P.O. Policlinico \"Paolo Giaccone\"",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Via del Vespro, 129",
        "latitude": 38.103469,
        "longitude": 13.3622403
    },
    HospitalCode.PS_SCIACCA: {
        "name": "P.O. \"San Giovanni Paolo II\" di Sciacca",
        "department": "Pronto Soccorso Adulti",
        "city": "Sciacca",
        "province": "AG",
        "address": "Via Pompei",
        "latitude": 37.5086,
        "longitude": 13.0778
    },
    HospitalCode.PS_RIBERA: {
        "name": "P.O. \"F.lli Parlapiano\" di Ribera",
        "department": "Pronto Soccorso Adulti",
        "city": "Ribera",
        "province": "AG",
        "address": "Via Circonvallazione",
        "latitude": 37.3343,
        "longitude": 13.2686
    },
    HospitalCode.PS_LICATA: {
        "name": "P.O. Medicina e Chirurgia di Accettazione e Urgenza di Licata",
        "department": "Pronto Soccorso Adulti",
        "city": "Licata",
        "province": "AG",
        "address": "Contrada Cannavecchia",
        "latitude": 37.1018,
        "longitude": 13.9372
    },
    HospitalCode.PS_CANICATTI: {
        "name": "P.O. Barone Lombardo di Canicattì",
        "department": "Pronto Soccorso Adulti",
        "city": "Canicattì",
        "province": "AG",
        "address": "Via Giudice Antonino Saetta",
        "latitude": 37.3571,
        "longitude": 13.8471
    },
    HospitalCode.PS_AGRIGENTO: {
        "name": "P.O. \"San Giovanni di Dio\" di Agrigento",
        "department": "Pronto Soccorso Adulti",
        "city": "Agrigento",
        "province": "AG",
        "address": "Contrada Consolida",
        "latitude": 37.3220,
        "longitude": 13.5896
    },
    HospitalCode.PS_SANTELIA: {
        "name": "P.O. Sant'Elia",
        "department": "Pronto Soccorso Adulti",
        "city": "Caltanissetta",
        "province": "CL",
        "address": "Via Luigi Russo, 6",
        "latitude": 37.489289,
        "longitude": 14.031392
    },
    HospitalCode.PS_INGRASSIA: {
        "name": "P.O. Ingrassia",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Corso Calatafimi, 1002",
        "latitude": 38.107778,
        "longitude": 13.339722
    },
    HospitalCode.PS_PARTINICO: {
        "name": "P.O. Civico di Partinico",
        "department": "Pronto Soccorso Adulti",
        "city": "Partinico",
        "province": "PA",
        "address": "Contrada Sicciarotta",
        "latitude": 38.047222,
        "longitude": 13.116944
    },
    HospitalCode.PS_CORLEONE: {
        "name": "P.O. 'Dei Bianchi'",
        "department": "Pronto Soccorso Adulti",
        "city": "Corleone",
        "province": "PA",
        "address": "Via Don Giovanni Colletto",
        "latitude": 37.812500,
        "longitude": 13.302778
    },
    HospitalCode.PS_PETRALIA: {
        "name": "P.O. Madonna SS. dell'Alto",
        "department": "Pronto Soccorso Adulti",
        "city": "Petralia Sottana",
        "province": "PA",
        "address": "Contrada Sant'Elia",
        "latitude": 37.810833,
        "longitude": 14.095833
    },
    HospitalCode.PS_TERMINI: {
        "name": "P.O. Cimino",
        "department": "Pronto Soccorso Adulti",
        "city": "Termini Imerese",
        "province": "PA",
        "address": "Via Salvatore Cimino, 2",
        "latitude": 37.985833,
        "longitude": 13.701944
    },
    HospitalCode.PO_CIVICO_ADULTI: {
        "name": "P.O. Civico e Benfratelli",
        "department": "Pronto Soccorso Adulti",
        "city": "Palermo",
        "province": "PA",
        "address": "Piazza Nicola Leotta, 4",
        "latitude": 38.111389,
        "longitude": 13.359722
    },
    HospitalCode.PO_CIVICO_PEDIATRICO: {
        "name": "P.O. Giovanni Di Cristina",
        "department": "Pronto Soccorso Pediatrico",
        "city": "Palermo",
        "province": "PA",
        "address": "Via dei Benedettini, 1",
        "latitude": 38.109722,
        "longitude": 13.361944
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