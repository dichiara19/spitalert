from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, text, inspect
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import sys

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Carica variabili d'ambiente
load_dotenv()

# Configurazione del database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("DATABASE_URL non trovato nelle variabili d'ambiente!")
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("DATABASE_URL è richiesto in produzione!")
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/spitalert"
    logger.info(f"Usando database di fallback: {DATABASE_URL}")

# Configura l'engine in base al tipo di database
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine_config = {
    "echo": os.getenv("DEBUG", "False").lower() == "true",
    "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
    "pool_pre_ping": True,
    "connect_args": {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
}

try:
    engine = create_async_engine(DATABASE_URL, **engine_config)
    logger.info("Engine del database creato con successo")
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
    department = Column(String)
    total_patients = Column(Integer, default=0)
    waiting_patients = Column(Integer, default=0)
    red_code = Column(Integer, default=0)
    orange_code = Column(Integer, default=0)
    azure_code = Column(Integer, default=0)
    green_code = Column(Integer, default=0)
    white_code = Column(Integer, default=0)
    overcrowding_index = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    url = Column(String)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def check_table_exists(conn, table_name):
    """Verifica l'esistenza di una tabella in modo database-agnostico."""
    try:
        # Utilizzo dell'Inspector di SQLAlchemy per un controllo database-agnostico
        def _check():
            inspector = inspect(conn)
            return table_name in inspector.get_table_names()
        
        exists = await conn.run_sync(_check)
        return exists
    except Exception as e:
        logger.error(f"Errore nel controllo della tabella {table_name}: {str(e)}")
        return False

async def init_db():
    try:
        async with engine.begin() as conn:
            # Verifica se le tabelle esistono già
            table_exists = await check_table_exists(conn, "hospitals")
            
            if not table_exists:
                logger.info("Creazione delle tabelle del database...")
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Tabelle create con successo")
            else:
                logger.info("Le tabelle esistono già, skip creazione")
        
        logger.info("Inizializzazione database completata")
        return True
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
        if os.getenv("ENVIRONMENT") == "production":
            raise
        return False 