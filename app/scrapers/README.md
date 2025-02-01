# SpitAlert Scrapers

Questo modulo contiene l'implementazione degli scraper per i vari ospedali supportati da SpitAlert.

## Struttura

```
scrapers/
├── base.py           # Classe base per gli scraper
├── factory.py        # Factory per la creazione degli scraper
├── hospital_codes.py # Enumerazione dei codici ospedale
└── examples/         # Esempi di implementazione
```

## Componenti Principali

### BaseHospitalScraper

La classe base astratta che definisce l'interfaccia comune per tutti gli scraper:

```python
from .hospital_codes import HospitalCode

class BaseHospitalScraper(ABC, LoggerMixin):
    hospital_code: ClassVar[HospitalCode]  # Deve essere definito nelle classi derivate
    
    async def scrape(self) -> HospitalStatusCreate:
        pass  # Da implementare
        
    async def validate_data(self) -> bool:
        pass  # Da implementare
```

#### Funzionalità Chiave

1. **HTTP Client Robusto**
   - Timeout configurabile
   - Retry automatico con backoff esponenziale
   - Gestione degli errori HTTP
   - Logging dettagliato
   ```python
   async def get_page(self, url: str, **kwargs) -> str:
       return await self.http_client.get_text(url, **kwargs)
       
   async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
       return await self.http_client.get_json(url, **kwargs)
   ```

2. **Parsing Tempi di Attesa**
   - Supporto per molteplici formati:
     - "2 ore e 30 minuti"
     - "45 min"
     - "1h 30m"
     - "2:30"
     - "150 minuti"
   - Logging dettagliato del processo
   - Gestione robusta degli errori

3. **Normalizzazione Codici Colore**
   - Mappatura standardizzata:
     - white/bianco → white
     - green/verde → green
     - blue/blu → blue
     - orange/arancione/yellow/giallo → orange
     - red/rosso → red
   - Logging delle conversioni non standard

## Implementazione di un Nuovo Scraper

1. **Definizione della Classe**
```python
from ..scrapers.base import BaseHospitalScraper
from ..scrapers.hospital_codes import HospitalCode

class MioOspedaleScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.MIO_OSPEDALE
    
    async def scrape(self) -> HospitalStatusCreate:
        # Implementazione dello scraping
        page = await self.get_page("https://mio-ospedale.it/pronto-soccorso")
        
        # Parsing dei dati
        waiting_time = self.parse_waiting_time("45 min")
        color_code = self.normalize_color_code("verde")
        
        return HospitalStatusCreate(
            hospital_id=self.hospital_id,
            waiting_time=waiting_time,
            color_code=color_code,
            available_beds=10
        )
        
    async def validate_data(self) -> bool:
        # Validazione personalizzata
        try:
            data = await self.scrape()
            return all([
                data.waiting_time is not None,
                data.color_code != "unknown",
                data.available_beds >= 0
            ])
        except Exception as e:
            self.logger.error(f"Errore durante la validazione: {str(e)}")
            return False
```

2. **Registrazione nel Factory**
```python
from .factory import ScraperFactory
from .mio_ospedale import MioOspedaleScraper

ScraperFactory.register(MioOspedaleScraper)
```

## Best Practices

### 1. Gestione HTTP
- Utilizzare sempre i metodi `get_page()` e `get_json()` della classe base
- Non implementare chiamate HTTP dirette nei singoli scraper
- Configurare timeout appropriati per l'ospedale specifico

```python
# ✅ Corretto
page = await self.get_page(url, timeout=45.0)

# ❌ Errato
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### 2. Parsing dei Tempi
- Utilizzare il parser centralizzato per i tempi di attesa
- Gestire casi specifici dell'ospedale prima della normalizzazione

```python
# ✅ Corretto
raw_time = "2 ore e mezza"
normalized = raw_time.replace("mezza", "30")
waiting_time = self.parse_waiting_time(normalized)

# ❌ Errato
hours = int(raw_time.split()[0])
waiting_time = hours * 60
```

### 3. Codici Colore
- Utilizzare sempre il normalizzatore di codici colore
- Aggiungere mappature specifiche se necessario

```python
# ✅ Corretto
color = self.normalize_color_code(raw_color)

# ❌ Errato
color = raw_color.lower()
```

### 4. Logging
- Utilizzare il logger ereditato da `LoggerMixin`
- Loggare informazioni utili per il debugging
- Utilizzare i livelli appropriati (DEBUG, INFO, WARNING, ERROR)

```python
# ✅ Corretto
self.logger.debug(f"Dati grezzi ricevuti: {raw_data}")
self.logger.info(f"Scraping completato per {self.hospital_code}")
self.logger.warning(f"Formato tempo non standard: {time_str}")
self.logger.error(f"Errore durante lo scraping", exc_info=True)

# ❌ Errato
print(f"Errore: {e}")
```

### 5. Validazione
- Implementare controlli specifici per l'ospedale
- Validare tutti i campi obbligatori
- Loggare dettagli sui fallimenti

```python
# ✅ Corretto
async def validate_data(self) -> bool:
    try:
        data = await self.scrape()
        if not data.waiting_time:
            self.logger.warning("Tempo di attesa mancante")
            return False
        return True
    except Exception as e:
        self.logger.error(f"Validazione fallita: {str(e)}")
        return False

# ❌ Errato
async def validate_data(self) -> bool:
    return True  # Sempre valido
```

## Configurazione

Le configurazioni degli scraper sono gestite centralmente tramite il file `.env`:

```env
# HTTP Client
HTTP_TIMEOUT=30.0
HTTP_MAX_RETRIES=3
HTTP_USER_AGENT="SpitAlert/1.0"

# Scraping
SCRAPE_CONCURRENT_TASKS=5
SCRAPE_TIMEOUT=60.0
```

## Testing

Ogni scraper dovrebbe includere test per:
1. Parsing dei tempi di attesa
2. Normalizzazione dei codici colore
3. Gestione degli errori HTTP
4. Validazione dei dati
5. Casi limite e formati inaspettati
