from typing import List, Type
from .base_scraper import BaseScraper
from .villa_sofia_cervello import VillaSofiaCervelloScraper
from .civico import CivicoScraper
from .asp_palermo import AspPalermoScraper
from .policlinico import PoliclinicoScraper
from .asp_agrigento import AspAgrigentoScraper
from .asp_caltanissetta import AspCaltanissettaScraper

# list of all available scrapers
AVAILABLE_SCRAPERS: List[Type[BaseScraper]] = [
    VillaSofiaCervelloScraper,
    CivicoScraper,
    AspPalermoScraper,
    PoliclinicoScraper,
    AspAgrigentoScraper,
    AspCaltanissettaScraper
]

def get_all_scrapers() -> List[BaseScraper]:
    """Restituisce le istanze di tutti gli scraper disponibili."""
    return [scraper() for scraper in AVAILABLE_SCRAPERS] 