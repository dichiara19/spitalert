"""
Inizializzazione degli scraper.
Registra tutti gli scraper disponibili nel factory.
"""

from .factory import ScraperFactory
from .hospital_codes import HospitalCode, HospitalRegistry
from .ospedali_riuniti_palermo import (
    POCervelloAdultiScraper,
    POVillaSofiaAdultiScraper,
    POCervelloPediatricoScraper
)
from .policlinico_palermo import PoliclinicoPalermoScraper
from .asp_agrigento import (
    PsSciacca,
    PsRibera,
    PsAgrigento,
    PsCanicatti,
    PsLicata
)
from .asp_caltanissetta import PsSantEliaScraper
from .asp_palermo import (
    PsIngrassiaScraper,
    PsPartinicoScraper,
    PsCorleoneScraper,
    PsPetraliaScraper,
    PsTerminiScraper
)
from .arnas_civico import (
    PoCivicoAdultiScraper,
    PoCivicoPediatricoScraper
)

# Registra i mapping ID-codice nel registry
HospitalRegistry.register(1, HospitalCode.PO_CERVELLO_ADULTI)
HospitalRegistry.register(2, HospitalCode.PO_VILLA_SOFIA_ADULTI)
HospitalRegistry.register(3, HospitalCode.PO_CERVELLO_PEDIATRICO)
HospitalRegistry.register(4, HospitalCode.POLICLINICO_PALERMO)
HospitalRegistry.register(5, HospitalCode.PS_SCIACCA)
HospitalRegistry.register(6, HospitalCode.PS_RIBERA)
HospitalRegistry.register(7, HospitalCode.PS_AGRIGENTO)
HospitalRegistry.register(8, HospitalCode.PS_CANICATTI)
HospitalRegistry.register(9, HospitalCode.PS_LICATA)
HospitalRegistry.register(10, HospitalCode.PS_SANTELIA)
HospitalRegistry.register(11, HospitalCode.PS_INGRASSIA)
HospitalRegistry.register(12, HospitalCode.PS_PARTINICO)
HospitalRegistry.register(13, HospitalCode.PS_CORLEONE)
HospitalRegistry.register(14, HospitalCode.PS_PETRALIA)
HospitalRegistry.register(15, HospitalCode.PS_TERMINI)
HospitalRegistry.register(16, HospitalCode.PO_CIVICO_ADULTI)
HospitalRegistry.register(17, HospitalCode.PO_CIVICO_PEDIATRICO)

# Registra gli scraper
ScraperFactory.register_scraper(POCervelloAdultiScraper)
ScraperFactory.register_scraper(POVillaSofiaAdultiScraper)
ScraperFactory.register_scraper(POCervelloPediatricoScraper)
ScraperFactory.register_scraper(PoliclinicoPalermoScraper)

# Registra gli scraper dell'ASP di Agrigento
ScraperFactory.register_scraper(PsSciacca)
ScraperFactory.register_scraper(PsRibera)
ScraperFactory.register_scraper(PsAgrigento)
ScraperFactory.register_scraper(PsCanicatti)
ScraperFactory.register_scraper(PsLicata)

# Registra lo scraper dell'ASP di Caltanissetta
ScraperFactory.register_scraper(PsSantEliaScraper)

# Registra gli scraper dell'ASP di Palermo
ScraperFactory.register_scraper(PsIngrassiaScraper)
ScraperFactory.register_scraper(PsPartinicoScraper)
ScraperFactory.register_scraper(PsCorleoneScraper)
ScraperFactory.register_scraper(PsPetraliaScraper)
ScraperFactory.register_scraper(PsTerminiScraper)

# Registra gli scraper dell'ARNAS Civico
ScraperFactory.register_scraper(PoCivicoAdultiScraper)
ScraperFactory.register_scraper(PoCivicoPediatricoScraper) 
