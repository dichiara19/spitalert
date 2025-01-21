from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper
import logging
import re

logger = logging.getLogger(__name__)

class AspAgrigentoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="http://pswall.aspag.it/ps/listaattesa.php",
            name="ASP Agrigento"
        )
        
        # Mappa dei nomi degli ospedali per normalizzarli
        self.hospital_names = {
            "PS LICATA": "U.O.C. Medicina e Chirurgia di Accettazione e Urgenza di Licata",
            "PS CANICATTI'": "P.O. di Canicattì",
            "PS AGRIGENTO": "P.O. 'S. Giovanni Di Dio' di Agrigento",
            "PS RIBERA": "P.O. 'F.lli Parlapiano' di Ribera",
            "PS SCIACCA": "P.O. 'San Giovanni Paolo II' di Sciacca"
        }

    def extract_number(self, cell) -> int:
        """Estrae il numero da una cella della tabella."""
        try:
            # Cerca il numero dopo lo span del dot
            text = cell.text.strip()
            number = re.search(r'\d+', text)
            return int(number.group()) if number else 0
        except Exception as e:
            logger.error(f"Errore nell'estrazione del numero: {str(e)}")
            return 0

    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Trova la tabella con i dati
            table = soup.find('table', class_='table')
            if not table or not table.find('tbody'):
                logger.error("Tabella dati non trovata")
                return []
                
            # Estrai la data di aggiornamento
            update_div = soup.find('div', style="text-align:right;")
            last_updated = datetime.utcnow()  # default a ora corrente
            if update_div and update_div.find('small'):
                try:
                    update_text = update_div.find('small').text
                    last_updated = datetime.strptime(update_text.replace('Data Aggiornamento ', ''), '%H:%M %d/%m/%Y')
                except Exception as e:
                    logger.error(f"Errore nel parsing della data: {str(e)}")
            
            # Processa ogni riga della tabella
            rows = table.find('tbody').find_all('tr')
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 7:  # Verifica che ci siano tutte le colonne necessarie
                        continue
                        
                    hospital_code = cells[0].text.strip()
                    
                    # Salta se l'ospedale non è nella nostra lista
                    if hospital_code not in self.hospital_names:
                        continue
                        
                    hospital_name = self.hospital_names[hospital_code]
                    
                    # Estrai i conteggi per ogni codice
                    red = self.extract_number(cells[1])
                    orange = self.extract_number(cells[2])
                    yellow = self.extract_number(cells[3])
                    green = self.extract_number(cells[4])
                    azure = self.extract_number(cells[5])
                    white = self.extract_number(cells[6])
                    
                    # Calcola il totale dei pazienti
                    total_patients = red + orange + yellow + green + azure + white
                    
                    # Calcola l'indice di sovraffollamento (esempio semplificato)
                    overcrowding_index = round((total_patients / 20) * 100, 2)  # Assumiamo una capacità di 20 pazienti
                    
                    results.append({
                        'name': hospital_name,
                        'department': 'Pronto Soccorso',
                        'total_patients': total_patients,
                        'waiting_patients': total_patients,  # Assumiamo che tutti stiano aspettando
                        'red_code': red,
                        'orange_code': orange + yellow,  # Combiniamo i codici giallo e arancione
                        'green_code': green,
                        'azure_code': azure,
                        'white_code': white,
                        'overcrowding_index': overcrowding_index,
                        'last_updated': last_updated,
                        'url': self.url,
                        'is_active': True
                    })
                except Exception as e:
                    logger.error(f"Errore nel parsing della riga per {hospital_code}: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Errore generale nel parsing: {str(e)}")
            return [] 