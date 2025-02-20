import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_waiting_time(time_str: str) -> Optional[int]:
    """
    Converte una stringa di tempo di attesa in minuti.
    Gestisce vari formati come:
    - "2 ore e 30 minuti"
    - "45 min"
    - "1h 30m"
    - "2:30"
    - "150 minuti"
    
    Args:
        time_str: Stringa contenente il tempo di attesa
        
    Returns:
        Optional[int]: Tempo di attesa in minuti o None se il parsing fallisce
    """
    if not time_str or not isinstance(time_str, str):
        return None
        
    # Pulisce la stringa
    time_str = time_str.lower().strip()
    
    try:
        # Pattern per formati comuni
        patterns = [
            # 2 ore e 30 minuti
            (r'(\d+)\s*or[ae]\s*(?:e\s*)?(\d+)?\s*min(?:uti)?', lambda h, m: int(h) * 60 + (int(m) if m else 0)),
            # 45 min
            (r'(\d+)\s*min(?:uti)?', lambda m, _: int(m)),
            # 1h 30m
            (r'(\d+)\s*h\s*(?:(\d+)\s*m)?', lambda h, m: int(h) * 60 + (int(m) if m else 0)),
            # 2:30
            (r'(\d+):(\d+)', lambda h, m: int(h) * 60 + int(m)),
            # 150 minuti
            (r'(\d+)', lambda m, _: int(m))
        ]
        
        for pattern, converter in patterns:
            match = re.match(pattern, time_str)
            if match:
                groups = match.groups()
                # Se abbiamo un solo gruppo, il secondo sarà None
                result = converter(groups[0], groups[1] if len(groups) > 1 else None)
                logger.debug(f"Convertito '{time_str}' in {result} minuti usando pattern {pattern}")
                return result
                
        logger.warning(f"Nessun pattern valido trovato per '{time_str}'")
        return None
        
    except Exception as e:
        logger.error(f"Errore nel parsing del tempo di attesa '{time_str}': {str(e)}")
        return None 