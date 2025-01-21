from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper
import logging
import re

logger = logging.getLogger(__name__)

class AspCaltanissettaScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://cruscottops.asp.cl.it/",  # URL base
            name="ASP Caltanissetta"
        )
        
        # Mappa dei nomi degli ospedali per normalizzarli
        self.hospital_names = {
            "SANT'ELIA": "P.O. 'S. Elia' di Caltanissetta",
            "VITTORIO EMANUELE": "P.O. 'Vittorio Emanuele' di Gela"
        }
        
        # Mappa delle URL per ogni ospedale
        self.hospital_urls = {
            "SANT'ELIA": "caltanissetta.php",
            "VITTORIO EMANUELE": "gela.php"
        }

    def extract_number(self, cell) -> int:
        """Estrae il numero da una cella della tabella."""
        try:
            text = cell.text.strip()
            number = re.search(r'\d+', text)
            return int(number.group()) if number else 0
        except Exception as e:
            logger.error(f"Errore nell'estrazione del numero: {str(e)}")
            return 0

    async def scrape(self) -> List[Dict[str, Any]]:
        """Esegue lo scraping per tutti gli ospedali."""
        all_results = []
        for hospital_code, url_suffix in self.hospital_urls.items():
            try:
                full_url = self.url + url_suffix
                original_url = self.url
                self.url = full_url
                html_content = await self.fetch_page()
                self.url = original_url  # Ripristino l'URL originale
                results = await self.parse(html_content, hospital_code, full_url)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Errore nello scraping dell'ospedale {hospital_code}: {str(e)}")
        return all_results

    async def parse(self, html_content: str, expected_hospital_code: str, current_url: str) -> List[Dict[str, Any]]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Trova il titolo per verificare l'ospedale
            title = soup.find('h1')
            if not title:
                logger.error("Titolo non trovato")
                return []
            
            hospital_name = title.text.strip().replace("PRONTO SOCCORSO P.O. ", "")
            if hospital_name not in self.hospital_names:
                logger.error(f"Ospedale non riconosciuto: {hospital_name}")
                return []
            
            # Verifica che l'ospedale corrisponda a quello atteso
            if hospital_name != expected_hospital_code:
                logger.error(f"Ospedale non corrispondente: atteso {expected_hospital_code}, trovato {hospital_name}")
                return []
            
            # Trova la tabella con i dati
            table = soup.find('table', attrs={'width': '95%', 'style': 'border:solid white 2px;'})
            if not table:
                logger.error("Tabella dati non trovata")
                return []
            
            # Estrai la data di aggiornamento
            update_div = soup.find('div', style=lambda x: x and 'font-variant: small-caps;' in x and 'Aggiornamento:' in soup.find('div', style=x).text)
            last_updated = datetime.utcnow()  # default a ora corrente
            if update_div:
                try:
                    update_text = update_div.text.replace('Aggiornamento: ', '')
                    last_updated = datetime.strptime(update_text, '%d-%m-%Y %H:%M')
                except Exception as e:
                    logger.error(f"Errore nel parsing della data: {str(e)}")
            
            # Trova le righe con i dati
            rows = table.find_all('tr')[1:]  # Salta l'header
            if len(rows) < 2:
                logger.error("Dati non trovati nella tabella")
                return []
            
            # Estrai i dati dalle righe
            waiting_row = rows[0]
            treatment_row = rows[1]
            
            # Estrai i conteggi per ogni codice
            waiting_cells = waiting_row.find_all('td')
            treatment_cells = treatment_row.find_all('td')
            
            # Verifica che ci siano abbastanza celle
            if len(waiting_cells) < 7 or len(treatment_cells) < 7:
                logger.error("Numero insufficiente di celle nella tabella")
                return []
            
            # Estrai i numeri dalle celle
            red = self.extract_number(waiting_cells[0]) + self.extract_number(treatment_cells[0])
            orange = self.extract_number(waiting_cells[1]) + self.extract_number(treatment_cells[1])
            yellow = self.extract_number(waiting_cells[2]) + self.extract_number(treatment_cells[2])
            azure = self.extract_number(waiting_cells[3]) + self.extract_number(treatment_cells[3])
            green = self.extract_number(waiting_cells[4]) + self.extract_number(treatment_cells[4])
            white = self.extract_number(waiting_cells[5]) + self.extract_number(treatment_cells[5])
            
            # Calcola il totale dei pazienti in attesa
            waiting_patients = sum(self.extract_number(cell) for cell in waiting_cells[:-1])  # Escludi la colonna totale
            
            # Calcola il totale dei pazienti
            total_patients = red + orange + yellow + green + azure + white
            
            # Calcola l'indice di sovraffollamento (esempio semplificato)
            overcrowding_index = round((total_patients / 20) * 100, 2)  # Assumiamo una capacità di 20 pazienti
            
            results.append({
                'name': self.hospital_names[hospital_name],
                'department': 'Pronto Soccorso',
                'total_patients': total_patients,
                'waiting_patients': waiting_patients,
                'red_code': red,
                'orange_code': orange + yellow,  # Combiniamo i codici giallo e arancione
                'green_code': green,
                'azure_code': azure,
                'white_code': white,
                'overcrowding_index': overcrowding_index,
                'last_updated': last_updated,
                'url': current_url,
                'is_active': True
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Errore generale nel parsing: {str(e)}")
            return [] 