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

## Deploy

Il progetto è configurato per il deploy su Render. Vedere `render.yaml` per i dettagli della configurazione.

## Licenza

MIT 