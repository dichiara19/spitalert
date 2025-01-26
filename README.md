# SpitAlert Backend

[![Website](https://img.shields.io/badge/Website-spitalert.com-blue)](https://spitalert.com)
[![API](https://img.shields.io/badge/API-api.spitalert.com-green)](https://api.spitalert.com)
[![Visitors](https://visitor-badge.laobi.icu/badge?page_id=dichiara19.spitalert)](https://github.com/dichiara19/spitalert)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)

Real-time monitoring system for waiting times in Sicilian emergency rooms.

## Features

- Automatic scraping of data from hospital websites
- REST API to access data
- Modular system to easily add new hospitals
- Automatic update every 15 minutes
- Wait time history

## Technologies

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- BeautifulSoup4
- APScheduler

## Installation

1. Clone the repository:
```bash
git clone https://github.com/dichiara19/spitalert.git
cd spitalert
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate # Linux/Mac
# or
.\venv\Scripts\activate # Windows
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your parameters
```

4. Start the application:
```bash
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`
Swagger documentation at `http://localhost:8000/docs`

## Project Structure

```
backend/
│── main.py # API entry point
│── scraper.py # Scraping management
│── database.py # Database configuration
│── scheduler.py # Automatic tasks
│── requirements.txt # Dependencies
│── .env # Configuration
└── scrapers/ # Scraper modules
├── __init__.py
├── base_scraper.py
└── villa_sofia_cervello.py
```

## Adding a New Scraper

1. Create a new file in `scrapers/` (eg: `nuovo_ospedale.py`)
2. Create a class that inherits from `BaseScraper`
3. Implement the `parse()` method
4. Add the class to `AVAILABLE_SCRAPERS` in `scrapers/__init__.py`

Example:
```python
from .base_scraper import BaseScraper

class NuovoOspedaleScraper(BaseScraper):
def __init__(self):
super().__init__(
url="URL_HOSPITAL",
name="Nome Ospedale"
)

async def parse(self, html_content: str):
# Implement parsing logic
pass
```

## List of hospitals

You can find the list of added hospitals [here](https://github.com/dichiara19/spitalert/projects/1)

## Contribute to the project

### Detailed Guide to Add a New Scraper

#### 1. Prerequisites
- Python 3.9+
- Basic knowledge of web scraping with BeautifulSoup4
- Git for versioning the code

#### 2. Structure of a New Scraper

Each scraper must:
1. Inherit from `BaseScraper`
2. Implement the abstract method `parse()`
3. Return the data in the correct format

##### Base Template Example
```python
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class NuovoOspedaleScraper(BaseScraper):
def __init__(self):
super().__init__(
url="URL_DEL_EMERGENCY_SOCCORSO",
name="Name of Hospital"
)

async def parse(self, html_content: str) -> List[Dict[str, Any]]:
soup = BeautifulSoup(html_content, 'html.parser')
hospitals_data = []

# Implement parsing logic here
data = {
'name': "Name of Hospital",
'department': "Emergency Room",
'total_patients': 0, # Total number of patients
'waiting_patients': 0, # Patients waiting
'red_code': 0, # Red codes
'orange_code': 0, # Codes orange
'azure_code': 0, # Blue codes
'green_code': 0, # Green codes
'white_code': 0, # White codes
'overcrowding_index': 0.0, # Overcrowding index
'last_updated': datetime.utcnow(), # Last update date
'url': self.url
}

hospitals_data.append(data)
return hospitals_data
```

#### 3. Contributing Steps

1. **Fork the Repository**
```bash
git clone https://github.com/dichiara19/spitalert.git
cd spitalert
```

2. **Create a new branch**
```bash
git checkout -b feature/new-hospital
```

3. **Create a new scraper**
- Create a new file in `scrapers/` (eg: `new_hospital.py`)
- Implement the scraper class following the template
- Add the necessary tests

4. **Register the scraper**
- Add the import in `scrapers/__init__.py`
- Add the class to the `AVAILABLE_SCRAPERS` list

5. **Test the scraper**
```bash
python -m pytest tests/test_scrapers.py
```

#### 4. Best Practices

1. **Error handling**
- Use try/except to handle parsing errors
- Log errors appropriately
- Return an empty list on error

2. **Robust parsing**
- Always check for element existence before accessing
- Use fallback methods for missing data
- Validate extracted data

3. **Documentation**
- Add docstrings to functions
- Comment complex code
- Update README if necessary

4. **Performance**
- Minimize parsing
- Use efficient CSS/class selectors
- Implement cache where appropriate

#### 5. Submitting contributions

1. **Commit changes**
```bash
git add .
git commit -m "Added scraper for Hospital X"
```

2. **Push and create a pull request**
```bash
git push origin feature/new-hospital
```
- Create a Pull Request on GitHub
- Describe your changes in detail
- Attach screenshots or examples of the extracted data

#### 6. Support

For questions or problems:
- Open an issue on GitHub
- Join the discussion in the dedicated thread
- Consult the existing documentation

Remember that each hospital can have a different HTML structure, so it is important to carefully analyze the source page before implementing the parser.

## License

MIT