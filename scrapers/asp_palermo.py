from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class AspPalermoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://www.asppalermo.org/attese_ps/index_mod2.php",
            name="ASP Palermo"
        )
    
    def extract_percentage(self, text: str) -> float:
        """Estrae il valore percentuale da una stringa."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        return float(match.group(1)) if match else 0.0
    
    def parse_table_data(self, table) -> Dict[str, int]:
        """Analizza una tabella di codici e restituisce i conteggi."""
        codes = {
            "red_code": 0,
            "orange_code": 0,
            "azure_code": 0,
            "green_code": 0,
            "white_code": 0
        }
        
        # Trova la riga dei totali (ultima riga)
        rows = table.find_all('tr')
        if len(rows) >= 4:  # Verifica che ci siano abbastanza righe
            total_row = rows[-1]  # Ultima riga (totali)
            cells = total_row.find_all(['td', 'th'])
            
            if len(cells) >= 6:  # Verifica che ci siano tutte le colonne
                codes['red_code'] = int(cells[1].text.strip())
                codes['orange_code'] = int(cells[2].text.strip())
                codes['azure_code'] = int(cells[3].text.strip())
                codes['green_code'] = int(cells[4].text.strip())
                codes['white_code'] = int(cells[5].text.strip())
        
        return codes
    
    def extract_waiting_patients(self, table) -> int:
        """Estrae il numero di pazienti in attesa dalla tabella."""
        rows = table.find_all('tr')
        if len(rows) >= 2:  # Verifica che ci sia la riga "Attesa"
            waiting_row = rows[1]  # Prima riga dopo l'header
            cells = waiting_row.find_all(['td', 'th'])
            if len(cells) >= 6:
                return sum(int(cell.text.strip()) for cell in cells[1:6])  # Somma tutti i pazienti in attesa
        return 0
    
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """Analizza il contenuto HTML e estrae i dati degli ospedali."""
        soup = BeautifulSoup(html_content, 'html.parser')
        hospitals_data = []
        
        # Trova tutti i container degli ospedali
        hospital_sections = soup.find_all('div', class_='container')
        
        for section in hospital_sections:
            # Verifica che sia una sezione di ospedale valida
            hospital_name = section.find('h5', class_='alert-info')
            if not hospital_name:
                continue
                
            name = hospital_name.text.strip().replace('PRONTO SOCCORSO - ', '')
            
            # Trova i dettagli dell'ospedale
            details = section.find('div', class_='alert-dark')
            if not details:
                continue
                
            # Estrai la data di aggiornamento
            update_text = details.find('span', class_='fw-bold')
            last_updated = datetime.utcnow()
            if update_text:
                try:
                    # Formato: "18/01/25 - 13:24:29"
                    date_str = update_text.text.strip()
                    last_updated = datetime.strptime(date_str, '%d/%m/%y - %H:%M:%S')
                except Exception as e:
                    print(f"Errore nel parsing della data per {name}: {str(e)}")
            
            # Trova la tabella dei dati
            table = section.find('table', class_='table')
            if not table:
                continue
            
            # Estrai i dati base
            data = {
                "name": name,
                "department": "Pronto Soccorso",
                "url": self.url,
                "last_updated": last_updated,
                "is_active": True
            }
            
            # Estrai l'indice di sovraffollamento
            overcrowding_text = details.text
            overcrowding_match = re.search(r'Indice di Sovraffollamento:[^\d]*(\d+(?:\.\d+)?)\s*%', overcrowding_text)
            data["overcrowding_index"] = float(overcrowding_match.group(1)) if overcrowding_match else 0.0
            
            # Aggiungi i conteggi dei codici
            codes = self.parse_table_data(table)
            data.update(codes)
            
            # Calcola il totale dei pazienti
            data["total_patients"] = sum(codes.values())
            
            # Aggiungi i pazienti in attesa
            data["waiting_patients"] = self.extract_waiting_patients(table)
            
            hospitals_data.append(data)
        
        return hospitals_data 