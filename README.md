# SpitAlert Backend

Sistema di monitoraggio in tempo reale dei tempi di attesa nei pronto soccorso.

## Caratteristiche

- Scraping automatico dei dati dai siti web degli ospedali
- API REST per accedere ai dati
- Sistema modulare per aggiungere facilmente nuovi ospedali
- Aggiornamento automatico ogni 15 minuti
- Storico dei tempi di attesa

## Tecnologie

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- BeautifulSoup4
- APScheduler

## Installazione

1. Clona il repository:
```bash
git clone https://github.com/tuousername/spitalert.git
cd spitalert
```

2. Crea un ambiente virtuale e installare le dipendenze:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. Configura le variabili d'ambiente:
```bash
cp .env.example .env
# Modifica .env con i tuoi parametri
```

4. Avvia l'applicazione:
```bash
uvicorn main:app --reload
```

L'API sarà disponibile su `http://localhost:8000`
La documentazione Swagger su `http://localhost:8000/docs`

## Struttura del Progetto

```
backend/
│── main.py               # Punto di ingresso API
│── scraper.py           # Gestione scraping
│── database.py          # Configurazione database
│── scheduler.py         # Task automatici
│── requirements.txt     # Dipendenze
│── .env                # Configurazione
└── scrapers/           # Moduli scraper
    ├── __init__.py
    ├── base_scraper.py
    └── villa_sofia_cervello.py
```

## Aggiungere un Nuovo Scraper

1. Crea un nuovo file in `scrapers/` (es: `nuovo_ospedale.py`)
2. Crea una classe che eredita da `BaseScraper`
3. Implementa il metodo `parse()`
4. Aggiungi la classe a `AVAILABLE_SCRAPERS` in `scrapers/__init__.py`

Esempio:
```python
from .base_scraper import BaseScraper

class NuovoOspedaleScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="URL_OSPEDALE",
            name="Nome Ospedale"
        )
    
    async def parse(self, html_content: str):
        # Implementa la logica di parsing
        pass
```

## Lista degli ospedali

Puoi trovare la lista degli ospedali aggiunti [qui](https://github.com/dichiara19/spitalert/projects/1)

## Contribuire al progetto

### Guida Dettagliata per Aggiungere un Nuovo Scraper

#### 1. Prerequisiti
- Python 3.9+
- Conoscenza base di web scraping con BeautifulSoup4
- Git per il versionamento del codice

#### 2. Struttura di un Nuovo Scraper

Ogni scraper deve:
1. Ereditare da `BaseScraper`
2. Implementare il metodo astratto `parse()`
3. Restituire i dati nel formato corretto

##### Esempio di Template Base
```python
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class NuovoOspedaleScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            url="URL_DEL_PRONTO_SOCCORSO",
            name="Nome Ospedale"
        )
    
    async def parse(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content, 'html.parser')
        hospitals_data = []
        
        # Implementa qui la logica di parsing
        data = {
            'name': "Nome Ospedale",
            'department': "Pronto Soccorso",
            'total_patients': 0,  # Numero totale pazienti
            'waiting_patients': 0,  # Pazienti in attesa
            'red_code': 0,     # Codici rossi
            'orange_code': 0,  # Codici arancioni
            'azure_code': 0,   # Codici azzurri
            'green_code': 0,   # Codici verdi
            'white_code': 0,   # Codici bianchi
            'overcrowding_index': 0.0,  # Indice di sovraffollamento
            'last_updated': datetime.utcnow(),  # Data ultimo aggiornamento
            'url': self.url
        }
        
        hospitals_data.append(data)
        return hospitals_data
```

#### 3. Passi per Contribuire

1. **Fork del Repository**
   ```bash
   git clone https://github.com/dichiara19/spitalert.git
   cd spitalert
   ```

2. **Crea un Nuovo Branch**
   ```bash
   git checkout -b feature/nuovo-ospedale
   ```

3. **Crea il Nuovo Scraper**
   - Crea un nuovo file in `scrapers/` (es: `nuovo_ospedale.py`)
   - Implementa la classe dello scraper seguendo il template
   - Aggiungi i test necessari

4. **Registra lo Scraper**
   - Aggiungi l'import in `scrapers/__init__.py`
   - Aggiungi la classe alla lista `AVAILABLE_SCRAPERS`

5. **Testa lo Scraper**
   ```bash
   python -m pytest tests/test_scrapers.py
   ```

#### 4. Best Practices

1. **Gestione degli Errori**
   - Usa try/except per gestire errori di parsing
   - Logga gli errori in modo appropriato
   - Restituisci una lista vuota in caso di errore

2. **Parsing Robusto**
   - Verifica sempre l'esistenza degli elementi prima di accedervi
   - Usa metodi di fallback per i dati mancanti
   - Valida i dati estratti

3. **Documentazione**
   - Aggiungi docstring alle funzioni
   - Commenta il codice complesso
   - Aggiorna il README se necessario

4. **Performance**
   - Minimizza le operazioni di parsing
   - Usa selettori CSS/class efficienti
   - Implementa cache dove appropriato

#### 5. Invio della Contribuzione

1. **Commit dei Cambiamenti**
   ```bash
   git add .
   git commit -m "Aggiunto scraper per Ospedale X"
   ```

2. **Push e Pull Request**
   ```bash
   git push origin feature/nuovo-ospedale
   ```
   - Crea una Pull Request su GitHub
   - Descrivi dettagliatamente le modifiche
   - Allega screenshot o esempi dei dati estratti

#### 6. Supporto

Per domande o problemi:
- Apri una issue su GitHub
- Partecipa alla discussione nel thread dedicato
- Consulta la documentazione esistente

Ricorda che ogni ospedale può avere una struttura HTML diversa, quindi è importante analizzare attentamente la pagina sorgente prima di implementare il parser.

## Licenza

MIT 