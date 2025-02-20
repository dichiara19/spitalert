import redis.asyncio as redis
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.config import get_settings

settings = get_settings()

async def check_rate_limit():
    """
    Verifica se è trascorso almeno 15 minuti dall'ultima richiesta POST
    (applicato solo in ambiente 'production').
    """
    # Applica il rate limiting solo se siamo in modalità production
    if settings.ENVIRONMENT.lower() != "production":
        return

    # Connessione a Redis utilizzando le variabili di ambiente
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    rate_limit_key = "scrape_last_run"
    last_run = await redis_client.get(rate_limit_key)
    now = datetime.utcnow()

    if last_run:
        try:
            last_run_time = datetime.fromisoformat(last_run)
        except Exception:
            # In caso di problemi nel parsing, forza il bypass della limitazione
            last_run_time = now - timedelta(minutes=16)
        
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
    
    # Aggiorna o imposta la chiave con il timestamp attuale
    await redis_client.set(rate_limit_key, now.isoformat()) 