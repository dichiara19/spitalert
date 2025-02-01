import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from ..config import get_settings

settings = get_settings()

# Configurazione base del logger
class CustomFormatter(logging.Formatter):
    """
    Formatter personalizzato per i log con colori per il terminale
    e formato esteso per i file
    """
    
    # Colori per il terminale
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    # Format per il terminale (colorato)
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Format per il file (dettagliato)
    file_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
        "[%(filename)s:%(lineno)d] - %(funcName)s"
    )

    FORMATS = {
        logging.DEBUG: grey + console_format + reset,
        logging.INFO: blue + console_format + reset,
        logging.WARNING: yellow + console_format + reset,
        logging.ERROR: red + console_format + reset,
        logging.CRITICAL: bold_red + console_format + reset
    }

    def format(self, record):
        # Usa il format colorato per la console
        if getattr(record, 'is_console', False):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
        else:
            # Usa il format dettagliato per il file
            formatter = logging.Formatter(self.file_format)
        
        return formatter.format(record)

def setup_logger(name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """
    Configura un logger con output su file e console.
    
    Args:
        name: Nome del logger
        log_file: Percorso del file di log (opzionale)
        
    Returns:
        logging.Logger: Logger configurato
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Evita duplicati dei log
    if logger.handlers:
        return logger

    # Handler per la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    # Aggiungi un attributo per identificare l'handler della console
    setattr(console_handler, 'is_console', True)
    logger.addHandler(console_handler)

    # Handler per il file se specificato
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(CustomFormatter())
        logger.addHandler(file_handler)

    return logger

# Logger principale dell'applicazione
app_logger = setup_logger(
    'spitalert',
    Path(settings.LOG_DIR) / 'app.log' if settings.LOG_DIR else None
)

# Logger specifico per gli scraper
scraper_logger = setup_logger(
    'spitalert.scraper',
    Path(settings.LOG_DIR) / 'scraper.log' if settings.LOG_DIR else None
)

class LoggerMixin:
    """
    Mixin per aggiungere funzionalità di logging alle classi.
    """
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f"spitalert.{self.__class__.__name__}")
        return self._logger 