from typing import Dict, Any, Type
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode, HospitalRegistry
from ..core.logging import LoggerMixin

class ScraperFactory(LoggerMixin):
    """
    Factory per la creazione di scraper specifici per ogni ospedale.
    """
    
    _scrapers: Dict[HospitalCode, Type[BaseHospitalScraper]] = {}
    
    @classmethod
    def register_scraper(cls, scraper_class: Type[BaseHospitalScraper]) -> None:
        """
        Registra un nuovo scraper nella factory.
        
        Args:
            scraper_class: Classe dello scraper da registrare
        
        Raises:
            AttributeError: Se la classe non ha definito l'attributo hospital_code
            ValueError: Se il codice ospedale è già registrato
        """
        hospital_code = scraper_class.get_hospital_code()
        
        if hospital_code in cls._scrapers:
            raise ValueError(
                f"Scraper già registrato per il codice ospedale: {hospital_code}"
            )
        
        cls._scrapers[hospital_code] = scraper_class
        cls.logger.info(
            f"Registrato scraper {scraper_class.__name__} "
            f"per l'ospedale {hospital_code}"
        )
    
    @classmethod
    def create_scraper(cls, hospital_id: int, config: Dict[str, Any]) -> BaseHospitalScraper:
        """
        Crea una nuova istanza dello scraper appropriato.
        
        Args:
            hospital_id: ID dell'ospedale nel database
            config: Configurazione specifica per lo scraper
            
        Returns:
            BaseHospitalScraper: Istanza dello scraper appropriato
            
        Raises:
            ValueError: Se nessuno scraper è registrato per l'ospedale
        """
        # Ottiene il codice ospedale dal registry
        hospital_code = HospitalRegistry.get_code(hospital_id)
        if not hospital_code:
            raise ValueError(
                f"Nessun codice ospedale registrato per l'ID: {hospital_id}"
            )
        
        # Ottiene la classe dello scraper
        scraper_class = cls._scrapers.get(hospital_code)
        if not scraper_class:
            raise ValueError(
                f"Nessuno scraper registrato per l'ospedale: {hospital_code}"
            )
        
        cls.logger.debug(
            f"Creazione scraper {scraper_class.__name__} "
            f"per ospedale {hospital_code} (ID: {hospital_id})"
        )
        
        return scraper_class(hospital_id=hospital_id, config=config)
    
    @classmethod
    def get_available_scrapers(cls) -> Dict[str, str]:
        """
        Restituisce un dizionario con i codici degli ospedali e i nomi degli scraper disponibili.
        
        Returns:
            Dict[str, str]: Dizionario {codice_ospedale: nome_scraper}
        """
        return {
            code.value: scraper.__name__ 
            for code, scraper in cls._scrapers.items()
        } 