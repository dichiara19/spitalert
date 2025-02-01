# SpitAlert Scrapers

Questo modulo contiene l'implementazione degli scraper per i vari ospedali supportati da SpitAlert.

## Struttura

```text
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

### 1. Pattern per Scraper Multipli dello Stesso Ospedale

Se uno scraper deve gestire più dipartimenti dello stesso ospedale, utilizzare una classe base comune:

```python
class BaseOspedaleRiunitiScraper(BaseHospitalScraper):
    """Classe base per gli scraper dell'ospedale"""
    BASE_URL = "https://ospedale.it/pronto-soccorso"
    
    async def scrape(self) -> HospitalStatusCreate:
        # Implementazione comune
        pass

class ProntoSoccorsoAdultiScraper(BaseOspedaleRiunitiScraper):
    """Scraper specifico per PS Adulti"""
    hospital_code = HospitalCode.PS_ADULTI

class ProntoSoccorsoPediatricoScraper(BaseOspedaleRiunitiScraper):
    """Scraper specifico per PS Pediatrico"""
    hospital_code = HospitalCode.PS_PEDIATRICO
```

### 2. Registrazione nel Factory

IMPORTANTE: Registrare OGNI classe specifica, non la classe base:

```python
# ✅ Corretto
from .factory import ScraperFactory
from .ospedale_riuniti import (
    ProntoSoccorsoAdultiScraper,
    ProntoSoccorsoPediatricoScraper
)

ScraperFactory.register_scraper(ProntoSoccorsoAdultiScraper)
ScraperFactory.register_scraper(ProntoSoccorsoPediatricoScraper)

# ❌ Errato
ScraperFactory.register_scraper(BaseOspedaleRiunitiScraper)
```

## Errori Comuni e Soluzioni

### 1. Errore: "Nessuno scraper registrato per l'ospedale"

```python
ValueError: Nessuno scraper registrato per l'ospedale: HospitalCode.PS_ADULTI
```

Cause comuni:

- Scraper non registrato nel factory
- Hospital code non definito nella classe
- Classe base registrata invece delle classi specifiche

Soluzione:

```python
# 1. Definire l'hospital_code nella classe
class MioScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_ADULTI  # ✅ Obbligatorio

# 2. Registrare lo scraper in __init__.py
ScraperFactory.register_scraper(MioScraper)  # ✅ Non dimenticare
```

### 2. Errore: "La classe deve definire l'attributo hospital_code"

```python
AttributeError: La classe MioScraper deve definire l'attributo 'hospital_code'
```

Cause comuni:

- Attributo `hospital_code` mancante
- Attributo definito nel posto sbagliato
- Valore non valido per `hospital_code`

Soluzione:

```python
# ✅ Corretto
class MioScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_ADULTI  # Come attributo di classe

# ❌ Errato
class MioScraper(BaseHospitalScraper):
    def __init__(self):
        self.hospital_code = HospitalCode.PS_ADULTI  # Come attributo di istanza
```

### 3. Errore: "Scraper già registrato per il codice ospedale"

```python
ValueError: Scraper già registrato per il codice ospedale: HospitalCode.PS_ADULTI
```

Cause comuni:

- Stesso `hospital_code` usato in più scraper
- Registrazione duplicata dello stesso scraper

Soluzione:

```python
# ✅ Corretto: Codici univoci per ogni scraper
class PSAdultiScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_ADULTI

class PSPediatricoScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_PEDIATRICO

# ❌ Errato: Stesso codice usato più volte
class PSAdultiScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_ADULTI

class PSEmergenzaScraper(BaseHospitalScraper):
    hospital_code = HospitalCode.PS_ADULTI  # Duplicato!
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
