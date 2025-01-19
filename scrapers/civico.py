from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class CivicoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://www.arnascivico.it/index.php/assistenza-ospedaliera/3415-attesa-al-pronto-soccorso",
            name="ARNAS Civico"
        )
    
    def extract_percentage(self, text: str) -> float:
        """Estrae il valore percentuale da una stringa."""
        match = re.search(r'(\d+)%', text)
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
        
        rows = table.find_all('tr')[1:]  # skip the header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:  # check if there are enough cells
                code_type = cells[0].text.strip().upper()
                total = int(cells[4].text.strip())
                
                if 'ROSSO' in code_type:
                    codes['red_code'] = total
                elif 'ARANCIONE' in code_type:
                    codes['orange_code'] = total
                elif 'AZZURRO' in code_type:
                    codes['azure_code'] = total
                elif 'VERDE' in code_type:
                    codes['green_code'] = total
                elif 'BIANCO' in code_type:
                    codes['white_code'] = total
        
        return codes
    
    def extract_total_patients(self, text: str) -> int:
        """Estrae il numero totale di pazienti da una stringa."""
        match = re.search(r'Totale pazienti[^:]*:\s*<strong>(\d+)</strong>', text)
        return int(match.group(1)) if match else 0
    
    def extract_waiting_patients(self, table) -> int:
        """Estrae il numero di pazienti in attesa dalla tabella."""
        total_row = table.find_all('tr')[-1]  # last row (totals)
        cells = total_row.find_all('th')
        if len(cells) >= 2:
            waiting = cells[1].text.strip()
            return int(re.search(r'\d+', waiting).group()) if re.search(r'\d+', waiting) else 0
        return 0
    
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """Analizza il contenuto HTML e estrae i dati degli ospedali."""
        soup = BeautifulSoup(html_content, 'html.parser')
        hospitals_data = []
        
        # find the update date
        update_text = soup.find(text=re.compile(r'Situazione aggiornata al'))
        last_updated = datetime.utcnow()  # default to now
        if update_text:
            try:
                date_str = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', update_text)
                if date_str:
                    last_updated = datetime.strptime(date_str.group(1), '%d/%m/%Y %H:%M:%S')
            except Exception as e:
                print(f"Errore nel parsing della data: {str(e)}")
        
        # find the emergency tables
        tables = soup.find_all('table', class_='gridtable')
        sections = soup.find_all(text=re.compile(r'Totale pazienti al P\.S\.'))
        
        for i, section in enumerate(sections):
            if i < len(tables):
                department = "Pronto Soccorso Adulti" if "Civico" in section else "Pronto Soccorso Pediatrico"
                section_text = str(section.parent)
                
                # extract the base data
                data = {
                    "name": self.name,
                    "department": department,
                    "total_patients": self.extract_total_patients(section_text),
                    "waiting_patients": self.extract_waiting_patients(tables[i]),
                    "url": self.url,
                    "last_updated": last_updated,
                    "is_active": True
                }
                
                # extract the overcrowding index
                overcrowding = re.search(r'Indice Sovraffollamento:[^%]*?(\d+)%', section_text)
                data["overcrowding_index"] = float(overcrowding.group(1)) if overcrowding else 0.0
                
                # add the codes counts
                data.update(self.parse_table_data(tables[i]))
                
                hospitals_data.append(data)
        
        return hospitals_data 