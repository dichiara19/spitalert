from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class BasePoliclinicoCataniaScraper(BaseHospitalScraper):
    """
    Classe base per gli scraper dei PS del Policlinico di Catania.
    Implementa la logica comune per le chiamate API.
    """
    BASE_URL = "https://www.policlinicorodolicosanmarco.it"
    is_api_based = True
    
    # Mappatura dei codici colore del Policlinico ai nostri
    COLOR_MAPPING = {
        'rossi': 'red',
        'gialli': 'orange',
        'verdi': 'green',
        'bianchi': 'white'
    }
    
    async def _get_hospital_data(self) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati grezzi dall'API.
        
        Returns:
            Optional[Dict[str, Any]]: Dizionario con i dati o None se non trovati
        """
        try:
            # Costruisci l'URL dell'API
            api_url = f"{self.BASE_URL}/api/smarteus/getpsinfo/{self.ps_id}"
            
            # Chiama l'API
            data = await self.get_json(api_url)
            if not data:
                self.logger.warning(f"Nessun dato trovato per {self.hospital_name}")
                return None
                
            return data
            
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati per {self.hospital_name}: {str(e)}")
            return None
    
    def _parse_update_date(self, date_str: str) -> Optional[datetime]:
        """
        Converte la stringa della data in oggetto datetime.
        Formato atteso: "DD/MM/YYYY HH:mm:ss"
        """
        try:
            return datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
        except Exception as e:
            self.logger.error(f"Errore nel parsing della data '{date_str}': {str(e)}")
            return None
    
    async def get_color_distribution(self) -> Optional[ColorCodeDistribution]:
        """
        Recupera la distribuzione dei codici colore.
        
        Returns:
            Optional[ColorCodeDistribution]: Distribuzione dei codici colore o None in caso di errore
        """
        try:
            data = await self._get_hospital_data()
            if not data:
                return None
            
            # Somma i pazienti per ogni colore (attesa + trattamento + OBI)
            total_by_color = {
                'rossi': (
                    int(data['pazientiInAttesa']['rossi']) +
                    int(data['pazientiInTrattamento']['rossi']) +
                    int(data['pazientiInObi']['rossi'])
                ),
                'gialli': (
                    int(data['pazientiInAttesa']['gialli']) +
                    int(data['pazientiInTrattamento']['gialli']) +
                    int(data['pazientiInObi']['gialli'])
                ),
                'verdi': (
                    int(data['pazientiInAttesa']['verdi']) +
                    int(data['pazientiInTrattamento']['verdi']) +
                    int(data['pazientiInObi']['verdi'])
                ),
                'bianchi': (
                    int(data['pazientiInAttesa']['bianchi']) +
                    int(data['pazientiInTrattamento']['bianchi']) +
                    int(data['pazientiInObi']['bianchi'])
                )
            }
            
            return ColorCodeDistribution(
                red=total_by_color['rossi'],
                orange=total_by_color['gialli'],
                blue=0,  # Il Policlinico non usa il codice blu
                green=total_by_color['verdi'],
                white=total_by_color['bianchi']
            )
        except Exception as e:
            self.logger.error(f"Errore nel recupero della distribuzione colori: {str(e)}")
            return None
    
    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati dal Pronto Soccorso.
        
        Returns:
            HospitalStatusCreate: Dati formattati secondo lo schema SpitAlert
        """
        # Recupera i dati grezzi
        data = await self._get_hospital_data()
        if not data:
            raise ValueError(f"Impossibile recuperare i dati per {self.hospital_name}")
        
        # Estrai la data di aggiornamento
        update_time = self._parse_update_date(data['dataOraInviante'])
        
        # Calcola il numero di pazienti in attesa
        patients_waiting = int(data['pazientiInAttesa']['totale'])
        
        # Determina il codice colore più critico
        color_code = 'unknown'
        for color in ['rossi', 'gialli', 'verdi', 'bianchi']:
            if int(data['pazientiInAttesa'][color]) > 0:
                color_code = self.COLOR_MAPPING[color]
                break
        
        # Calcola il numero totale di pazienti
        total_patients = (
            int(data['pazientiInAttesa']['totale']) +
            int(data['pazientiInTrattamento']['totale']) +
            int(data['pazientiInObi']['totale'])
        )
        
        # Stima il numero di posti letto disponibili
        available_beds = max(0, self.total_beds - total_patients)
        
        # Stima il tempo di attesa basato sul numero di pazienti in attesa
        waiting_time = patients_waiting * 30  # 30 minuti per paziente come stima
        
        # Ottieni la distribuzione dei codici colore
        color_distribution = await self.get_color_distribution()
        
        # Crea l'oggetto di risposta
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            color_code=color_code,
            waiting_time=waiting_time,
            patients_waiting=patients_waiting,
            available_beds=available_beds,
            color_distribution=color_distribution,
            last_updated=datetime.utcnow(),
            external_last_update=update_time
        )
    
    async def validate_data(self) -> bool:
        """
        Valida i dati ottenuti dallo scraping.
        
        Returns:
            bool: True se i dati sono validi, False altrimenti
        """
        try:
            data = await self._get_hospital_data()
            if not data:
                self.logger.warning(f"Nessun dato trovato per {self.hospital_name}")
                return False
            
            # Verifica la presenza della data di aggiornamento
            if not data.get('dataOraInviante'):
                self.logger.warning(f"Data di aggiornamento mancante per {self.hospital_name}")
                return False
            
            # Verifica che tutti i conteggi siano numeri non negativi
            for status in ['pazientiInAttesa', 'pazientiInTrattamento', 'pazientiInObi']:
                if not data.get(status):
                    self.logger.warning(f"Dati mancanti per {status} in {self.hospital_name}")
                    return False
                    
                for color in ['totale', 'bianchi', 'verdi', 'gialli', 'rossi']:
                    try:
                        count = int(data[status][color])
                        if count < 0:
                            self.logger.warning(f"Conteggio negativo per {color} in {status}: {count}")
                            return False
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Errore nel parsing del conteggio per {color} in {status}: {str(e)}")
                        return False
            
            # Log dei dati validi
            self.logger.debug(f"Dati validati per {self.hospital_name}:")
            self.logger.debug(f"- In attesa: {data['pazientiInAttesa']}")
            self.logger.debug(f"- In trattamento: {data['pazientiInTrattamento']}")
            self.logger.debug(f"- In OBI: {data['pazientiInObi']}")
            self.logger.debug(f"- Data aggiornamento: {data['dataOraInviante']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione per {self.hospital_name}: {str(e)}")
            return False

class PoRodolicoScraper(BasePoliclinicoCataniaScraper):
    """Scraper per il P.O. G. Rodolico"""
    hospital_code = HospitalCode.PO_RODOLICO
    hospital_name = "PRONTO SOCCORSO RODOLICO"
    ps_id = "105"  # ID del PS nell'API
    total_beds = 40  # Numero di posti letto stimato

class PoSanMarcoScraper(BasePoliclinicoCataniaScraper):
    """Scraper per il P.O. San Marco"""
    hospital_code = HospitalCode.PO_SAN_MARCO
    hospital_name = "PRONTO SOCCORSO SAN MARCO"
    ps_id = "106"  # ID del PS nell'API
    total_beds = 35  # Numero di posti letto stimato 