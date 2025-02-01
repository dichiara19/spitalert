from typing import Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import asyncio
from asyncio import Task, Semaphore

from ..models import Hospital, HospitalStatus, HospitalHistory
from ..scrapers.factory import ScraperFactory
from ..schemas import HospitalStatusCreate
from ..core.logging import LoggerMixin
from ..scrapers.hospital_codes import HospitalRegistry
from ..config import get_settings

settings = get_settings()

class ScraperService(LoggerMixin):
    def __init__(self, db: AsyncSession):
        self.db = db
        self._semaforo = Semaphore(settings.SCRAPE_CONCURRENT_TASKS)
        
    async def scrape_hospital(self, hospital_id: int) -> bool:
        """
        Esegue lo scraping per un singolo ospedale.
        
        Args:
            hospital_id: ID dell'ospedale
            
        Returns:
            bool: True se lo scraping è avvenuto con successo, False altrimenti
        """
        try:
            # Recupera l'ospedale
            query = select(Hospital).filter(Hospital.id == hospital_id)
            result = await self.db.execute(query)
            hospital = result.scalar_one_or_none()
            
            if not hospital:
                self.logger.error(f"Ospedale con ID {hospital_id} non trovato")
                return False
                
            self.logger.info(f"Inizio scraping per l'ospedale {hospital.name}")
            
            # Verifica che l'ospedale sia registrato nel registry
            if not HospitalRegistry.get_code(hospital_id):
                self.logger.error(
                    f"Ospedale {hospital.name} (ID: {hospital_id}) "
                    "non registrato nel registry"
                )
                return False
            
            # Crea lo scraper appropriato
            scraper = ScraperFactory.create_scraper(
                hospital_id=hospital_id,
                config={}
            )
            
            # Imposta un timeout per lo scraping
            try:
                async with asyncio.timeout(settings.SCRAPE_TIMEOUT):
                    # Valida i dati prima di salvarli
                    if not await scraper.validate_data():
                        self.logger.warning(
                            f"Validazione fallita per l'ospedale {hospital.name}"
                        )
                        return False
                    
                    # Esegue lo scraping
                    new_status = await scraper.scrape()
                    
                    # Salva i dati nello stato corrente
                    current_status = HospitalStatus(
                        hospital_id=hospital_id,
                        available_beds=new_status.available_beds,
                        waiting_time=new_status.waiting_time,
                        color_code=new_status.color_code,
                        external_last_update=new_status.external_last_update
                    )
                    self.db.add(current_status)
                    
                    # Salva i dati nella storia
                    history_entry = HospitalHistory(
                        hospital_id=hospital_id,
                        available_beds=new_status.available_beds,
                        waiting_time=new_status.waiting_time,
                        color_code=new_status.color_code,
                        external_last_update=new_status.external_last_update
                    )
                    self.db.add(history_entry)
                    
                    # Commit della transazione
                    try:
                        await self.db.commit()
                        self.logger.info(
                            f"Scraping completato per {hospital.name}: "
                            f"attesa={new_status.waiting_time}min, "
                            f"colore={new_status.color_code}, "
                            f"posti={new_status.available_beds}"
                        )
                        return True
                    except Exception as e:
                        await self.db.rollback()
                        self.logger.error(
                            f"Errore durante il salvataggio dei dati per {hospital.name}: {str(e)}",
                            exc_info=True
                        )
                        return False
                        
            except asyncio.TimeoutError:
                self.logger.error(
                    f"Timeout durante lo scraping dell'ospedale {hospital.name}"
                )
                return False
                
        except Exception as e:
            self.logger.error(
                f"Errore imprevisto durante lo scraping dell'ospedale {hospital_id}: {str(e)}",
                exc_info=True
            )
            return False
            
    async def scrape_all_hospitals(self) -> Dict[str, bool]:
        """
        Esegue lo scraping per tutti gli ospedali registrati.
        
        Returns:
            Dict[str, bool]: Dizionario con i risultati dello scraping per ogni ospedale
        """
        # Recupera tutti gli ospedali
        query = select(Hospital)
        result = await self.db.execute(query)
        hospitals = result.scalars().all()
        
        hospital_results = {}
        tasks = []
        
        for hospital in hospitals:
            # Crea un task per ogni ospedale
            task = asyncio.create_task(
                self._scrape_with_semaphore(hospital.id, hospital.name)
            )
            tasks.append(task)
            
        # Attendi il completamento di tutti i task
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa i risultati
        for hospital, result in zip(hospitals, results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Errore durante lo scraping di {hospital.name}: {str(result)}",
                    exc_info=True
                )
                hospital_results[hospital.name] = False
            else:
                hospital_results[hospital.name] = result
                
        successes = sum(1 for success in hospital_results.values() if success)
        self.logger.info(
            f"Scraping completato. Successi: {successes}/{len(hospitals)}"
        )
        
        return hospital_results
        
    async def _scrape_with_semaphore(self, hospital_id: int, hospital_name: str) -> bool:
        """
        Esegue lo scraping di un ospedale utilizzando un semaforo per limitare le chiamate concorrenti.
        
        Args:
            hospital_id: ID dell'ospedale
            hospital_name: Nome dell'ospedale per il logging
            
        Returns:
            bool: True se lo scraping è avvenuto con successo, False altrimenti
        """
        try:
            async with self._semaforo:
                self.logger.debug(f"Inizio scraping per {hospital_name}")
                return await self.scrape_hospital(hospital_id)
        except Exception as e:
            self.logger.error(
                f"Errore durante lo scraping con semaforo per {hospital_name}: {str(e)}",
                exc_info=True
            )
            return False 