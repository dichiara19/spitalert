from typing import Dict, Any, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import httpx
import re

from .base import BaseHospitalScraper
from app.hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

logger = logging.getLogger(__name__)

class AoPapardoScraper(BaseHospitalScraper):
    """Scraper per l'AO Papardo di Messina."""
    
    BASE_URL = "https://www.aopapardo.it/"
    hospital_code = HospitalCode.AO_PAPARDO

    def __init__(self, hospital_id: int, config: Dict[str, Any]):
        super().__init__(hospital_id, config)
        self.color_mapping = {
            "#FFFFFF": "white",    # Bianco
            "#36DB00": "green",    # Verde
            "#04E1F7": "blue",     # Azzurro/Blu
            "#F77A04": "orange",   # Arancione
            "#FF0000": "red"       # Rosso
        }

    async def _get_hospital_data(self) -> Dict[str, Any]:
        """Recupera i dati dal sito dell'ospedale."""
        try:
            # Ottieni la pagina HTML
            html = await self.get_page(self.BASE_URL)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Inizializza il dizionario dei dati
            data = {
                'patients': {},
                'last_update': None
            }

            # Trova la data di aggiornamento
            update_div = soup.find('div', {'class': 'hidden-sm hidden-xs pull-right small'})
            if update_div:
                update_text = update_div.text.strip()
                data['last_update'] = self._parse_update_date(update_text)
                self.logger.debug(f"Data di aggiornamento trovata: {data['last_update']}")

            # Trova tutti i div con classe semaforo_ps
            semaforo_divs = soup.find_all('div', {'class': 'semaforo_ps'})
            for div in semaforo_divs:
                # Estrai il colore dal background-color
                style = div.get('style', '')
                color_match = re.search(r'background-color:\s*(#[A-F0-9]{6})', style)
                if not color_match:
                    continue

                hex_color = color_match.group(1).upper()
                if hex_color not in self.color_mapping:
                    self.logger.warning(f"Colore non riconosciuto: {hex_color}")
                    continue

                # Trova il numero di pazienti nel div successivo
                patient_div = div.find_next('div')
                if not patient_div:
                    continue

                patient_span = patient_div.find('span')
                if not patient_span:
                    continue

                try:
                    patients = int(patient_span.text.strip())
                    std_color = self.color_mapping[hex_color]
                    data['patients'][std_color] = data['patients'].get(std_color, 0) + patients
                    self.logger.debug(f"Trovati {patients} pazienti per il colore {std_color}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Errore nel parsing del numero di pazienti: {e}")

            return data

        except Exception as e:
            self.logger.error(f"Errore durante lo scraping: {e}")
            raise

    def _parse_update_date(self, date_str: str) -> Optional[datetime]:
        """Converte la stringa della data in oggetto datetime."""
        try:
            # Esempio formato: "Aggiornato il 11/02/2025 alle 12:19"
            match = re.search(r'(\d{2}/\d{2}/\d{4}).*?(\d{2}:\d{2})', date_str)
            if not match:
                return None
            
            date_part, time_part = match.groups()
            datetime_str = f"{date_part} {time_part}"
            return datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
        except Exception as e:
            self.logger.error(f"Errore nel parsing della data '{date_str}': {e}")
            return None

    def ensure_color_distribution(self, patients: Dict[str, int]) -> ColorCodeDistribution:
        """
        Assicura una distribuzione dei colori valida anche in caso di dati mancanti.
        
        Args:
            patients: Dizionario con i conteggi dei pazienti per colore
            
        Returns:
            ColorCodeDistribution: Distribuzione dei colori con valori di default per i dati mancanti
        """
        return ColorCodeDistribution(
            red=patients.get('red', 0),
            orange=patients.get('orange', 0),
            blue=patients.get('blue', 0),
            green=patients.get('green', 0),
            white=patients.get('white', 0)
        )

    async def get_color_distribution(self) -> Optional[ColorCodeDistribution]:
        """
        Recupera la distribuzione dei codici colore.
        
        Returns:
            Optional[ColorCodeDistribution]: Distribuzione dei codici colore o None in caso di errore
        """
        try:
            data = await self._get_hospital_data()
            if not data or not data['patients']:
                return None
            
            return ColorCodeDistribution(
                red=data['patients'].get('red', 0),
                orange=data['patients'].get('orange', 0),
                blue=data['patients'].get('blue', 0),
                green=data['patients'].get('green', 0),
                white=data['patients'].get('white', 0)
            )
        except Exception as e:
            self.logger.error(f"Errore nel recupero della distribuzione colori: {str(e)}")
            return None

    async def scrape(self) -> HospitalStatusCreate:
        """Esegue lo scraping dei dati e li formatta secondo lo schema richiesto."""
        try:
            data = await self._get_hospital_data()
            
            # Calcola il totale dei pazienti
            total_patients = sum(data['patients'].values())
            
            # Determina il codice colore più critico
            color_code = 'unknown'
            for priority_color in ['red', 'orange', 'blue', 'green', 'white']:
                if data['patients'].get(priority_color, 0) > 0:
                    color_code = priority_color
                    break

            # Ottieni la distribuzione dei colori
            color_distribution = await self.get_color_distribution()
            if not color_distribution:
                color_distribution = self.ensure_color_distribution(data['patients'])

            # Stima il tempo di attesa (30 minuti per paziente)
            waiting_time = total_patients * 30

            # Stima i posti letto disponibili (assumiamo una capacità di 30 posti)
            available_beds = max(0, 30 - total_patients)

            return HospitalStatusCreate(
                hospital_id=self.hospital_id,
                color_code=color_code,
                waiting_time=waiting_time,
                patients_waiting=total_patients,
                available_beds=available_beds,
                color_distribution=color_distribution,
                last_updated=datetime.utcnow(),
                external_last_update=data['last_update']
            )

        except Exception as e:
            self.logger.error(f"Errore durante lo scraping per {self.hospital_code}: {e}")
            raise

    async def validate_data(self) -> bool:
        """Valida i dati estratti."""
        try:
            data = await self._get_hospital_data()
            
            # Verifica la presenza dei dati essenziali
            if not data['patients']:
                self.logger.error("Nessun dato sui pazienti trovato")
                return False

            # Verifica che i conteggi siano numeri non negativi
            for color, count in data['patients'].items():
                if not isinstance(count, int) or count < 0:
                    self.logger.error(f"Conteggio non valido per il colore {color}: {count}")
                    return False

            # Verifica la presenza della data di aggiornamento
            if not data['last_update']:
                self.logger.warning("Data di aggiornamento non trovata")
                # Non consideriamo questo un errore critico
                
            self.logger.info(f"Validazione dati completata con successo per {self.hospital_code}")
            return True

        except Exception as e:
            self.logger.error(f"Errore durante la validazione dei dati: {e}")
            return False 