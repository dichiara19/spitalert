from ..factory import ScraperFactory
from .ospedali_riuniti_palermo import OspedaliRiunitiPalermoScraper

# Registra lo scraper nel factory
ScraperFactory.register(OspedaliRiunitiPalermoScraper) 