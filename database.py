from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, text, inspect, UniqueConstraint, select
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

    __table_args__ = (
        UniqueConstraint('name', 'department', name='uix_name_department'),
    )

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
                logger.info("Le tabelle esistono già, procedo con la pulizia dei duplicati...")
                # Rimuovi i duplicati mantenendo solo la riga più recente per ogni combinazione name-department
                query = """
                DELETE FROM hospitals a USING (
                    SELECT name, department, MAX(last_updated) as max_date
                    FROM hospitals 
                    GROUP BY name, department
                ) b 
                WHERE a.name = b.name 
                AND a.department = b.department 
                AND a.last_updated < b.max_date;
                """
                await conn.execute(text(query))
                
                # Aggiungi il vincolo UNIQUE se non esiste
                try:
                    await conn.execute(text(
                        "ALTER TABLE hospitals ADD CONSTRAINT uix_name_department UNIQUE (name, department);"
                    ))
                    logger.info("Vincolo unique aggiunto con successo")
                except Exception as e:
                    if "already exists" not in str(e):
                        raise
                    logger.info("Il vincolo unique esiste già")
        
        logger.info("Inizializzazione database completata")
        return True
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
        if os.getenv("ENVIRONMENT") == "production":
            raise
        return False

async def get_or_create_hospital(session: AsyncSession, name: str, department: str, **kwargs) -> Hospital:
    """
    Recupera un ospedale esistente o ne crea uno nuovo se non esiste.
    Gestisce in modo sicuro i duplicati.
    """
    try:
        # Cerca l'ospedale esistente
        query = select(Hospital).filter(
            Hospital.name == name,
            Hospital.department == department
        )
        result = await session.execute(query)
        hospital = result.scalar_one_or_none()
        
        if hospital:
            # Aggiorna i campi esistenti
            for key, value in kwargs.items():
                if hasattr(hospital, key):
                    setattr(hospital, key, value)
        else:
            # Crea un nuovo ospedale
            hospital = Hospital(
                name=name,
                department=department,
                **kwargs
            )
            session.add(hospital)
        
        await session.commit()
        return hospital
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Errore nell'operazione su ospedale {name} - {department}: {str(e)}")
        raise 