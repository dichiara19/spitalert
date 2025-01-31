from datetime import datetime
from typing import Dict, Any, List
import aiohttp
import logging
from .base_scraper import BaseScraper

class PoliclinicoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="https://www.policlinico.pa.it",
            name="Policlinico",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "it-IT,it;q=0.9",
                "Origin": "https://www.policlinico.pa.it",
                "Referer": "https://www.policlinico.pa.it/portal/pronto-soccorso"
            },
            timeout=30
        )
        self.api_base_url = "https://www.policlinico.pa.it/o/PoliclinicoPaRestBuilder/v1.0"
    
    async def fetch_data(self) -> tuple[dict, dict]:
        """Recupera i dati dalle API del Policlinico."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            # Recupera i dati principali del pronto soccorso
            async with session.get(f"{self.api_base_url}/ProntoSoccorso", timeout=self.timeout) as response:
                if response.status != 200:
                    raise ValueError(f"Errore nel recupero dei dati: {response.status}")
                ps_data = await response.json()
                logging.info(f"Dati PS ricevuti: {ps_data}")
            
            # Recupera gli indici del pronto soccorso
            async with session.get(f"{self.api_base_url}/ProntoSoccorsoIndici", timeout=self.timeout) as response:
                if response.status != 200:
                    raise ValueError(f"Errore nel recupero degli indici: {response.status}")
                indici_data = await response.json()
                logging.info(f"Dati indici ricevuti: {indici_data}")
            
            return ps_data, indici_data

    async def scrape(self) -> List[Dict[str, Any]]:
        """Sovrascrive il metodo scrape della classe base per usare fetch_data invece di fetch_page."""
        try:
            ps_data, indici_data = await self.fetch_data()
            return await self.parse("")
        except Exception as e:
            print(f"Errore durante lo scraping di {self.name}: {str(e)}")
            return []

    def safe_int(self, value: Any) -> int:
        """Converte in modo sicuro un valore in intero."""
        try:
            if isinstance(value, str):
                # Rimuovi eventuali spazi e caratteri non numerici
                value = ''.join(c for c in value if c.isdigit())
            elif isinstance(value, float):
                value = int(value)
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """Analizza i dati delle API e li formatta per il database."""
        ps_data, indici_data = await self.fetch_data()
        
        # Estrai i dati dai JSON
        pazienti_in_attesa = ps_data.get("pazientiInAttesa", {})
        pazienti_in_carico = ps_data.get("pazientiInCarico", {})
        
        logging.info(f"Pazienti in attesa: {pazienti_in_attesa}")
        logging.info(f"Pazienti in carico: {pazienti_in_carico}")
        
        # Calcola i totali per ogni codice con conversione sicura
        red_code = self.safe_int(pazienti_in_attesa.get("Rosso (1)", 0)) + self.safe_int(pazienti_in_carico.get("Rosso (1)", 0))
        orange_code = self.safe_int(pazienti_in_attesa.get("Arancione (2)", 0)) + self.safe_int(pazienti_in_carico.get("Arancione (2)", 0))
        azure_code = self.safe_int(pazienti_in_attesa.get("Azzurro (3)", 0)) + self.safe_int(pazienti_in_carico.get("Azzurro (3)", 0))
        green_code = self.safe_int(pazienti_in_attesa.get("Verde (4)", 0)) + self.safe_int(pazienti_in_carico.get("Verde (4)", 0))
        white_code = self.safe_int(pazienti_in_attesa.get("Bianco (5)", 0)) + self.safe_int(pazienti_in_carico.get("Bianco (5)", 0))
        
        # Calcola i totali generali
        total_waiting = sum(self.safe_int(v) for v in pazienti_in_attesa.values())
        total_treatment = sum(self.safe_int(v) for v in pazienti_in_carico.values())
        total_patients = total_waiting + total_treatment
        
        # Ottieni l'indice di sovraffollamento
        try:
            overcrowding_index = float(indici_data.get("efficienzaOperativaStandard", 0))
        except (ValueError, TypeError):
            overcrowding_index = 0.0
        
        hospital_data = {
            "name": self.name,
            "department": "Pronto Soccorso",
            "total_patients": total_patients,
            "waiting_patients": total_waiting,
            "red_code": red_code,
            "orange_code": orange_code,
            "azure_code": azure_code,
            "green_code": green_code,
            "white_code": white_code,
            "overcrowding_index": overcrowding_index,
            "last_updated": datetime.utcnow(),
            "is_active": True
        }
        
        logging.info(f"Dati ospedale elaborati: {hospital_data}")
        return [hospital_data] 