"""
Inizializzazione degli scraper.
Registra tutti gli scraper disponibili nel factory.
"""

from .factory import ScraperFactory
from .hospital_codes import HospitalCode, HospitalRegistry

# Import degli scraper
from .ospedali_riuniti_palermo import POCervelloAdultiScraper, POCervelloPediatricoScraper, POVillaSofiaAdultiScraper
from .policlinico_palermo import PoliclinicoPalermoScraper
from .asp_agrigento import PsSciacca, PsRibera, PsLicata, PsCanicatti, PsAgrigento
from .asp_caltanissetta import PsSantEliaScraper
from .asp_palermo import (
    PsIngrassiaScraper, PsPartinicoScraper, PsCorleoneScraper, 
    PsPetraliaScraper, PsTerminiScraper
)
from .arnas_civico import PoCivicoAdultiScraper, PoCivicoPediatricoScraper
from .policlinico_catania import PoRodolicoScraper, PoSanMarcoScraper
# ASP Messina - Solo Policlinico e Papardo attivi
from .ao_papardo import AoPapardoScraper
from .policlinico_messina import PoliclinicoMessinaScraper

# Registrazione dei mapping ID-codice degli ospedali
hospital_mappings = [
    (1, HospitalCode.PO_CERVELLO_ADULTI),
    (2, HospitalCode.PO_VILLA_SOFIA_ADULTI),
    (3, HospitalCode.PO_CERVELLO_PEDIATRICO),
    (4, HospitalCode.POLICLINICO_PALERMO),
    (5, HospitalCode.PS_SCIACCA),
    (6, HospitalCode.PS_RIBERA),
    (7, HospitalCode.PS_AGRIGENTO),
    (8, HospitalCode.PS_CANICATTI),
    (9, HospitalCode.PS_LICATA),
    (10, HospitalCode.PS_SANTELIA),
    (11, HospitalCode.PS_INGRASSIA),
    (12, HospitalCode.PS_PARTINICO),
    (13, HospitalCode.PS_CORLEONE),
    (14, HospitalCode.PS_PETRALIA),
    (15, HospitalCode.PS_TERMINI),
    (16, HospitalCode.PO_CIVICO_ADULTI),
    (17, HospitalCode.PO_CIVICO_PEDIATRICO),
    (18, HospitalCode.PO_RODOLICO),
    (19, HospitalCode.PO_SAN_MARCO),
    # ASP Messina - Solo Policlinico e Papardo attivi
    (20, HospitalCode.AO_PAPARDO),
    (21, HospitalCode.POLICLINICO_MESSINA)
]

for hosp_id, hosp_code in hospital_mappings:
    HospitalRegistry.register(hosp_id, hosp_code)

# Registrazione degli scraper nella factory
scrapers = [
    POCervelloAdultiScraper,
    POCervelloPediatricoScraper,
    POVillaSofiaAdultiScraper,
    PoliclinicoPalermoScraper,
    PsSciacca,
    PsRibera,
    PsLicata,
    PsCanicatti,
    PsAgrigento,
    PsSantEliaScraper,
    PsIngrassiaScraper,
    PsPartinicoScraper,
    PsCorleoneScraper,
    PsPetraliaScraper,
    PsTerminiScraper,
    PoCivicoAdultiScraper,
    PoCivicoPediatricoScraper,
    PoRodolicoScraper,
    PoSanMarcoScraper,
    AoPapardoScraper,
    PoliclinicoMessinaScraper
]

for scraper in scrapers:
    ScraperFactory.register_scraper(scraper) 
