from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, ClassVar
from datetime import datetime
from ..schemas import HospitalStatusCreate
from ..core.logging import LoggerMixin
from .hospital_codes import HospitalCode
from ..utils.parsing import parse_waiting_time
from ..utils.http import HTTPClient

class BaseHospitalScraper(ABC, LoggerMixin):
    """
    Classe base astratta per gli scraper degli ospedali.
    Ogni nuovo scraper deve implementare questa interfaccia.
    """
    
    # Codice dell'ospedale, da definire in ogni classe derivata
    hospital_code: ClassVar[HospitalCode]
    
    def __init__(self, hospital_id: int, config: Dict[str, Any]):
        self.hospital_id = hospital_id
        self.config = config
        self.http_client = HTTPClient()
        self.logger.debug(
            f"Inizializzato scraper {self.__class__.__name__} "
            f"(codice: {self.hospital_code}, id: {hospital_id})"
        )
    
    @classmethod
    def get_hospital_code(cls) -> HospitalCode:
        """
        Restituisce il codice dell'ospedale associato a questo scraper.
        
        Returns:
            HospitalCode: Codice dell'ospedale
            
        Raises:
            AttributeError: Se il codice non è definito nella classe derivata
        """
        if not hasattr(cls, 'hospital_code'):
            raise AttributeError(
                f"La classe {cls.__name__} deve definire l'attributo 'hospital_code'"
            )
        return cls.hospital_code
    
    @abstractmethod
    async def scrape(self) -> HospitalStatusCreate:
        """
        Metodo principale per lo scraping dei dati.
        Deve essere implementato da ogni scraper specifico.
        
        Returns:
            HospitalStatusCreate: I dati dello stato dell'ospedale
        """
        pass
    
    @abstractmethod
    async def validate_data(self) -> bool:
        """
        Valida i dati ottenuti dallo scraping.
        Deve essere implementato da ogni scraper specifico.
        
        Returns:
            bool: True se i dati sono validi, False altrimenti
        """
        pass
    
    def normalize_color_code(self, color: str) -> str:
        """
        Normalizza il codice colore secondo lo standard SpitAlert.
        
        Args:
            color: Il codice colore originale dell'ospedale
            
        Returns:
            str: Il codice colore normalizzato
        """
        if not color:
            self.logger.warning("Codice colore vuoto o None")
            return 'unknown'
            
        color = color.lower().strip()
        
        # Mappatura dei colori standard
        color_mapping = {
            # Codici standard
            'white': 'white',
            'bianco': 'white',
            'green': 'green',
            'verde': 'green',
            'blue': 'blue',
            'blu': 'blue',
            'orange': 'orange',
            'arancione': 'orange',
            'red': 'red',
            'rosso': 'red',
            # Possibili varianti
            'yellow': 'orange',  # Alcuni ospedali usano giallo invece di arancione
            'giallo': 'orange',
        }
        
        normalized = color_mapping.get(color, 'unknown')
        if normalized == 'unknown':
            self.logger.warning(f"Codice colore non riconosciuto: {color}")
        
        return normalized
    
    def parse_waiting_time(self, time_str: str) -> Optional[int]:
        """
        Converte una stringa di tempo di attesa in minuti.
        
        Args:
            time_str: La stringa contenente il tempo di attesa
            
        Returns:
            Optional[int]: Il tempo di attesa in minuti, None se non valido
        """
        if not time_str:
            self.logger.warning("Stringa tempo di attesa vuota o None")
            return None
            
        try:
            # Rimuove spazi extra e converte in minuscolo
            time_str = time_str.lower().strip()
            
            # Gestisce diversi formati comuni
            if 'min' in time_str:
                return int(time_str.replace('min', '').strip())
            elif 'ora' in time_str or 'ore' in time_str:
                hours = float(time_str.replace('ore', '').replace('ora', '').strip())
                return int(hours * 60)
            elif ':' in time_str:  # formato HH:MM
                hours, minutes = map(int, time_str.split(':'))
                return hours * 60 + minutes
            else:
                # Assume che sia un numero in minuti
                return int(time_str)
        except (ValueError, TypeError) as e:
            self.logger.error(
                f"Errore nel parsing del tempo di attesa '{time_str}'",
                exc_info=True
            )
            return None
        
    async def get_page(self, url: str, **kwargs) -> str:
        """
        Recupera il contenuto di una pagina web.
        
        Args:
            url: URL della pagina
            **kwargs: Parametri aggiuntivi per la richiesta HTTP
            
        Returns:
            str: Contenuto della pagina
        """
        return await self.http_client.get_text(url, **kwargs)
        
    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Recupera e decodifica dati JSON da un endpoint.
        
        Args:
            url: URL dell'endpoint
            **kwargs: Parametri aggiuntivi per la richiesta HTTP
            
        Returns:
            Dict[str, Any]: Dati JSON decodificati
        """
        return await self.http_client.get_json(url, **kwargs) 