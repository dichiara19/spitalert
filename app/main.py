from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import api
from .database import init_db
from .scripts.init_hospitals import init_hospitals
from .config import get_settings
from .scheduler import setup_scheduler
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,  # Disabilita Swagger in produzione
    redoc_url="/redoc" if settings.DEBUG else None,  # Disabilita ReDoc in produzione
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
    max_age=settings.CORS_MAX_AGE,
)

# Log della configurazione CORS all'avvio
logger.info(
    "Configurazione CORS: domini consentiti %s",
    settings.cors_origins
)

# Inizializzazione del database all'avvio
@app.on_event("startup")
async def startup_event():
    """
    Evento di startup dell'applicazione.
    Inizializza il database, gli ospedali e lo scheduler.
    """
    logger.info("Avvio dell'applicazione...")
    
    # Inizializza il database
    logger.info("Inizializzazione database...")
    await init_db()
    
    # Inizializza gli ospedali
    logger.info("Inizializzazione ospedali...")
    try:
        await init_hospitals()
        logger.info("Inizializzazione ospedali completata con successo")
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione degli ospedali: {str(e)}", exc_info=True)
        # Non solleviamo l'eccezione per permettere all'app di partire comunque
        # Gli admin possono sempre eseguire l'inizializzazione manualmente con il CLI
    
    # Avvia lo scheduler
    logger.info("Avvio dello scheduler...")
    setup_scheduler()

# Pulizia alla chiusura
@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento di shutdown dell'applicazione.
    Esegue le operazioni di pulizia necessarie.
    """
    logger.info("Arresto dell'applicazione...")
    
    # Qui possiamo aggiungere altre operazioni di pulizia se necessario

# Inclusione dei router
app.include_router(api.router, prefix=settings.API_V1_STR)

# Root endpoint per health check
@app.get("/")
async def health_check():
    """
    Endpoint di health check.
    """
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    } 