from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class VillaSofiaCervelloScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://www.ospedaliriunitipalermo.it/amministrazione-trasparente/servizi-erogati/liste-di-attesa/pazienti-in-attesa-al-pronto-soccorso/",
            name="Villa Sofia-Cervello"
        )
    
    def extract_percentage(self, text: str) -> float:
        """Estrae il valore percentuale da una stringa."""
        match = re.search(r'(\d+(?:\.\d+)?)%', text)
        return float(match.group(1)) if match else 0.0
    
    def parse_hospital_section(self, section) -> Dict[str, Any]:
        """Analizza una sezione di ospedale e restituisce i dati strutturati."""
        data = {
            "name": section.find("h3", class_="olo-title-hospital").text.strip(),
            "department": section.find("div", class_="olo-sezione-pronto-soccorso").text.strip(),
            "total_patients": int(section.find("div", class_="olo-number-pazienti tot").text.strip() if section.find("div", class_="olo-number-pazienti tot") else section.find_all("div", class_="olo-number-pazienti")[0].text.strip()),
            "waiting_patients": int(section.find("div", class_="olo-number-pazienti wait").text.strip() if section.find("div", class_="olo-number-pazienti wait") else section.find_all("div", class_="olo-number-pazienti")[1].text.strip()),
            "red_code": 0,
            "orange_code": 0,
            "azure_code": 0,
            "green_code": 0,
            "white_code": 0,
            "url": self.url
        }
        
        # Estrai i codici colore
        codes = section.find_all("div", class_="olo-container-codice")
        for code in codes:
            color = ""
            if "olo-codice-red" in code["class"]: color = "red"
            elif "olo-codice-orange" in code["class"]: color = "orange"
            elif "olo-codice-azure" in code["class"]: color = "azure"
            elif "olo-codice-green" in code["class"]: color = "green"
            elif "olo-codice-grey" in code["class"]: color = "white"
            
            if color:
                data[f"{color}_code"] = int(code.find("div", class_="olo-number-codice").text.strip())
        
        # Estrai l'indice di sovraffollamento
        overcrowding = section.find("div", class_="olo-row-indice-sovraffollamento")
        if overcrowding:
            data["overcrowding_index"] = self.extract_percentage(overcrowding.text)
        
        return data
    
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """Analizza il contenuto HTML e estrae i dati degli ospedali."""
        soup = BeautifulSoup(html_content, 'html.parser')
        hospitals_data = []
        
        # Trova la data di aggiornamento
        update_div = soup.find("div", class_="olo-row-dati-aggiornati-al")
        last_updated = datetime.utcnow()  # Default a now
        if update_div:
            try:
                # Esempio: "Situazione aggiornata al 17 Gennaio 2025 18:04"
                update_text = update_div.text.strip()
                date_str = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{2}):(\d{2})', update_text)
                if date_str:
                    day, month, year, hour, minute = date_str.groups()
                    month_map = {
                        'Gennaio': 1, 'Febbraio': 2, 'Marzo': 3, 'Aprile': 4,
                        'Maggio': 5, 'Giugno': 6, 'Luglio': 7, 'Agosto': 8,
                        'Settembre': 9, 'Ottobre': 10, 'Novembre': 11, 'Dicembre': 12
                    }
                    last_updated = datetime(
                        int(year), month_map[month], int(day),
                        int(hour), int(minute)
                    )
            except Exception as e:
                print(f"Errore nel parsing della data: {str(e)}")
        
        # Trova tutte le sezioni degli ospedali
        hospital_sections = soup.find_all("div", class_="olo-container-single-hospital")
        
        for section in hospital_sections:
            data = self.parse_hospital_section(section)
            data["last_updated"] = last_updated
            hospitals_data.append(data)
        
        return hospitals_data 