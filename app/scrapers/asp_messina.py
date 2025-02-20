"""
Scraper per i Pronto Soccorso dell'ASP di Messina.
URL: https://www.asp.messina.it/?page_id=125231
"""

from typing import Dict, Optional, ClassVar
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution
from ..core.logging import scraper_logger
import logging
import time
import random

logger = logging.getLogger("spitalert.scraper")

class BaseAspMessinaScraper(BaseHospitalScraper):
    """Classe base per gli scraper dell'ASP Messina"""
    
    BASE_URL = "https://www.asp.messina.it/?page_id=125231"
    _browser: Optional[Browser] = None
    _page: Optional[Page] = None
    
    @classmethod
    async def initialize(cls) -> None:
        """
        Inizializza il browser Playwright se non è già stato fatto.
        """
        if not cls._browser:
            playwright = await async_playwright().start()
            cls._browser = await playwright.chromium.launch(headless=True)
            cls._page = await cls._browser.new_page()
            
            # Configura il browser per bypassare il WAF
            await cls._page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3"
            })
    
    @classmethod
    async def cleanup(cls) -> None:
        """
        Chiude il browser Playwright.
        """
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            cls._page = None
    
    async def get_page_content(self) -> str:
        """
        Ottiene il contenuto della pagina usando Playwright.
        
        Returns:
            str: Contenuto HTML della pagina
        """
        if not self._page:
            await self.initialize()
        
        try:
            # Naviga alla pagina
            await self._page.goto(self.BASE_URL)
            
            # Aspetta che il WAF completi la verifica
            await self._page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Attesa aggiuntiva per sicurezza
            
            # Aspetta che il contenuto sia caricato
            await self._page.wait_for_selector(".hospital-data", timeout=10000)
            
            # Ritorna il contenuto HTML
            return await self._page.content()
            
        except Exception as e:
            self.logger.error(f"Errore durante il recupero della pagina: {str(e)}", exc_info=True)
            return ""
    
    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati dal Pronto Soccorso.
        
        Returns:
            HospitalStatusCreate: Dati del pronto soccorso
        """
        try:
            # Ottieni la pagina HTML usando Playwright
            html = await self.get_page_content()
            if not html:
                self.logger.error("Impossibile ottenere il contenuto della pagina")
                return self._create_empty_status()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerca la sezione relativa all'ospedale specifico
            hospital_data = self._find_hospital_data(soup)
            if not hospital_data:
                self.logger.error(f"Dati non trovati per l'ospedale {self.hospital_code}")
                return self._create_empty_status()
            
            # Estrai i dati
            color_distribution = self._extract_color_distribution(hospital_data)
            total_patients = sum([
                color_distribution.white,
                color_distribution.green,
                color_distribution.blue,
                color_distribution.orange,
                color_distribution.red
            ])
            
            # Stima il tempo di attesa
            estimated_waiting_time = self._estimate_waiting_time(color_distribution)
            
            return HospitalStatusCreate(
                hospital_id=self.hospital_id,
                color_distribution=color_distribution,
                total_patients=total_patients,
                estimated_waiting_time=estimated_waiting_time,
                external_last_update=datetime.now()  # Il sito non fornisce l'orario di aggiornamento
            )
            
        except Exception as e:
            self.logger.error(f"Errore durante lo scraping: {str(e)}", exc_info=True)
            return self._create_empty_status()
        finally:
            # Assicurati di chiudere il browser alla fine
            await self.cleanup()
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        Cerca la sezione relativa all'ospedale specifico nella pagina.
        Da implementare nelle classi derivate.
        
        Args:
            soup: BeautifulSoup della pagina
            
        Returns:
            Optional[BeautifulSoup]: Sezione dell'ospedale se trovata
        """
        raise NotImplementedError
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        """
        Estrae la distribuzione dei codici colore dalla sezione dell'ospedale.
        Da implementare nelle classi derivate.
        
        Args:
            hospital_data: BeautifulSoup della sezione dell'ospedale
            
        Returns:
            ColorCodeDistribution: Distribuzione dei codici colore
        """
        raise NotImplementedError
    
    def _estimate_waiting_time(self, color_dist: ColorCodeDistribution) -> Optional[int]:
        """
        Stima il tempo di attesa in base alla distribuzione dei codici colore.
        
        Args:
            color_dist: Distribuzione dei codici colore
            
        Returns:
            Optional[int]: Tempo di attesa stimato in minuti
        """
        # Pesi per il calcolo del tempo di attesa
        weights = {
            "red": 60,      # Impatto maggiore sul tempo di attesa
            "orange": 45,
            "blue": 30,
            "green": 20,
            "white": 10
        }
        
        # Calcola il tempo di attesa pesato
        total_weighted_time = (
            color_dist.red * weights["red"] +
            color_dist.orange * weights["orange"] +
            color_dist.blue * weights["blue"] +
            color_dist.green * weights["green"] +
            color_dist.white * weights["white"]
        )
        
        # Se non ci sono pazienti, restituisci None
        total_patients = sum([
            color_dist.red,
            color_dist.orange,
            color_dist.blue,
            color_dist.green,
            color_dist.white
        ])
        
        if total_patients == 0:
            return None
            
        # Calcola il tempo medio di attesa
        return round(total_weighted_time / total_patients)
    
    def _create_empty_status(self) -> HospitalStatusCreate:
        """
        Crea uno stato vuoto in caso di errore.
        
        Returns:
            HospitalStatusCreate: Stato vuoto
        """
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            color_distribution=ColorCodeDistribution(
                white=0, green=0, blue=0, orange=0, red=0
            ),
            total_patients=0,
            estimated_waiting_time=None,
            external_last_update=datetime.now()
        )

