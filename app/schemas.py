from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict


class HospitalBase(BaseModel):
    name: str
    city: str
    province: str
    address: str
    latitude: float
    longitude: float


class HospitalCreate(HospitalBase):
    pass


class Hospital(HospitalBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class HospitalStatusBase(BaseModel):
    hospital_id: int
    available_beds: int
    waiting_time: int
    color_code: str
    external_last_update: Optional[datetime] = None


class HospitalStatusCreate(HospitalStatusBase):
    pass


class HospitalStatus(HospitalStatusBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)


class HospitalHistoryBase(BaseModel):
    hospital_id: int
    available_beds: int
    waiting_time: int
    color_code: str
    external_last_update: Optional[datetime] = None


class HospitalHistory(HospitalHistoryBase):
    id: int
    scraped_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HospitalWithStatus(Hospital):
    current_status: Optional[HospitalStatus] = None
    
    class Config:
        from_attributes = True


class HospitalStats(BaseModel):
    total_hospitals: int
    overcrowded_hospitals: int
    average_waiting_time: float
    hospitals_by_color: Dict[str, int] 