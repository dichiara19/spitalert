import redis.asyncio as redis
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def get_redis_client():
    """Crea una connessione Redis usando l'URL di configurazione"""
    try:
        if settings.REDIS_URL:
            return redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                retry_on_timeout=True
            )
        else:
            # Fallback alle configurazioni separate
            return redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                decode_responses=True
            )
    except Exception as e:
        logger.error(f"Errore nella connessione Redis: {str(e)}")
        return None

async def check_rate_limit():
    """
    Verifica se è trascorso almeno 15 minuti dall'ultima richiesta POST
    (applicato solo in ambiente 'production').
    """
    if settings.ENVIRONMENT.lower() != "production":
        return
        
    try:
        redis_client = await get_redis_client()
        if not redis_client:
            logger.warning("Redis non disponibile, rate limiting disabilitato")
            return

        rate_limit_key = "scrape_last_run"
        last_run = await redis_client.get(rate_limit_key)
        now = datetime.utcnow()

        if last_run:
            try:
                last_run_time = datetime.fromisoformat(last_run)
                if now - last_run_time < timedelta(minutes=15):
                    remaining = timedelta(minutes=15) - (now - last_run_time)
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            f"Limite di richieste superato. "
                            f"Riprovare dopo {int(remaining.total_seconds() // 60)} minuti e "
                            f"{int(remaining.total_seconds() % 60)} secondi."
                        )
                    )
            except ValueError:
                logger.error("Errore nel parsing del timestamp Redis")
                await redis_client.delete(rate_limit_key)
        
        await redis_client.set(rate_limit_key, now.isoformat())
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Errore nel rate limiting: {str(e)}")
        # Non blocchiamo l'applicazione se Redis non funziona
        return 