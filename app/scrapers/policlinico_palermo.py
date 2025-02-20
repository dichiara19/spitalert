from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class PoliclinicoPalermoScraper(BaseHospitalScraper):
    """
    Scraper per il Pronto Soccorso del Policlinico di Palermo.
    Utilizza gli endpoint REST ufficiali dell'ospedale.
    """
    hospital_code = HospitalCode.POLICLINICO_PALERMO
    is_api_based = True  # Flag per indicare che questo scraper usa API invece di HTML
    
    BASE_URL = "https://www.policlinico.pa.it/o/PoliclinicoPaRestBuilder/v1.0"
    ENDPOINTS = {
        "status": "/ProntoSoccorso",
        "indices": "/ProntoSoccorsoIndici"
    }

    # Selettori vuoti perché usiamo API REST invece di HTML
    hospital_selectors = {
        "container": "",
        "waiting_time": "",
        "patients_waiting": "",
        "color_code": "",
        "available_beds": ""
    }

    # Mappatura dei codici colore del Policlinico ai nostri
    COLOR_MAPPING = {
        'Rosso': 'red',
        'Arancione': 'orange',
        'Azzurro': 'blue',  # Il Policlinico usa Azzurro invece di Blu
        'Verde': 'green',
        'Bianco': 'white'
    }

    # Ordine di priorità dei codici (dal più al meno critico)
    COLOR_PRIORITY = [
        'Rosso (1)',
        'Arancione (2)', 
        'Azzurro (3)',
        'Verde (4)',
        'Bianco (5)'
    ]

    def _get_color_and_count(self, data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Determina il codice colore più critico e il numero totale di pazienti.
        
        Args:
            data: Dati grezzi dall'API
            
        Returns:
            Tuple[str, int]: (codice colore normalizzato, totale pazienti)
        """
        total_patients = 0
        highest_color = 'unknown'
        
        # Controlla prima i pazienti in attesa
        for color in self.COLOR_PRIORITY:
            patients = int(float(data['pazientiInAttesa'].get(color, 0)))
            if patients > 0:
                clean_color = color.split('(')[0].strip()
                highest_color = self.COLOR_MAPPING.get(clean_color, 'unknown')
                break
            total_patients += patients
            
        # Se non ci sono pazienti in attesa, controlla i carichi di urgenza
        if highest_color == 'unknown':
            for color in self.COLOR_PRIORITY:
                if float(data['carichiUrgenza'].get(color, 0)) > 0:
                    clean_color = color.split('(')[0].strip()
                    highest_color = self.COLOR_MAPPING.get(clean_color, 'unknown')
                    break
        
        return highest_color, total_patients

    def _calculate_waiting_time(self, data: Dict[str, Any], color_code: str) -> int:
        """
        Calcola il tempo di attesa appropriato per il codice colore corrente.
        
        Args:
            data: Dati grezzi dall'API
            color_code: Codice colore normalizzato
            
        Returns:
            int: Tempo di attesa in minuti
        """
        try:
            # Mappa i nostri codici colore a quelli del Policlinico
            reverse_mapping = {v: k for k, v in self.COLOR_MAPPING.items()}
            target_color = None
            
            # Trova il colore corrispondente nei dati
            for color in self.COLOR_PRIORITY:
                clean_color = color.split('(')[0].strip()
                if clean_color == reverse_mapping.get(color_code):
                    target_color = color
                    break
            
            if not target_color:
                self.logger.warning(f"Nessun colore target trovato per {color_code}")
                return 0
                
            # Prendi il tempo di attesa per quel colore
            time_str = data['tempiMediAttesa'].get(target_color)
            if not time_str:
                self.logger.warning(f"Nessun tempo di attesa trovato per {target_color}")
                return 0
                
            waiting_time = self._parse_time_str(time_str)
            self.logger.debug(f"Tempo di attesa calcolato per {target_color}: {waiting_time} minuti")
            return waiting_time
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo del tempo di attesa: {str(e)}")
            return 0

    def _get_available_beds(self, indices_data: Dict[str, Any]) -> int:
        """
        Calcola il numero di posti letto disponibili.
        
        Args:
            indices_data: Dati dagli indici
            
        Returns:
            int: Numero di posti disponibili
        """
        try:
            total_beds = int(indices_data['postiTecniciPresidiati'])
            occupied_24h = int(indices_data['permanenza24H'].split()[0])
            occupied_over_24h = int(indices_data['permanenzaOltre24H'].split()[0])
            
            available = total_beds - (occupied_24h + occupied_over_24h)
            return max(0, available)  # Non permettiamo numeri negativi
        except (ValueError, KeyError, IndexError):
            self.logger.warning("Errore nel calcolo dei posti disponibili")
            return 0

    async def get_page(self, url: str, **kwargs) -> str:
        """
        Sovrascrive il metodo get_page per gestire le chiamate all'URL base.
        Per il Policlinico, non abbiamo bisogno di fare scraping HTML,
        quindi restituiamo una stringa vuota se viene richiesto l'URL base.
        
        Args:
            url: URL della pagina
            **kwargs: Parametri aggiuntivi per la richiesta HTTP
            
        Returns:
            str: Contenuto della pagina o stringa vuota per l'URL base
        """
        if url == self.BASE_URL:
            return ""  # Non abbiamo bisogno di fare scraping HTML
        return await super().get_page(url, **kwargs)

    def _parse_time_str(self, time_str: str) -> int:
        """
        Converte una stringa di tempo nel formato "Xh  Ym" in minuti.
        
        Args:
            time_str: Stringa nel formato "Xh  Ym" (es. "3h  13m")
            
        Returns:
            int: Tempo totale in minuti
        """
        try:
            if not time_str:
                return 0
                
            # Rimuove spazi extra e converte in minuscolo
            time_str = time_str.lower().strip()
            
            # Estrae ore e minuti
            hours = 0
            minutes = 0
            
            if 'h' in time_str:
                parts = time_str.split('h')
                hours_part = parts[0].strip()
                if hours_part and hours_part.isdigit():
                    hours = int(hours_part)
                
                if len(parts) > 1:
                    minutes_part = parts[1].replace('m', '').strip()
                    if minutes_part and minutes_part.isdigit():
                        minutes = int(minutes_part)
            elif 'm' in time_str:
                minutes_part = time_str.replace('m', '').strip()
                if minutes_part and minutes_part.isdigit():
                    minutes = int(minutes_part)
            elif time_str.isdigit():  # Solo un numero, assumiamo minuti
                minutes = int(time_str)
            else:
                self.logger.warning(f"Formato tempo non riconosciuto: {time_str}")
                return 0
                
            return (hours * 60) + minutes
            
        except Exception as e:
            self.logger.error(f"Errore nel parsing del tempo '{time_str}': {str(e)}")
            return 0

    def _map_color_code(self, color: str) -> str:
        """
        Mappa i codici colore specifici del Policlinico allo standard SpitAlert.
        
        Args:
            color: Codice colore dal Policlinico
            
        Returns:
            str: Codice colore normalizzato
        """
        # Rimuove il numero tra parentesi e spazi
        clean_color = color.split('(')[0].strip()
        
        # Mappatura specifica per il Policlinico
        color_mapping = {
            'Rosso': 'red',
            'Arancione': 'orange',
            'Azzurro': 'blue',  # Il Policlinico usa Azzurro invece di Blu
            'Verde': 'green',
            'Bianco': 'white',
            'Nero': 'black'  # Non usato in SpitAlert, ma presente nell'API
        }
        
        return color_mapping.get(clean_color, 'unknown')

    def _get_highest_priority_color(self, data: Dict[str, Any]) -> str:
        """
        Determina il codice colore più critico tra i pazienti in attesa.
        
        Args:
            data: Dati grezzi dall'API del Policlinico
            
        Returns:
            str: Codice colore normalizzato più critico
        """
        # Ordine di priorità dei colori (dal più al meno critico)
        priority_order = ['Rosso (1)', 'Arancione (2)', 'Azzurro (3)', 'Verde (4)', 'Bianco (5)']
        
        for color in priority_order:
            if data['pazientiInAttesa'].get(color, 0) > 0:
                return self._map_color_code(color)
        
        return 'unknown'

    def _calculate_total_waiting_time(self, data: Dict[str, Any]) -> int:
        """
        Calcola il tempo medio di attesa pesato sul numero di pazienti.
        
        Args:
            data: Dati grezzi dall'API del Policlinico
            
        Returns:
            int: Tempo medio di attesa in minuti
        """
        total_patients = 0
        weighted_time = 0
        
        for color, time_str in data['tempiMediAttesa'].items():
            if color == 'Nero':  # Ignora il codice nero
                continue
                
            patients = float(data['pazientiInAttesa'].get(color, 0))
            if patients > 0:
                waiting_time = self._parse_time_str(time_str)
                if waiting_time is not None:
                    weighted_time += waiting_time * patients
                    total_patients += patients
        
        if total_patients > 0:
            return int(weighted_time / total_patients)
        return 0

    async def get_endpoint_url(self, endpoint: str) -> str:
        """
        Costruisce l'URL completo per un endpoint.
        
        Args:
            endpoint: Nome dell'endpoint
            
        Returns:
            str: URL completo dell'endpoint
        """
        return f"{self.BASE_URL}{self.ENDPOINTS[endpoint]}"

    async def get_color_distribution(self) -> Optional[ColorCodeDistribution]:
        """
        Recupera la distribuzione dei codici colore dall'API.
        """
        try:
            status_data = await self.get_json(await self.get_endpoint_url("status"))
            
            return ColorCodeDistribution(
                white=int(float(status_data['pazientiInAttesa'].get('Bianco (5)', 0))),
                green=int(float(status_data['pazientiInAttesa'].get('Verde (4)', 0))),
                blue=int(float(status_data['pazientiInAttesa'].get('Azzurro (3)', 0))),
                orange=int(float(status_data['pazientiInAttesa'].get('Arancione (2)', 0))),
                red=int(float(status_data['pazientiInAttesa'].get('Rosso (1)', 0)))
            )
        except Exception as e:
            self.logger.error(f"Errore nel recupero della distribuzione colori: {str(e)}")
            return None

    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati dal Policlinico.
        
        Returns:
            HospitalStatusCreate: Dati formattati secondo lo schema SpitAlert
        """
        # Recupera i dati da entrambi gli endpoint
        status_data = await self.get_json(await self.get_endpoint_url("status"))
        indices_data = await self.get_json(await self.get_endpoint_url("indices"))
        
        # Determina il codice colore e il numero di pazienti
        color_code, patients_waiting = self._get_color_and_count(status_data)
        
        # Calcola il tempo di attesa per il codice colore corrente
        waiting_time = self._calculate_waiting_time(status_data, color_code)
        
        # Calcola i posti letto disponibili
        available_beds = self._get_available_beds(indices_data)
        
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
            external_last_update=datetime.utcnow()  # L'API non fornisce questo dato
        )

    async def validate_data(self) -> bool:
        """
        Valida i dati ottenuti dallo scraping.
        
        Returns:
            bool: True se i dati sono validi, False altrimenti
        """
        try:
            # Verifica che entrambi gli endpoint siano accessibili
            status_data = await self.get_json(await self.get_endpoint_url("status"))
            indices_data = await self.get_json(await self.get_endpoint_url("indices"))
            
            # Verifica la presenza dei campi necessari
            required_status_fields = ['pazientiInAttesa', 'tempiMediAttesa']
            required_indices_fields = ['postiTecniciPresidiati']
            
            if not all(field in status_data for field in required_status_fields):
                self.logger.error("Campi mancanti nei dati di stato")
                return False
                
            if not all(field in indices_data for field in required_indices_fields):
                self.logger.error("Campi mancanti nei dati degli indici")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore durante la validazione: {str(e)}")
            return False 