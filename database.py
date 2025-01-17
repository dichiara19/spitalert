from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carica variabili d'ambiente
load_dotenv()

# Configurazione del database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL non trovato nelle variabili d'ambiente!")
    DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Database di fallback per development
    logger.info(f"Usando database di fallback: {DATABASE_URL}")

try:
    # Configura l'engine in base al tipo di database
    if DATABASE_URL.startswith('sqlite'):
        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DEBUG", "False").lower() == "true"
        )
    else:
        # PostgreSQL supporta il connection pooling
        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DEBUG", "False").lower() == "true",
            pool_size=5,
            max_overflow=10
        )
    logger.info("Connessione al database configurata con successo")
except Exception as e:
    logger.error(f"Errore nella creazione dell'engine del database: {str(e)}")
    raise

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Hospital(Base):
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    department = Column(String)  # es. "Pronto Soccorso Adulti", "Pronto Soccorso Pediatrico"
    total_patients = Column(Integer, default=0)
    waiting_patients = Column(Integer, default=0)
    
    # Codici colore
    red_code = Column(Integer, default=0)
    orange_code = Column(Integer, default=0)
    azure_code = Column(Integer, default=0)
    green_code = Column(Integer, default=0)
    white_code = Column(Integer, default=0)
    
    overcrowding_index = Column(Float)  # Indice di sovraffollamento in percentuale
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    url = Column(String)  # URL del pronto soccorso da monitorare

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database inizializzato con successo")
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
        raise 