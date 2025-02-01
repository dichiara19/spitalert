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
        # Semaforo per limitare le chiamate concorrenti
        self._semaphore = Semaphore(settings.SCRAPE_CONCURRENT_TASKS)
        
    async def scrape_all_hospitals(self) -> Dict[str, bool]:
        """
        Esegue lo scraping per tutti gli ospedali registrati in parallelo.
        
        Returns:
            Dict[str, bool]: Dizionario con i risultati dello scraping per ogni ospedale
        """
        self.logger.info("Avvio scraping parallelo per tutti gli ospedali")
        
        # Recupera tutti gli ospedali
        query = select(Hospital)
        result = await self.db.execute(query)
        hospitals = result.scalars().all()
        
        if not hospitals:
            self.logger.warning("Nessun ospedale trovato nel database")
            return {}
        
        self.logger.info(
            f"Trovati {len(hospitals)} ospedali da processare. "
            f"Massimo {settings.SCRAPE_CONCURRENT_TASKS} task concorrenti"
        )
        
        # Crea i task per ogni ospedale
        tasks: List[Task] = []
        for hospital in hospitals:
            task = asyncio.create_task(
                self._scrape_hospital_with_semaphore(hospital),
                name=f"scrape_{hospital.name}"
            )
            tasks.append(task)
        
        # Attendi il completamento di tutti i task
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa i risultati
        hospital_results = {}
        successes = 0
        
        for hospital, result in zip(hospitals, results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Errore durante lo scraping dell'ospedale {hospital.name}",
                    exc_info=result
                )
                hospital_results[hospital.name] = False
            else:
                hospital_results[hospital.name] = result
                if result:
                    successes += 1
        
        self.logger.info(
            f"Scraping completato. Successi: {successes}/{len(hospitals)}"
        )
        return hospital_results
    
    async def _scrape_hospital_with_semaphore(self, hospital: Hospital) -> bool:
        """
        Wrapper per eseguire lo scraping di un ospedale con un semaforo.
        
        Args:
            hospital: L'ospedale da processare
            
        Returns:
            bool: True se lo scraping è avvenuto con successo, False altrimenti
        """
        try:
            async with self._semaphore:
                self.logger.debug(
                    f"Acquisito semaforo per l'ospedale {hospital.name}"
                )
                return await self.scrape_hospital(hospital.id)
        except Exception as e:
            self.logger.error(
                f"Errore durante lo scraping dell'ospedale {hospital.name}",
                exc_info=e
            )
            return False
    
    async def scrape_hospital(self, hospital_id: int) -> bool:
        """
        Esegue lo scraping per un singolo ospedale.
        
        Args:
            hospital_id: ID dell'ospedale
            
        Returns:
            bool: True se lo scraping è avvenuto con successo, False altrimenti
        """
        # Recupera l'ospedale
        query = select(Hospital).filter(Hospital.id == hospital_id)
        result = await self.db.execute(query)
        hospital = result.scalar_one_or_none()
        
        if not hospital:
            self.logger.error(f"Ospedale con ID {hospital_id} non trovato")
            return False
            
        try:
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
            except asyncio.TimeoutError:
                self.logger.error(
                    f"Timeout durante lo scraping dell'ospedale {hospital.name}"
                )
                return False
            
            # Aggiorna lo stato corrente
            current_status = await self._update_current_status(new_status)
            
            # Salva nello storico
            await self._save_to_history(new_status)
            
            await self.db.commit()
            
            self.logger.info(
                f"Scraping completato con successo per l'ospedale {hospital.name}. "
                f"Stato: {new_status.color_code}, "
                f"Tempo di attesa: {new_status.waiting_time} min"
            )
            return True
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(
                f"Errore durante lo scraping dell'ospedale {hospital.name}",
                exc_info=True
            )
            return False
    
    async def _update_current_status(self, new_status: HospitalStatusCreate) -> HospitalStatus:
        """
        Aggiorna lo stato corrente dell'ospedale.
        
        Args:
            new_status: Nuovi dati dello stato
            
        Returns:
            HospitalStatus: Lo stato aggiornato
        """
        # Cerca lo stato corrente
        query = select(HospitalStatus).filter(HospitalStatus.hospital_id == new_status.hospital_id)
        result = await self.db.execute(query)
        current = result.scalar_one_or_none()
        
        if current:
            self.logger.debug(f"Aggiornamento stato esistente per ospedale {new_status.hospital_id}")
            # Aggiorna lo stato esistente
            for key, value in new_status.model_dump().items():
                setattr(current, key, value)
            current.last_updated = datetime.utcnow()
        else:
            self.logger.debug(f"Creazione nuovo stato per ospedale {new_status.hospital_id}")
            # Crea un nuovo stato
            current = HospitalStatus(**new_status.model_dump())
            self.db.add(current)
        
        return current
    
    async def _save_to_history(self, status: HospitalStatusCreate) -> HospitalHistory:
        """
        Salva lo stato nella tabella storica.
        
        Args:
            status: Dati dello stato da salvare
            
        Returns:
            HospitalHistory: Il record storico creato
        """
        self.logger.debug(f"Salvataggio storico per ospedale {status.hospital_id}")
        
        history_entry = HospitalHistory(
            hospital_id=status.hospital_id,
            available_beds=status.available_beds,
            waiting_time=status.waiting_time,
            color_code=status.color_code,
            external_last_update=status.external_last_update
        )
        
        self.db.add(history_entry)
        return history_entry 