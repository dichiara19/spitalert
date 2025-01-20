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

- Agrigento
  - P.O. "S. Giovanni Di Dio" di Agrigento
  - P.O. "F.lli Parlapiano" di Ribera
  - P.O. "Ospedali Civili Riuniti" di Sciacca
  - P.O. "San Giovanni Paolo II" di Sciacca
- Caltanissetta
  - P.O. "S. Elia" di Caltanissetta
  - P.O. "Vittorio Emanuele" di Gela
- Catania
  - P.O. "S. Marta e S. Venera" di Acireale
  - A.O. per l'Emergenza "Cannizzaro"
  - A.O. Universitaria Policlinico di Catania
  - Ospedale Garibaldi Centro
  - Ospedale Garibaldi-Nesima
- Enna
  - P.O. "Umberto I" di Enna
- Messina
  - A.O. "Papardo"
  - A.O. Universitaria Policlinico di Messina
  - P.O. Piemonte
  - P.O. "San Vincenzo" di Taormina
  - P.O. "Barone Romeo" di Patti
- Palermo
  - P.O. "Civico" di Partinico
  - P.O. "S. Cimino" di Termini Imerese
  - P.O. "G. F. Ingrassia"
  - A.O. Villa Sofia-Cervello
  - A.O.R. Villa Sofia-Cervello - P.O. V. Cervello
  - A.R.N.A.S. Ospedale Civico Di Cristina Benfratelli
  - A.O.U. Policlinico "P. Giaccone"
  - P.O. "Dei Bianchi" di Corleone
  - P.O. "Madonna SS. dell'Alto" di Petralia Sottana
- Ragusa
  - P.O. "Civile-OMPA" di Ragusa
  - P.O. "R. Guzzardi" di Vittoria
  - P.O. "Maggiore" di Modica
- Siracusa
  - P.O. "G. Di Maria" di Avola
  - P.O. "Umberto I" di Siracusa
  - P.O. "Generale" di Lentini
- Trapani
  - P.O. "S. Antonio Abate" di Trapani
  - P.O. "Vittorio Emanuele II" di Castelvetrano
  - P.O. "A. Ajello" di Mazara del Vallo
  - P.O. "Paolo Borsellino" di Marsala

## Licenza

MIT 