# Usa una versione specifica di Python
FROM python:3.11-slim

# Imposta le variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Aggiungi Poetry al PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Installa le dipendenze di sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installa Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di configurazione
COPY pyproject.toml poetry.lock ./

# Installa le dipendenze
RUN poetry install --no-dev --no-interaction --no-ansi

# Copia il codice dell'applicazione
COPY . .

# Esponi la porta
EXPOSE 8000

# Script di avvio
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

# Comando di avvio
CMD ["/start.sh"] 