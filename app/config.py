from pydantic_settings import BaseSettings
from typing import Any, List, Optional
from functools import lru_cache
import json

class Settings(BaseSettings):
    """
    Configurazioni centralizzate dell'applicazione.
    Tutte le configurazioni scalabili sono gestite tramite variabili d'ambiente.
    """
    
    # Informazioni di base
    PROJECT_NAME: str = "SpitAlert API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Ambiente
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "spitalert"
    # Pool di connessioni
    POSTGRES_MIN_POOL_SIZE: int = 1
    POSTGRES_MAX_POOL_SIZE: int = 10
    POSTGRES_POOL_RECYCLE: int = 3600  # 1 ora
    POSTGRES_POOL_TIMEOUT: int = 30  # secondi
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_TIMEOUT: int = 10  # secondi
    REDIS_POOL_SIZE: int = 10
    REDIS_RETRY_ON_TIMEOUT: bool = True
    
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else "@"
        scheme = "rediss" if self.REDIS_SSL else "redis"
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ORIGINS_REGEX: str = ""
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-Total-Count",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]
    CORS_EXPOSE_HEADERS: List[str] = ["X-Total-Count"]
    CORS_MAX_AGE: int = 3600  # secondi
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @property
    def cors_origins(self) -> List[str]:
        """
        Gestisce la lista dei domini consentiti per CORS.
        In produzione, usa i domini specificati in CORS_ORIGINS.
        In sviluppo, consente localhost.
        """
        if self.ENVIRONMENT == "production":
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS deve essere configurato in produzione")
            return self.CORS_ORIGINS
        return ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_MAX_BYTES: int = 10_485_760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_STDOUT: bool = True
    
    # HTTP Client
    HTTP_TIMEOUT: float = 30.0
    HTTP_MAX_RETRIES: int = 3
    HTTP_RETRY_BACKOFF_FACTOR: float = 0.5
    HTTP_POOL_CONNECTIONS: int = 100
    HTTP_POOL_MAXSIZE: int = 10
    HTTP_MAX_KEEPALIVE: int = 5
    HTTP_USER_AGENT: str = "SpitAlert/1.0"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # richieste
    RATE_LIMIT_WINDOW: int = 60  # secondi
    
    # Cache
    CACHE_TTL: int = 300  # secondi
    CACHE_ENABLED: bool = True
    
    # Scraping
    SCRAPE_INTERVAL: int = 300  # secondi
    SCRAPE_TIMEOUT: float = 60.0
    SCRAPE_MAX_RETRIES: int = 3
    SCRAPE_CONCURRENT_TASKS: int = 5
    
    # Security
    SECURITY_ALLOWED_HOSTS: List[str] = ["*"]
    SECURITY_SSL_REDIRECT: bool = False
    SECURITY_HSTS_SECONDS: int = 31536000  # 1 anno
    SECURITY_FRAME_DENY: bool = True
    SECURITY_CONTENT_TYPE_NOSNIFF: bool = True
    SECURITY_BROWSER_XSS_FILTER: bool = True
    SECURITY_CSP_POLICY: str = "default-src 'self'"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
        # Permette la conversione di stringhe JSON in liste
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name.endswith(("_LIST", "_ARRAY", "_ORIGINS", "_METHODS", "_HEADERS")):
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return raw_val.split(",")
            return raw_val


@lru_cache()
def get_settings() -> Settings:
    """
    Restituisce un'istanza singleton delle impostazioni.
    """
    return Settings() 