from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
from bs4 import BeautifulSoup
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class BaseArnasCivicoScraper(BaseHospitalScraper):
    """
    Classe base per gli scraper dei PS dell'ARNAS Civico.
    Implementa la logica comune per il parsing della pagina.
    """
    BASE_URL = "https://www.arnascivico.it/index.php/assistenza-ospedaliera/3415-attesa-al-pronto-soccorso"
    
    # Mappatura dei codici colore dell'ARNAS ai nostri
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
            
            # Cerca il contenuto dell'articolo
            article_body = soup.find('div', {'itemprop': 'articleBody'})
            if not article_body:
                self.logger.warning("Contenuto dell'articolo non trovato")
                return None
            
            # Cerca la sezione dell'ospedale specifico cercando il testo "Totale pazienti al P.S."
            hospital_section = None
            tables = article_body.find_all('table', class_='gridtable')
            
            # Identifica la sezione corretta in base al tipo di PS
            if "Civico" in self.hospital_name:
                # Per il PS Adulti, prendiamo la prima tabella
                hospital_section = tables[0] if tables else None
            else:
                # Per il PS Pediatrico, prendiamo la seconda tabella
                hospital_section = tables[1] if len(tables) > 1 else None
            
            if not hospital_section:
                self.logger.warning(f"Tabella non trovata per {self.hospital_name}")
                return None
            
            # Cerca la data di aggiornamento in diversi formati e posizioni
            update_time = None
            
            # Pattern per le date più comuni
            date_patterns = [
                r'(?:aggiornato|aggiornata)\s+al\s+(\d{2}/\d{2}/\d{4})\s+(?:ore\s+)?(\d{2}:\d{2}(?::\d{2})?)',
                r'(?:aggiornato|aggiornata)\s+al\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}[:.]\d{2}(?:[:.]\d{2})?)',
                r'(?:aggiornato|aggiornata)\s+alle\s+ore\s+(\d{2}:\d{2}(?::\d{2})?)\s+del\s+(\d{2}/\d{2}/\d{4})',
                r'(?:situazione|dati)\s+al\s+(\d{2}/\d{2}/\d{4})\s+(?:ore\s+)?(\d{2}:\d{2}(?::\d{2})?)'
            ]
            
            # Cerca in tutto il testo dell'articolo
            article_text = article_body.get_text()
            
            for pattern in date_patterns:
                match = re.search(pattern, article_text, re.IGNORECASE)
                if match:
                    # Estrai data e ora dai gruppi
                    groups = match.groups()
                    if len(groups) == 2:
                        date_str = groups[0]
                        time_str = groups[1].replace('.', ':')  # Normalizza il separatore
                        
                        # Se il tempo non include i secondi, aggiungi :00
                        if len(time_str) == 5:
                            time_str += ":00"
                        
                        try:
                            update_time = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                            self.logger.debug(f"Data aggiornamento trovata: {update_time} (pattern: {pattern})")
                            break
                        except ValueError as e:
                            self.logger.warning(f"Errore nel parsing della data '{date_str} {time_str}': {str(e)}")
                            continue
            
            if not update_time:
                # Se non troviamo una data valida, usiamo la data corrente
                self.logger.warning(f"Data di aggiornamento non trovata per {self.hospital_name}, uso data corrente")
                update_time = datetime.utcnow()
            
            # Estrai i dati dalle righe
            data = {
                'in_attesa': {},
                'in_trattamento': {},
                'in_osservazione': {},
                'last_update': update_time
            }
            
            # Processa le righe della tabella
            rows = hospital_section.find_all('tr')[1:-1]  # Salta header e totali
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                color = cells[0].text.strip().upper()
                if color not in self.COLOR_MAPPING:
                    continue
                
                try:
                    data['in_attesa'][color] = int(cells[1].text.strip() or '0')
                    data['in_trattamento'][color] = int(cells[2].text.strip() or '0')
                    data['in_osservazione'][color] = int(cells[3].text.strip() or '0')
                    self.logger.debug(f"Processata riga per {color}: {data['in_attesa'][color]}, {data['in_trattamento'][color]}, {data['in_osservazione'][color]}")
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Errore nel parsing dei numeri per {color}: {str(e)}")
                    continue
            
            self.logger.info(f"Dati estratti con successo per {self.hospital_name}")
            return data
            
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati per {self.hospital_name}: {str(e)}", exc_info=True)
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
                if not data[status]:
                    self.logger.warning(f"Nessun dato trovato per lo stato {status} in {self.hospital_name}")
                    return False
                    
                for color, count in data[status].items():
                    if not isinstance(count, int):
                        self.logger.warning(f"Conteggio non valido per {color} in {status}: {count} non è un intero")
                        return False
                    if count < 0:
                        self.logger.warning(f"Conteggio negativo per {color} in {status}: {count}")
                        return False
            
            # Verifica la presenza della data di aggiornamento
            if not data.get('last_update'):
                self.logger.warning(f"Data di aggiornamento mancante per {self.hospital_name}")
                return False
            
            # Log dei dati validi
            self.logger.debug(f"Dati validati per {self.hospital_name}:")
            self.logger.debug(f"- In attesa: {data['in_attesa']}")
            self.logger.debug(f"- In trattamento: {data['in_trattamento']}")
            self.logger.debug(f"- In osservazione: {data['in_osservazione']}")
            self.logger.debug(f"- Data aggiornamento: {data['last_update']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione per {self.hospital_name}: {str(e)}", exc_info=True)
            return False
    
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

class PoCivicoAdultiScraper(BaseArnasCivicoScraper):
    """Scraper per il P.O. Civico e Benfratelli (PS Adulti)"""
    hospital_code = HospitalCode.PO_CIVICO_ADULTI
    hospital_name = "PRONTO SOCCORSO ADULTI"
    total_beds = 30  # Numero di posti letto stimato

class PoCivicoPediatricoScraper(BaseArnasCivicoScraper):
    """Scraper per il P.O. Giovanni Di Cristina (PS Pediatrico)"""
    hospital_code = HospitalCode.PO_CIVICO_PEDIATRICO
    hospital_name = "PRONTO SOCCORSO PEDIATRICO"
    total_beds = 15  # Numero di posti letto stimato 