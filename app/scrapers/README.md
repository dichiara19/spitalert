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
    is_api_based: ClassVar[bool] = False   # True per scraper basati su API
    
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
   - Supporto per chiamate REST API e scraping HTML

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

## Tipi di Scraper

### 1. Scraper HTML

Per ospedali che espongono i dati tramite pagine web HTML:

```python
class HTMLBasedScraper(BaseHospitalScraper):
    """Scraper che utilizza parsing HTML"""
    hospital_code = HospitalCode.EXAMPLE_HOSPITAL
    is_api_based = False  # Default, può essere omesso
    
    # Selettori CSS per l'estrazione dei dati
    hospital_selectors = {
        "container": ".hospital-status",
        "waiting_time": ".waiting-time",
        "patients_waiting": ".patients-count",
        "color_code": ".triage-color",
        "available_beds": ".available-beds"
    }
    
    async def scrape(self) -> HospitalStatusCreate:
        html = await self.get_page(self.BASE_URL)
        # Implementa il parsing HTML
```

### 2. Scraper API REST

Per ospedali che forniscono API REST:

```python
class APIBasedScraper(BaseHospitalScraper):
    """Scraper che utilizza API REST"""
    hospital_code = HospitalCode.EXAMPLE_API_HOSPITAL
    is_api_based = True
    
    BASE_URL = "https://api.hospital.com/v1"
    ENDPOINTS = {
        "status": "/status",
        "details": "/details"
    }
    
    async def get_endpoint_url(self, endpoint: str) -> str:
        return f"{self.BASE_URL}{self.ENDPOINTS[endpoint]}"
        
    async def get_color_distribution(self) -> Optional[ColorCodeDistribution]:
        """Metodo specifico per scraper API"""
        data = await self.get_json(await self.get_endpoint_url("status"))
        return ColorCodeDistribution(...)
```

## Implementazione di un Nuovo Scraper

### 1. Scegliere il Tipo di Scraper

Prima di implementare, determinare se l'ospedale espone:

- Pagina web HTML → Usare scraping HTML
- API REST → Usare chiamate API dirette

### 2. Pattern per Scraper Multipli dello Stesso Ospedale

Se uno scraper deve gestire più dipartimenti dello stesso ospedale, utilizzare una classe base comune:

```python
class BaseOspedaleRiunitiScraper(BaseHospitalScraper):
    """Classe base per gli scraper dell'ospedale"""
    BASE_URL = "https://ospedale.it/pronto-soccorso"
    is_api_based = False  # o True se usa API
    
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

### 3. Registrazione nel Factory

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

## Verifica degli Scraper

Prima di considerare completo uno scraper, verificare che:

1. **Distribuzione dei Colori**
   - Il metodo `get_color_distribution()` sia implementato
   - Il metodo `ensure_color_distribution()` sia presente per gestire casi di errore
   - La distribuzione dei colori sia correttamente mappata allo schema SpitAlert

2. **Gestione degli Errori**
   - Tutti i metodi che fanno chiamate esterne usino try/catch
   - Gli errori siano loggati con il livello appropriato
   - In caso di errore, venga restituito un valore di fallback valido

3. **Validazione dei Dati**
   - Il metodo `validate_data()` controlli tutti i campi obbligatori
   - I conteggi dei pazienti siano numeri non negativi
   - Le date di aggiornamento siano valide

4. **Conformità allo Schema**
   - Tutti i campi richiesti da `HospitalStatusCreate` siano presenti
   - I tipi di dati siano corretti (es. `color_distribution` sia di tipo `ColorCodeDistribution`)
   - I valori di default siano gestiti appropriatamente

## Analisi Preliminare delle API

Prima di implementare uno scraper HTML, è consigliabile verificare se l'ospedale espone delle API. Ecco alcuni comandi utili:

### 1. Analisi delle Richieste XHR

```bash
# Monitora tutte le richieste XHR durante la navigazione
curl -H "X-Requested-With: XMLHttpRequest" "https://ospedale.example.com/pronto-soccorso"

# Prova diversi header comuni
curl -H "Accept: application/json" "https://ospedale.example.com/api/status"
curl -H "Content-Type: application/json" "https://ospedale.example.com/api/ps"
```

### 2. Endpoint Comuni

```bash
# Prova pattern comuni di endpoint
curl "https://ospedale.example.com/api/v1/pronto-soccorso"
curl "https://ospedale.example.com/api/ps/status"
curl "https://ospedale.example.com/api/waiting-times"
curl "https://ospedale.example.com/api/emergency/data"
```

### 3. Analisi dei WebSocket

```bash
# Se il sito usa WebSocket per aggiornamenti in tempo reale
wscat -c "wss://ospedale.example.com/ws/ps-status"
```

### 4. Verifica GraphQL

```bash
# Se il sito usa GraphQL
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "{ prontoSoccorso { waitingTimes } }"}' \
  "https://ospedale.example.com/graphql"
```

### 5. Monitoraggio del Network

- Usa gli strumenti di sviluppo del browser (Network tab)
- Filtra per XHR/Fetch
- Cerca pattern nelle richieste periodiche
- Analizza i payload delle risposte

### 6. Headers Comuni da Provare

```bash
# User-Agent comuni
curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://ospedale.example.com/api/status"

# Referrer
curl -H "Referer: https://ospedale.example.com/" \
  "https://ospedale.example.com/api/data"

# Origin
curl -H "Origin: https://ospedale.example.com" \
  "https://ospedale.example.com/api/ps"
```

### 7. Rate Limiting e Caching

```bash
# Verifica la presenza di rate limiting
for i in {1..10}; do
  curl -I "https://ospedale.example.com/api/status"
  sleep 1
done

# Verifica le policy di cache
curl -I "https://ospedale.example.com/api/status"
```

Se non vengono trovate API utilizzabili, procedere con l'implementazione dello scraper HTML seguendo le best practices descritte sopra.
