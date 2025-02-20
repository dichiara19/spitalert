from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
from bs4 import BeautifulSoup
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class PsSantEliaScraper(BaseHospitalScraper):
    """
    Scraper per il Pronto Soccorso del P.O. Sant'Elia di Caltanissetta.
    Utilizza la pagina del cruscotto dell'ASP di Caltanissetta.
    """
    hospital_code = HospitalCode.PS_SANTELIA
    BASE_URL = "https://cruscottops.asp.cl.it/caltanissetta.php"
    
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
            
            # Trova le righe della tabella
            rows = soup.find_all('tr')
            if not rows:
                self.logger.warning("Nessuna riga trovata nella tabella")
                return None
            
            # Estrai i dati dalle celle
            data = {
                'in_attesa': {},
                'in_trattamento': {}
            }
            
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Determina se è la riga "in attesa" o "in trattamento"
                row_type = 'in_attesa' if 'In attesa' in row.text else 'in_trattamento' if 'In trattamento' in row.text else None
                if not row_type:
                    continue
                
                # Estrai i numeri dalle celle
                data[row_type] = {
                    'ROSSO': int(cells[0].text.strip() or '0'),
                    'ARANCIONE': int(cells[1].text.strip() or '0'),
                    'AZZURRO': int(cells[2].text.strip() or '0'),
                    'VERDE': int(cells[3].text.strip() or '0'),
                    'BIANCO': int(cells[4].text.strip() or '0')
                }
            
            # Estrai la data di aggiornamento
            update_div = soup.select_one('.update-time')
            if update_div:
                data['last_update'] = self._parse_update_date(update_div.text)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati: {str(e)}")
            return None
    
    def _parse_update_date(self, date_str: str) -> Optional[datetime]:
        """
        Converte la stringa della data in oggetto datetime.
        Formato atteso: "Aggiornamento: DD-MM-YYYY HH:MM"
        """
        try:
            # Estrai la data dal formato
            match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})', date_str)
            if not match:
                return None
                
            day, month, year, hour, minute = match.groups()
            return datetime(
                int(year), int(month), int(day),
                int(hour), int(minute)
            )
            
        except Exception as e:
            self.logger.error(f"Errore nel parsing della data '{date_str}': {str(e)}")
            return None
    
    def _get_color_and_count(self, data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Determina il codice colore più critico e il numero totale di pazienti.
        
        Args:
            data: Dizionario con i dati grezzi
            
        Returns:
            Tuple[str, int]: (codice colore normalizzato, totale pazienti)
        """
        # Ordine di priorità dei colori (dal più al meno critico)
        priority = ['ROSSO', 'ARANCIONE', 'AZZURRO', 'VERDE', 'BIANCO']
        
        # Calcola il totale dei pazienti in attesa
        total_waiting = sum(data['in_attesa'].values())
        
        # Trova il colore più critico con almeno un paziente in attesa
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
            
            # Somma i pazienti in attesa e in trattamento per ogni colore
            total_by_color = {
                color: data['in_attesa'].get(color, 0) + data['in_trattamento'].get(color, 0)
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
            raise ValueError("Impossibile recuperare i dati dal cruscotto")
        
        # Determina il codice colore e il numero di pazienti
        color_code, patients_waiting = self._get_color_and_count(data)
        
        # Usa il metodo ensure_color_distribution per garantire la presenza della distribuzione
        color_distribution = await self.get_color_distribution()
        if not color_distribution:
            color_distribution = self.ensure_color_distribution(data['in_attesa'])
        
        # Calcola il numero totale di pazienti (in attesa + in trattamento)
        total_patients = sum(data['in_attesa'].values()) + sum(data['in_trattamento'].values())
        
        # Stima il numero di posti letto disponibili (assumiamo una capacità di 30 posti)
        available_beds = max(0, 30 - total_patients)
        
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
                return False
            
            # Verifica che tutti i conteggi siano numeri non negativi
            for status in ['in_attesa', 'in_trattamento']:
                if not all(isinstance(v, int) and v >= 0 for v in data[status].values()):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione: {str(e)}")
            return False 