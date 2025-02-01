from typing import Dict, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from ..base import BaseHospitalScraper
from ...schemas import HospitalStatusCreate
from ..hospital_codes import HospitalCode

class OspedaliRiunitiPalermoScraper(BaseHospitalScraper):
    """
    Scraper per gli Ospedali Riuniti di Palermo.
    Gestisce tre pronto soccorso:
    - P.O. Cervello (Adulti)
    - P.O. Villa Sofia (Adulti)
    - P.O. Cervello (Pediatrico)
    """
    
    # URL base per lo scraping
    BASE_URL = "https://www.ospedaliriunitipalermo.it/amministrazione-trasparente/servizi-erogati/liste-di-attesa/pazienti-in-attesa-al-pronto-soccorso/"
    
    def __init__(self, hospital_id: int, config: Dict[str, Any]):
        super().__init__(hospital_id, config)
        # Mappa tra ID ospedale e selettore CSS
        self.hospital_selectors = {
            HospitalCode.PO_CERVELLO_ADULTI: ".olo-container-single-hospital.cervello",
            HospitalCode.PO_VILLA_SOFIA_ADULTI: ".olo-container-single-hospital.villaSofia",
            HospitalCode.PO_CERVELLO_PEDIATRICO: ".olo-container-single-hospital:not(.cervello):not(.villaSofia)"
        }
    
    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati per l'ospedale specificato.
        
        Returns:
            HospitalStatusCreate: Dati aggiornati dell'ospedale
        """
        self.logger.info(f"Inizio scraping per {self.hospital_code}")
        
        try:
            # Recupera la pagina
            html = await self.get_page(self.BASE_URL)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Estrai la data di aggiornamento
            update_div = soup.select_one(".olo-row-dati-aggiornati-al")
            external_last_update = self._parse_update_date(update_div.text if update_div else "")
            
            # Seleziona il container dell'ospedale corretto
            selector = self.hospital_selectors.get(self.hospital_code)
            if not selector:
                raise ValueError(f"Selettore non trovato per {self.hospital_code}")
                
            hospital_div = soup.select_one(selector)
            if not hospital_div:
                raise ValueError(f"Container non trovato per {self.hospital_code}")
            
            # Estrai i dati
            total_patients = self._extract_number(hospital_div, ".olo-number-pazienti.tot")
            waiting_patients = self._extract_number(hospital_div, ".olo-number-pazienti.wait")
            
            # Estrai i codici colore
            codes = {
                'red': self._extract_number(hospital_div, ".olo-codice-red .olo-number-codice"),
                'orange': self._extract_number(hospital_div, ".olo-codice-orange .olo-number-codice"),
                'azure': self._extract_number(hospital_div, ".olo-codice-azure .olo-number-codice"),
                'green': self._extract_number(hospital_div, ".olo-codice-green .olo-number-codice"),
                'white': self._extract_number(hospital_div, ".olo-codice-grey .olo-number-codice")
            }
            
            # Determina il codice colore dominante
            color_code = self._determine_color_code(codes)
            
            # Estrai l'indice di sovraffollamento
            overcrowding = self._extract_overcrowding(hospital_div)
            
            # Calcola il tempo di attesa stimato basato sul sovraffollamento
            waiting_time = self._estimate_waiting_time(overcrowding, codes)
            
            self.logger.info(
                f"Scraping completato per {self.hospital_code}: "
                f"pazienti={total_patients}, "
                f"in attesa={waiting_patients}, "
                f"colore={color_code}, "
                f"tempo stimato={waiting_time}min"
            )
            
            return HospitalStatusCreate(
                hospital_id=self.hospital_id,
                waiting_time=waiting_time,
                color_code=color_code,
                available_beds=max(0, 100 - total_patients),  # Stima basata sul totale pazienti
                external_last_update=external_last_update
            )
            
        except Exception as e:
            self.logger.error(f"Errore durante lo scraping: {str(e)}", exc_info=True)
            raise
    
    def _parse_update_date(self, date_str: str) -> Optional[datetime]:
        """Converte la stringa della data in oggetto datetime."""
        try:
            # Estrai la data dal formato "Situazione aggiornata al 1 Febbraio 2025 19:27"
            match = re.search(r'(\d+)\s+(\w+)\s+(\d{4})\s+(\d{2}):(\d{2})', date_str)
            if not match:
                return None
                
            day, month, year, hour, minute = match.groups()
            
            # Mappa dei mesi in italiano
            months = {
                'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
                'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
                'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
            }
            
            month_num = months.get(month.lower())
            if not month_num:
                return None
                
            return datetime(
                int(year), month_num, int(day),
                int(hour), int(minute)
            )
            
        except Exception as e:
            self.logger.error(f"Errore nel parsing della data '{date_str}': {str(e)}")
            return None
    
    def _extract_number(self, container: BeautifulSoup, selector: str) -> int:
        """Estrae un numero da un elemento HTML."""
        try:
            element = container.select_one(selector)
            return int(element.text.strip()) if element else 0
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Errore nell'estrazione del numero da {selector}: {str(e)}")
            return 0
    
    def _determine_color_code(self, codes: Dict[str, int]) -> str:
        """
        Determina il codice colore dominante basato sui conteggi.
        Priorità: red > orange > azure > green > white
        """
        if codes['red'] > 0:
            return 'red'
        elif codes['orange'] > 0:
            return 'orange'
        elif codes['azure'] > 0:
            return 'blue'  # Normalizzato a blue per lo standard SpitAlert
        elif codes['green'] > 0:
            return 'green'
        elif codes['white'] > 0:
            return 'white'
        return 'unknown'
    
    def _extract_overcrowding(self, container: BeautifulSoup) -> float:
        """Estrae l'indice di sovraffollamento."""
        try:
            element = container.select_one(".olo-row-indice-sovraffollamento span")
            if element:
                # Rimuovi il simbolo % e converti in float
                return float(element.text.replace('%', '').strip()) / 100
            return 1.0
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Errore nell'estrazione dell'indice di sovraffollamento: {str(e)}")
            return 1.0
    
    def _estimate_waiting_time(self, overcrowding: float, codes: Dict[str, int]) -> int:
        """
        Stima il tempo di attesa basato sull'indice di sovraffollamento
        e sul numero di pazienti per codice colore.
        """
        # Tempi base di attesa per codice (in minuti)
        base_times = {
            'red': 0,      # Accesso immediato
            'orange': 15,  # Massimo 15 minuti
            'azure': 60,   # 1 ora
            'green': 120,  # 2 ore
            'white': 240   # 4 ore
        }
        
        # Calcola il tempo medio pesato
        total_patients = sum(codes.values())
        if total_patients == 0:
            return 0
            
        weighted_time = sum(
            codes[color] * base_times[color]
            for color in codes
        ) / total_patients
        
        # Applica il fattore di sovraffollamento
        return int(weighted_time * overcrowding)
    
    async def validate_data(self) -> bool:
        """Valida i dati ottenuti dallo scraping."""
        try:
            data = await self.scrape()
            return all([
                data.waiting_time is not None and data.waiting_time >= 0,
                data.color_code != "unknown",
                data.available_beds is not None and data.available_beds >= 0,
                data.external_last_update is not None
            ])
        except Exception as e:
            self.logger.error(f"Errore durante la validazione: {str(e)}")
            return False 