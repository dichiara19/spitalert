from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class BaseAspAgrigentoScraper(BaseHospitalScraper):
    """
    Classe base per gli scraper dei Pronto Soccorso dell'ASP di Agrigento.
    Tutti i PS condividono la stessa fonte dati HTML.
    """
    BASE_URL = "http://pswall.aspag.it/ps/listaattesa.php"
    
    # Mappatura dei codici colore dell'ASP ai nostri
    COLOR_MAPPING = {
        'ROSSO': 'red',
        'ARANCIONE': 'orange',
        'GIALLO': 'orange',  # L'ASP usa giallo, noi lo mappiamo a orange
        'VERDE': 'green',
        'AZZURRO': 'blue',
        'BIANCO': 'white'
    }
    
    async def _get_hospital_data(self) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati grezzi per l'ospedale specifico dalla tabella HTML.
        
        Returns:
            Optional[Dict[str, Any]]: Dizionario con i dati dell'ospedale o None se non trovato
        """
        try:
            # Ottieni la pagina HTML
            html = await self.get_page(self.BASE_URL)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerca la riga della tabella per questo ospedale
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                    
                hospital_name = cells[0].text.strip()
                if hospital_name == self.get_hospital_name():
                    # Estrai i dati dalle celle
                    return {
                        'ROSSO': int(cells[1].text.strip().split()[-1]),
                        'ARANCIONE': int(cells[2].text.strip().split()[-1]),
                        'GIALLO': int(cells[3].text.strip().split()[-1]),
                        'VERDE': int(cells[4].text.strip().split()[-1]),
                        'AZZURRO': int(cells[5].text.strip().split()[-1]),
                        'BIANCO': int(cells[6].text.strip().split()[-1])
                    }
            
            self.logger.warning(f"Ospedale {self.get_hospital_name()} non trovato nella tabella")
            return None
            
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati per {self.get_hospital_name()}: {str(e)}")
            return None
    
    def get_hospital_name(self) -> str:
        """
        Restituisce il nome dell'ospedale come appare nella tabella HTML.
        Da implementare nelle classi derivate.
        """
        raise NotImplementedError("Implementare nelle classi derivate")
    
    def _get_color_and_count(self, data: Dict[str, int]) -> Tuple[str, int]:
        """
        Determina il codice colore più critico e il numero totale di pazienti.
        
        Args:
            data: Dizionario con i conteggi per ogni codice colore
            
        Returns:
            Tuple[str, int]: (codice colore normalizzato, totale pazienti)
        """
        # Ordine di priorità dei colori (dal più al meno critico)
        priority = ['ROSSO', 'ARANCIONE', 'GIALLO', 'VERDE', 'AZZURRO', 'BIANCO']
        
        total_patients = sum(data.values())
        highest_color = 'unknown'
        
        # Trova il colore più critico con almeno un paziente
        for color in priority:
            if data[color] > 0:
                highest_color = self.COLOR_MAPPING[color]
                break
        
        return highest_color, total_patients
    
    async def get_color_distribution(self) -> Optional[ColorCodeDistribution]:
        """
        Recupera la distribuzione dei codici colore.
        
        Returns:
            Optional[ColorCodeDistribution]: Distribuzione dei codici colore o None in caso di errore
        """
        try:
            data = await self._get_hospital_data()
            if not data:
                return None
                
            return ColorCodeDistribution(
                red=data['ROSSO'],
                orange=data['ARANCIONE'] + data['GIALLO'],  # Sommiamo arancione e giallo
                blue=data['AZZURRO'],
                green=data['VERDE'],
                white=data['BIANCO']
            )
        except Exception as e:
            self.logger.error(f"Errore nel recupero della distribuzione colori: {str(e)}")
            return None
    
    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati dal Pronto Soccorso.
        
        Returns:
            HospitalStatusCreate: Dati formattati secondo lo schema SpitAlert
        """
        # Recupera i dati grezzi
        data = await self._get_hospital_data()
        if not data:
            raise ValueError(f"Impossibile recuperare i dati per {self.get_hospital_name()}")
        
        # Determina il codice colore e il numero di pazienti
        color_code, patients_waiting = self._get_color_and_count(data)
        
        # Usa il metodo ensure_color_distribution per garantire la presenza della distribuzione
        color_distribution = self.ensure_color_distribution(data)
        
        # Non abbiamo informazioni sui posti letto disponibili
        available_beds = 0
        
        # Non abbiamo informazioni sui tempi di attesa
        waiting_time = 0
        
        # Crea l'oggetto di risposta
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            color_code=color_code,
            waiting_time=waiting_time,
            patients_waiting=patients_waiting,
            available_beds=available_beds,
            color_distribution=color_distribution,
            last_updated=datetime.utcnow(),
            external_last_update=datetime.utcnow()  # La pagina mostra l'ultimo aggiornamento ma non lo estraiamo per ora
        )
    
    async def validate_data(self) -> bool:
        """
        Valida i dati ottenuti dallo scraping.
        
        Returns:
            bool: True se i dati sono validi, False altrimenti
        """
        try:
            data = await self._get_hospital_data()
            if not data:
                return False
                
            # Verifica che tutti i conteggi siano numeri non negativi
            return all(isinstance(v, int) and v >= 0 for v in data.values())
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione: {str(e)}")
            return False

class PsSciacca(BaseAspAgrigentoScraper):
    """Scraper per il P.O. 'San Giovanni Paolo II' di Sciacca"""
    hospital_code = HospitalCode.PS_SCIACCA
    
    def get_hospital_name(self) -> str:
        return "PS SCIACCA"

class PsRibera(BaseAspAgrigentoScraper):
    """Scraper per il P.O. 'F.lli Parlapiano' di Ribera"""
    hospital_code = HospitalCode.PS_RIBERA
    
    def get_hospital_name(self) -> str:
        return "PS RIBERA"

class PsAgrigento(BaseAspAgrigentoScraper):
    """Scraper per il P.O. 'S. Giovanni Di Dio' di Agrigento"""
    hospital_code = HospitalCode.PS_AGRIGENTO
    
    def get_hospital_name(self) -> str:
        return "PS AGRIGENTO"

class PsCanicatti(BaseAspAgrigentoScraper):
    """Scraper per il P.O. di Canicattì"""
    hospital_code = HospitalCode.PS_CANICATTI
    
    def get_hospital_name(self) -> str:
        return "PS CANICATTI'"

class PsLicata(BaseAspAgrigentoScraper):
    """Scraper per l'U.O.C. Medicina e Chirurgia di Accettazione e Urgenza di Licata"""
    hospital_code = HospitalCode.PS_LICATA
    
    def get_hospital_name(self) -> str:
        return "PS LICATA" 