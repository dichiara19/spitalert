"""
Inizializzazione degli scraper.
Registra tutti gli scraper disponibili nel factory.
"""

from .factory import ScraperFactory
from .ospedali_riuniti_palermo import (
    POCervelloAdultiScraper,
    POVillaSofiaAdultiScraper,
    POCervelloPediatricoScraper
)

# Registra gli scraper
ScraperFactory.register_scraper(POCervelloAdultiScraper)
ScraperFactory.register_scraper(POVillaSofiaAdultiScraper)
ScraperFactory.register_scraper(POCervelloPediatricoScraper) 