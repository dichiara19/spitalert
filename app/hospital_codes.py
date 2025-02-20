from enum import Enum
from typing import Dict, Optional

class HospitalCode(str, Enum):
    """
    Enum per i codici degli ospedali.
    Ogni ospedale deve avere un codice univoco qui.
    """
    PO_CERVELLO = "po_cervello"
    PO_VILLA_SOFIA = "po_villa_sofia"
    PO_POLICLINICO = "po_policlinico"
    PO_SCIACCA = "po_sciacca"
    PO_RIBERA = "po_ribera"
    PO_LICATA = "po_licata"
    PO_CANICATTI = "po_canicatti"
    PO_RODOLICO = "po_rodolico"
    PO_SAN_MARCO = "po_san_marco"
    AO_PAPARDO = "ao_papardo"

class HospitalRegistry:
    """
    Registry centrale per la gestione del mapping tra ID database e codici ospedale.
    """
    _id_to_code: Dict[int, HospitalCode] = {}
    _code_to_id: Dict[HospitalCode, int] = {}
    
    @classmethod
    def register(cls, hospital_id: int, code: HospitalCode) -> None:
        """
        Registra un mapping tra ID database e codice ospedale.
        
        Args:
            hospital_id: ID dell'ospedale nel database
            code: Codice enum dell'ospedale
        """
        cls._id_to_code[hospital_id] = code
        cls._code_to_id[code] = hospital_id
    
    @classmethod
    def get_code(cls, hospital_id: int) -> Optional[HospitalCode]:
        """
        Ottiene il codice ospedale dato l'ID database.
        
        Args:
            hospital_id: ID dell'ospedale nel database
            
        Returns:
            Optional[HospitalCode]: Codice dell'ospedale se registrato
        """
        return cls._id_to_code.get(hospital_id)
    
    @classmethod
    def get_id(cls, code: HospitalCode) -> Optional[int]:
        """
        Ottiene l'ID database dato il codice ospedale.
        
        Args:
            code: Codice enum dell'ospedale
            
        Returns:
            Optional[int]: ID dell'ospedale se registrato
        """
        return cls._code_to_id.get(code)
    
    @classmethod
    def clear(cls) -> None:
        """
        Pulisce tutti i mapping registrati.
        Utile principalmente per i test.
        """
        cls._id_to_code.clear()
        cls._code_to_id.clear() 