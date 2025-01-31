from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import aiohttp
from datetime import datetime

class BaseScraper(ABC):
    def __init__(
        self, 
        url: str, 
        name: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        self.url = url
        self.name = name
        self.headers = headers or {}
        self.timeout = timeout
    
    async def fetch_page(self) -> str:
        """Recupera il contenuto della pagina web."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(self.url, timeout=self.timeout) as response:
                return await response.text()
    
    @abstractmethod
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Implementa la logica di parsing specifica per il sito.
        Deve restituire una lista di dizionari con i seguenti campi:
        {
            'name': str,
            'department': str,
            'total_patients': int,
            'waiting_patients': int,
            'red_code': int,
            'orange_code': int,
            'azure_code': int,
            'green_code': int,
            'white_code': int,
            'overcrowding_index': float,
            'last_updated': datetime,
            'url': str
        }
        """
        pass
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Esegue lo scraping completo."""
        try:
            html_content = await self.fetch_page()
            return await self.parse(html_content)
        except Exception as e:
            print(f"Errore durante lo scraping di {self.name}: {str(e)}")
            return [] 