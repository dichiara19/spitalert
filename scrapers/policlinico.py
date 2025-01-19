from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, Any, List
from .base_scraper import BaseScraper

class PoliclinicoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://www.policlinico.pa.it/portal/index.php",
            name="Policlinico"
        )
    
    def extract_number(self, text: str) -> int:
        """Estrae un numero da una stringa."""
        if not text:
            return 0
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0
    
    def extract_percentage(self, text: str) -> float:
        """Estrae una percentuale da una stringa."""
        if not text:
            return 0.0
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return float(match.group(1)) if match else 0.0
    
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """Analizza il contenuto HTML e estrae i dati del pronto soccorso."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Estrai i dati principali
        overcrowding_index = self.extract_percentage(
            soup.find('b', id='indice-sovraffollamento').text if soup.find('b', id='indice-sovraffollamento') else "0"
        )
        
        # Estrai i pazienti in attesa per codice
        waiting_red = self.extract_number(
            soup.find('b', id='attesa-rosso').text if soup.find('b', id='attesa-rosso') else "0"
        )
        waiting_yellow = self.extract_number(
            soup.find('b', id='attesa-giallo').text if soup.find('b', id='attesa-giallo') else "0"
        )
        waiting_azure = self.extract_number(
            soup.find('b', id='attesa-azzurro').text if soup.find('b', id='attesa-azzurro') else "0"
        )
        waiting_green = self.extract_number(
            soup.find('b', id='attesa-verde').text if soup.find('b', id='attesa-verde') else "0"
        )
        waiting_white = self.extract_number(
            soup.find('b', id='attesa-bianco').text if soup.find('b', id='attesa-bianco') else "0"
        )
        
        # Estrai i pazienti in cura per codice
        treatment_red = self.extract_number(
            soup.find('b', id='carico-rosso').text if soup.find('b', id='carico-rosso') else "0"
        )
        treatment_yellow = self.extract_number(
            soup.find('b', id='carico-giallo').text if soup.find('b', id='carico-giallo') else "0"
        )
        treatment_azure = self.extract_number(
            soup.find('b', id='carico-azzurro').text if soup.find('b', id='carico-azzurro') else "0"
        )
        treatment_green = self.extract_number(
            soup.find('b', id='carico-verde').text if soup.find('b', id='carico-verde') else "0"
        )
        treatment_white = self.extract_number(
            soup.find('b', id='carico-bianco').text if soup.find('b', id='carico-bianco') else "0"
        )
        
        # Calcola i totali
        total_waiting = waiting_red + waiting_yellow + waiting_azure + waiting_green + waiting_white
        total_treatment = treatment_red + treatment_yellow + treatment_azure + treatment_green + treatment_white
        total_patients = total_waiting + total_treatment
        
        # Prepara i dati per il database
        hospital_data = {
            "name": self.name,
            "department": "Pronto Soccorso",
            "total_patients": total_patients,
            "waiting_patients": total_waiting,
            "red_code": waiting_red + treatment_red,
            "orange_code": waiting_yellow + treatment_yellow,  # Giallo corrisponde a arancione
            "azure_code": waiting_azure + treatment_azure,
            "green_code": waiting_green + treatment_green,
            "white_code": waiting_white + treatment_white,
            "overcrowding_index": overcrowding_index,
            "last_updated": datetime.utcnow(),
            "is_active": True
        }
        
        return [hospital_data] 