# Implementazione degli scraper specifici per ogni ospedale
class PsMilazzoScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. G. Fogliani di Milazzo"""
    hospital_code = HospitalCode.PS_MILAZZO
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Trova la sezione relativa all'ospedale di Milazzo"""
        return soup.find("div", {"id": "ps-milazzo"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        """Estrae la distribuzione dei codici colore per Milazzo"""
        try:
            # Cerca i contatori per ogni codice colore
            white = int(hospital_data.find("span", {"class": "code-white"}).text.strip() or 0)
            green = int(hospital_data.find("span", {"class": "code-green"}).text.strip() or 0)
            blue = int(hospital_data.find("span", {"class": "code-blue"}).text.strip() or 0)
            orange = int(hospital_data.find("span", {"class": "code-orange"}).text.strip() or 0)
            red = int(hospital_data.find("span", {"class": "code-red"}).text.strip() or 0)
            
            return ColorCodeDistribution(
                white=white,
                green=green,
                blue=blue,
                orange=orange,
                red=red
            )
        except (AttributeError, ValueError) as e:
            self.logger.error(f"Errore nell'estrazione dei dati: {str(e)}", exc_info=True)
            return ColorCodeDistribution(white=0, green=0, blue=0, orange=0, red=0)

# Implementazioni simili per gli altri ospedali...
class PsLipariScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. di Lipari"""
    hospital_code = HospitalCode.PS_LIPARI
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-lipari"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class PsBarcellonaScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. di Barcellona P.G."""
    hospital_code = HospitalCode.PS_BARCELLONA
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-barcellona"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class PsPattiScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. Barone Romeo di Patti"""
    hospital_code = HospitalCode.PS_PATTI
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-patti"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class PsSantAngeloScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. di Sant'Agata di Militello"""
    hospital_code = HospitalCode.PS_SANTANGELO
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-santagata"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class PsMistrettaScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. SS. Salvatore di Mistretta"""
    hospital_code = HospitalCode.PS_MISTRETTA
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-mistretta"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class PsTaorminaScraper(BaseAspMessinaScraper):
    """Scraper per il P.O. San Vincenzo di Taormina"""
    hospital_code = HospitalCode.PS_TAORMINA
    
    def _find_hospital_data(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        return soup.find("div", {"id": "ps-taormina"})
    
    def _extract_color_distribution(self, hospital_data: BeautifulSoup) -> ColorCodeDistribution:
        # Implementazione simile a Milazzo
        pass

class ASPMessinaAnalyzer:
    """Classe per l'analisi del sito dell'ASP di Messina"""
    
    BASE_URL = "https://www.asp.messina.it/?page_id=125231"
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.requests_count = 0
        self.json_responses = []
        self.xhr_requests = []
        self.ws_connections = []
    
    async def initialize(self):
        """Inizializza il browser con configurazioni anti-detection"""
        try:
            logger.info("Inizializzazione browser...")
            playwright = await async_playwright().start()
            
            # Configurazioni browser anti-detection
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--start-maximized'
                ]
            )
            
            # Configurazioni context anti-detection
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                has_touch=True,
                java_script_enabled=True,
                locale='it-IT',
                timezone_id='Europe/Rome',
                geolocation={'latitude': 38.1938, 'longitude': 15.5540}, # Messina coordinates
                permissions=['geolocation']
            )
            
            # Configurazione cookies e storage
            await self.context.add_cookies([{
                'name': 'consent',
                'value': 'true',
                'domain': '.asp.messina.it',
                'path': '/'
            }])
            
            # Configurazione page
            self.page = await self.context.new_page()
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Event listeners
            self.page.on("request", self.handle_request)
            self.page.on("response", self.handle_response)
            self.page.on("websocket", self.handle_websocket)
            
            logger.info("Browser inizializzato con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante l'inizializzazione del browser: {str(e)}")
            return False
            
    async def handle_request(self, request):
        """Gestisce e monitora le richieste in uscita"""
        try:
            self.requests_count += 1
            if request.resource_type == "xhr":
                self.xhr_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': request.headers,
                    'timestamp': time.time()
                })
            logger.debug(f"Richiesta intercettata: {request.method} {request.url}")
        except Exception as e:
            logger.error(f"Errore durante la gestione della richiesta: {str(e)}")

    async def handle_response(self, response):
        """Gestisce e monitora le risposte in ingresso"""
        try:
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    json_data = await response.json()
                    self.json_responses.append({
                        'url': response.url,
                        'status': response.status,
                        'data': json_data,
                        'timestamp': time.time()
                    })
                    logger.debug(f"Risposta JSON da {response.url}")
                except:
                    pass
            elif 'text' in content_type:
                logger.debug(f"Risposta testuale da {response.url}")
        except Exception as e:
            logger.error(f"Errore durante la gestione della risposta: {str(e)}")

    async def handle_websocket(self, ws):
        """Gestisce e monitora le connessioni WebSocket"""
        try:
            self.ws_connections.append({
                'url': ws.url,
                'timestamp': time.time()
            })
            logger.debug(f"Connessione WebSocket rilevata: {ws.url}")
        except Exception as e:
            logger.error(f"Errore durante la gestione del WebSocket: {str(e)}")

    async def analyze_scripts(self):
        """Analizza gli script presenti nella pagina"""
        try:
            scripts = await self.page.evaluate('''() => {
                return Array.from(document.getElementsByTagName('script')).map(s => ({
                    src: s.src,
                    type: s.type,
                    content: s.innerText
                }));
            }''')
            return scripts
        except Exception as e:
            logger.error(f"Errore durante l'analisi degli script: {str(e)}")
            return []

    async def analyze_forms(self):
        """Analizza i form presenti nella pagina"""
        try:
            forms = await self.page.evaluate('''() => {
                return Array.from(document.getElementsByTagName('form')).map(f => ({
                    action: f.action,
                    method: f.method,
                    inputs: Array.from(f.elements).map(e => ({
                        name: e.name,
                        type: e.type,
                        value: e.value
                    }))
                }));
            }''')
            return forms
        except Exception as e:
            logger.error(f"Errore durante l'analisi dei form: {str(e)}")
            return []

    async def analyze_iframes(self):
        """Analizza gli iframe presenti nella pagina"""
        try:
            iframes = await self.page.evaluate('''() => {
                return Array.from(document.getElementsByTagName('iframe')).map(i => ({
                    src: i.src,
                    name: i.name,
                    id: i.id
                }));
            }''')
            return iframes
        except Exception as e:
            logger.error(f"Errore durante l'analisi degli iframe: {str(e)}")
            return []

    async def analyze(self):
        """Analizza il sito ASP Messina per potenziali endpoint"""
        try:
            logger.info("Inizio analisi del sito ASP Messina...")
            
            # Navigazione con retry e delay random
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info("Navigazione a https://www.asp.messina.it/?page_id=125231")
                    await self.page.goto("https://www.asp.messina.it/?page_id=125231", 
                                       wait_until="networkidle")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(random.uniform(2, 5))
                    continue

            # Attesa per richieste AJAX
            logger.info("Attesa per richieste AJAX...")
            await asyncio.sleep(5)  # Attesa più lunga per AJAX

            # Analisi elementi pagina
            scripts = await self.analyze_scripts()
            forms = await self.analyze_forms()
            iframes = await self.analyze_iframes()

            # Raccolta risultati
            results = {
                'xhr_requests': self.xhr_requests,
                'json_responses': self.json_responses,
                'ws_connections': self.ws_connections,
                'scripts': scripts,
                'forms': forms,
                'iframes': iframes,
                'total_requests': self.requests_count
            }

            logger.info(f"Analisi completata. Trovate {len(self.xhr_requests)} richieste XHR, "
                       f"{len(self.json_responses)} risposte JSON, "
                       f"{len(self.ws_connections)} connessioni WebSocket")
            
            return results

        except Exception as e:
            logger.error(f"Errore durante l'analisi: {str(e)}")
            return None

    async def cleanup(self):
        """Pulisce le risorse del browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Pulizia risorse completata")
        except Exception as e:
            logger.error(f"Errore durante la pulizia delle risorse: {str(e)}")

async def main():
    """Funzione principale"""
    analyzer = ASPMessinaAnalyzer()
    if await analyzer.initialize():
        try:
            results = await analyzer.analyze()
            if results:
                logger.info("Analisi completata con successo")
                # Qui puoi aggiungere la logica per processare i risultati
        finally:
            await analyzer.cleanup()
    else:
        logger.error("Impossibile inizializzare l'analizzatore")

if __name__ == "__main__":
    asyncio.run(main()) 