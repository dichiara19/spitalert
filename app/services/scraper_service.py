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
        
    async def scrape_hospital(self, hospital_id: int, hospital_name: str) -> bool:
        """
        Esegue lo scraping per un singolo ospedale.
        
        Args:
            hospital_id: ID dell'ospedale
            hospital_name: Nome dell'ospedale
            
        Returns:
            bool: True se lo scraping è avvenuto con successo, False altrimenti
        """
        try:
            self.logger.info(f"Inizio scraping per l'ospedale {hospital_name}")
            
            # Verifica che l'ospedale sia registrato nel registry
            if not HospitalRegistry.get_code(hospital_id):
                self.logger.error(
                    f"Ospedale {hospital_name} (ID: {hospital_id}) "
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
                            f"Validazione fallita per l'ospedale {hospital_name}"
                        )
                        return False
                    
                    # Esegue lo scraping
                    new_status = await scraper.scrape()
                    
                    # Crea gli oggetti da salvare
                    current_status = HospitalStatus(
                        hospital_id=hospital_id,
                        available_beds=new_status.available_beds,
                        waiting_time=new_status.waiting_time,
                        color_code=new_status.color_code,
                        external_last_update=new_status.external_last_update
                    )
                    
                    history_entry = HospitalHistory(
                        hospital_id=hospital_id,
                        available_beds=new_status.available_beds,
                        waiting_time=new_status.waiting_time,
                        color_code=new_status.color_code,
                        external_last_update=new_status.external_last_update
                    )
                    
                    # Salva i dati
                    self.db.add(current_status)
                    self.db.add(history_entry)
                    
                    self.logger.info(
                        f"Scraping completato per {hospital_name}: "
                        f"attesa={new_status.waiting_time}min, "
                        f"colore={new_status.color_code}, "
                        f"posti={new_status.available_beds}"
                    )
                    return True
                        
            except asyncio.TimeoutError:
                self.logger.error(
                    f"Timeout durante lo scraping dell'ospedale {hospital_name}"
                )
                return False
            except Exception as e:
                self.logger.error(
                    f"Errore durante il salvataggio dei dati per {hospital_name}: {str(e)}",
                    exc_info=True
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
        async with self.db.begin():
            # Recupera tutti gli ospedali con una singola query
            query = (
                select(Hospital.id, Hospital.name)
                .order_by(Hospital.id)
            )
            result = await self.db.execute(query)
            hospitals = result.all()
            
            hospital_results = {}
            tasks = []
            
            for hospital_id, hospital_name in hospitals:
                # Crea un task per ogni ospedale
                task = asyncio.create_task(
                    self._scrape_with_semaphore(hospital_id, hospital_name)
                )
                tasks.append((hospital_name, task))
            
            # Attendi il completamento di tutti i task
            for hospital_name, task in tasks:
                try:
                    result = await task
                    hospital_results[hospital_name] = result
                except Exception as e:
                    self.logger.error(
                        f"Errore durante lo scraping di {hospital_name}: {str(e)}",
                        exc_info=True
                    )
                    hospital_results[hospital_name] = False
            
            successes = sum(1 for success in hospital_results.values() if success)
            self.logger.info(
                f"Scraping completato. Successi: {successes}/{len(hospitals)}"
            )
            
            # Commit esplicito alla fine di tutti gli scraping
            await self.db.commit()
            
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
                return await self.scrape_hospital(hospital_id, hospital_name)
        except Exception as e:
            self.logger.error(
                f"Errore durante lo scraping con semaforo per {hospital_name}: {str(e)}",
                exc_info=True
            )
            return False 