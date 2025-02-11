from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
from bs4 import BeautifulSoup
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class BaseAspPalermoScraper(BaseHospitalScraper):
    """
    Classe base per gli scraper dei PS dell'ASP di Palermo.
    Implementa la logica comune per il parsing della pagina.
    """
    BASE_URL = "https://www.asppalermo.org/attese_ps/index_mod2.php"
    
    # Mappatura dei codici colore dell'ASP ai nostri
    COLOR_MAPPING = {
        'ROSSO': 'red',
        'ARANCIONE': 'orange',
        'AZZURRO': 'blue',
        'VERDE': 'green',
        'BIANCO': 'white'
    }
    
    async def _get_hospital_data(self) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati grezzi dalla pagina HTML.
        
        Returns:
            Optional[Dict[str, Any]]: Dizionario con i dati o None se non trovati
        """
        try:
            # Ottieni la pagina HTML
            html = await self.get_page(self.BASE_URL)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trova la sezione dell'ospedale specifico
            hospital_section = None
            for section in soup.find_all('div', class_='container'):
                if self.hospital_name in section.text:
                    hospital_section = section
                    break
                    
            if not hospital_section:
                self.logger.warning(f"Sezione non trovata per {self.hospital_name}")
                return None
            
            # Estrai la data di aggiornamento
            update_div = hospital_section.select_one('.alert-dark')
            update_time = None
            if update_div:
                update_match = re.search(r'(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})', update_div.text)
                if update_match:
                    date_str, time_str = update_match.groups()
                    update_time = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M:%S")
            
            # Trova la tabella dei dati
            table = hospital_section.find('table')
            if not table:
                return None
                
            # Estrai i dati dalle righe
            data = {
                'in_attesa': {},
                'in_trattamento': {},
                'in_osservazione': {},
                'last_update': update_time
            }
            
            rows = table.find_all('tr')[1:]  # Salta l'header
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                    
                row_type = row.find('th').text.strip().lower()
                if 'attesa' in row_type:
                    key = 'in_attesa'
                elif 'trattam' in row_type:
                    key = 'in_trattamento'
                elif 'osservaz' in row_type:
                    key = 'in_osservazione'
                else:
                    continue
                    
                data[key] = {
                    'ROSSO': int(cells[0].text.strip() or '0'),
                    'ARANCIONE': int(cells[1].text.strip() or '0'),
                    'AZZURRO': int(cells[2].text.strip() or '0'),
                    'VERDE': int(cells[3].text.strip() or '0'),
                    'BIANCO': int(cells[4].text.strip() or '0')
                }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati: {str(e)}")
            return None
    
    def _get_color_and_count(self, data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Determina il codice colore più critico e il numero totale di pazienti in attesa.
        
        Args:
            data: Dizionario con i dati grezzi
            
        Returns:
            Tuple[str, int]: (codice colore normalizzato, totale pazienti in attesa)
        """
        # Priorità dei colori (dal più al meno critico)
        priority = ['ROSSO', 'ARANCIONE', 'AZZURRO', 'VERDE', 'BIANCO']
        
        # Calcola il totale dei pazienti in attesa
        total_waiting = sum(data['in_attesa'].values())
        
        # Trova il colore più critico con almeno un paziente
        highest_color = 'unknown'
        for color in priority:
            if data['in_attesa'].get(color, 0) > 0:
                highest_color = self.COLOR_MAPPING[color]
                break
        
        return highest_color, total_waiting
    
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
            
            # Somma i pazienti per ogni colore (attesa + trattamento + osservazione)
            total_by_color = {
                color: (
                    data['in_attesa'].get(color, 0) +
                    data['in_trattamento'].get(color, 0) +
                    data['in_osservazione'].get(color, 0)
                )
                for color in self.COLOR_MAPPING.keys()
            }
            
            return ColorCodeDistribution(
                red=total_by_color['ROSSO'],
                orange=total_by_color['ARANCIONE'],
                blue=total_by_color['AZZURRO'],
                green=total_by_color['VERDE'],
                white=total_by_color['BIANCO']
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
            raise ValueError(f"Impossibile recuperare i dati per {self.hospital_name}")
        
        # Determina il codice colore e il numero di pazienti
        color_code, patients_waiting = self._get_color_and_count(data)
        
        # Usa il metodo ensure_color_distribution per garantire la presenza della distribuzione
        color_distribution = await self.get_color_distribution()
        if not color_distribution:
            color_distribution = self.ensure_color_distribution(data['in_attesa'])
        
        # Calcola il numero totale di pazienti
        total_patients = sum(
            sum(status.values())
            for status in [data['in_attesa'], data['in_trattamento'], data['in_osservazione']]
        )
        
        # Stima il numero di posti letto disponibili
        available_beds = max(0, self.total_beds - total_patients)
        
        # Stima il tempo di attesa basato sul numero di pazienti in attesa
        waiting_time = patients_waiting * 30  # 30 minuti per paziente come stima
        
        # Crea l'oggetto di risposta
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            color_code=color_code,
            waiting_time=waiting_time,
            patients_waiting=patients_waiting,
            available_beds=available_beds,
            color_distribution=color_distribution,
            last_updated=datetime.utcnow(),
            external_last_update=data.get('last_update', datetime.utcnow())
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
                self.logger.warning(f"Nessun dato trovato per {self.hospital_name}")
                return False
                
            # Verifica che tutti i conteggi siano numeri non negativi
            for status in ['in_attesa', 'in_trattamento', 'in_osservazione']:
                if not all(isinstance(v, int) and v >= 0 for v in data[status].values()):
                    self.logger.warning(f"Conteggi non validi per {status} in {self.hospital_name}")
                    return False
            
            # Verifica la presenza della data di aggiornamento
            if not data.get('last_update'):
                self.logger.warning(f"Data di aggiornamento mancante per {self.hospital_name}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione per {self.hospital_name}: {str(e)}")
            return False

class PsIngrassiaScraper(BaseAspPalermoScraper):
    """Scraper per il P.O. Ingrassia di Palermo"""
    hospital_code = HospitalCode.PS_INGRASSIA
    hospital_name = "PRONTO SOCCORSO - INGRASSIA DI PALERMO"
    total_beds = 13  # Come indicato nella pagina

class PsPartinicoScraper(BaseAspPalermoScraper):
    """Scraper per il P.O. Civico di Partinico"""
    hospital_code = HospitalCode.PS_PARTINICO
    hospital_name = "PRONTO SOCCORSO - CIVICO DI PARTINICO"
    total_beds = 11  # Come indicato nella pagina

class PsCorleoneScraper(BaseAspPalermoScraper):
    """Scraper per il P.O. 'Dei Bianchi' di Corleone"""
    hospital_code = HospitalCode.PS_CORLEONE
    hospital_name = "PRONTO SOCCORSO - P.O. 'DEI BIANCHI' DI CORLEONE"
    total_beds = 6  # Come indicato nella pagina

class PsPetraliaScraper(BaseAspPalermoScraper):
    """Scraper per il P.O. Madonna SS. dell'Alto di Petralia Sottana"""
    hospital_code = HospitalCode.PS_PETRALIA
    hospital_name = "PRONTO SOCCORSO - MADONNA SS. DELL'ALTO DI PETRALIA SOTTANA"
    total_beds = 10  # Come indicato nella pagina

class PsTerminiScraper(BaseAspPalermoScraper):
    """Scraper per il P.O. Cimino di Termini Imerese"""
    hospital_code = HospitalCode.PS_TERMINI
    hospital_name = "PRONTO SOCCORSO - CIMINO DI TERMINI IMERESE"
    total_beds = 8  # Come indicato nella pagina 