from typing import List, Type
from .base_scraper import BaseScraper
from .villa_sofia_cervello import VillaSofiaCervelloScraper

# Lista di tutti gli scraper disponibili
AVAILABLE_SCRAPERS: List[Type[BaseScraper]] = [
    VillaSofiaCervelloScraper
]

def get_all_scrapers() -> List[BaseScraper]:
    """Restituisce le istanze di tutti gli scraper disponibili."""
    return [scraper() for scraper in AVAILABLE_SCRAPERS] 