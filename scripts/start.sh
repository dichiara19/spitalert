#!/bin/bash

# Attendi che il database sia pronto (se necessario)
echo "Attesa del database..."
python -c "
import asyncio
from app.database import init_db

async def wait_for_db():
    max_retries = 30
    retry_interval = 2

    for i in range(max_retries):
        try:
            await init_db()
            print('Database connesso!')
            return
        except Exception as e:
            print(f'Tentativo {i+1}/{max_retries}: Database non pronto ({str(e)})')
            if i < max_retries - 1:
                await asyncio.sleep(retry_interval)
    
    raise Exception('Impossibile connettersi al database')

asyncio.run(wait_for_db())
"

# Avvia l'applicazione con Gunicorn
echo "Avvio dell'applicazione..."
exec gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info 