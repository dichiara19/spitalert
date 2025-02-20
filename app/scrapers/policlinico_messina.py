"""
Scraper per il Pronto Soccorso del Policlinico G. Martino di Messina.
URL: https://www.polime.it/ps_view.php?PS=1
"""

from typing import Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from .base import BaseHospitalScraper
from .hospital_codes import HospitalCode
from ..schemas import HospitalStatusCreate, ColorCodeDistribution

class PoliclinicoMessinaScraper(BaseHospitalScraper):
    """Scraper per il Pronto Soccorso del Policlinico di Messina"""
    
    hospital_code = HospitalCode.POLICLINICO_MESSINA
    BASE_URL = "https://www.polime.it/ps_view.php?PS=1"
    
    async def validate_data(self) -> bool:
        """
        Valida i dati ottenuti dallo scraping.
        
        Returns:
            bool: True se i dati sono validi, False altrimenti
        """
        try:
            data = await self.scrape()
            
            # Verifica che ci sia una distribuzione dei codici colore
            if not data.color_distribution:
                self.logger.warning("Distribuzione codici colore mancante")
                return False
                
            # Verifica che il totale dei pazienti sia coerente con la distribuzione
            total = sum([
                data.color_distribution.white,
                data.color_distribution.green,
                data.color_distribution.blue,
                data.color_distribution.orange,
                data.color_distribution.red
            ])
            
            if total != data.total_patients:
                self.logger.warning(
                    f"Totale pazienti non coerente: {total} vs {data.total_patients}"
                )
                return False
                
            # Verifica che ci sia una data di aggiornamento
            if not data.external_last_update:
                self.logger.warning("Data di aggiornamento mancante")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Validazione fallita: {str(e)}", exc_info=True)
            return False
    
    async def scrape(self) -> HospitalStatusCreate:
        """
        Esegue lo scraping dei dati dal Pronto Soccorso.
        
        Returns:
            HospitalStatusCreate: Dati del pronto soccorso
        """
        # Ottieni la pagina HTML
        html = await self.get_page(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Estrai la data di aggiornamento
        date_cell = soup.find('td', style='font-size:30px;')
        if date_cell:
            date_str = date_cell.text.strip().split(' - ')[0]
            time_str = date_cell.text.strip().split(' - ')[1]
            external_last_update = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
        else:
            external_last_update = datetime.now()
        
        # Inizializza il conteggio dei codici
        color_counts: Dict[str, int] = {
            "white": 0,
            "green": 0,
            "blue": 0,
            "orange": 0,
            "red": 0
        }
        
        # Trova la tabella principale
        table = soup.find('table', border='1')
        if not table:
            self.logger.error("Tabella dati non trovata")
            return self._create_empty_status()
        
        # Analizza le righe della tabella
        for row in table.find_all('tr')[1:]:  # Salta l'header
            cells = row.find_all('td')
            if len(cells) >= 6:
                # Somma i pazienti per ogni codice colore
                if cells[1].text.strip():  # Bianchi
                    color_counts["white"] += int(cells[1].text.strip())
                if cells[2].text.strip():  # Verdi
                    color_counts["green"] += int(cells[2].text.strip())
                if cells[3].text.strip():  # Azzurri
                    color_counts["blue"] += int(cells[3].text.strip())
                if cells[4].text.strip():  # Arancioni
                    color_counts["orange"] += int(cells[4].text.strip())
                if cells[5].text.strip():  # Rossi
                    color_counts["red"] += int(cells[5].text.strip())
        
        # Calcola il totale dei pazienti
        total_patients = sum(color_counts.values())
        
        # Crea la distribuzione dei codici colore
        color_distribution = ColorCodeDistribution(
            white=color_counts["white"],
            green=color_counts["green"],
            blue=color_counts["blue"],
            orange=color_counts["orange"],
            red=color_counts["red"]
        )
        
        # Calcola il tempo di attesa stimato (non fornito direttamente)
        estimated_waiting_time = self._estimate_waiting_time(color_distribution)
        
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            color_distribution=color_distribution,
            total_patients=total_patients,
            estimated_waiting_time=estimated_waiting_time,
            external_last_update=external_last_update
        )
    
    def _estimate_waiting_time(self, color_dist: ColorCodeDistribution) -> Optional[int]:
        """
        Stima il tempo di attesa in base alla distribuzione dei codici colore.
        Questa è una stima approssimativa basata sul numero di pazienti e la loro gravità.
        
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