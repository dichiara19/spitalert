from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class HospitalStatusBase(BaseModel):
    available_beds: int = Field(ge=0)
    waiting_time: int = Field(ge=0)  # in minuti
    color_code: str
    external_last_update: Optional[datetime] = None


class HospitalStatusCreate(HospitalStatusBase):
    hospital_id: int


class HospitalStatus(HospitalStatusBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hospital_id: int
    last_updated: datetime


class HospitalHistoryBase(BaseModel):
    available_beds: int = Field(ge=0)
    waiting_time: int = Field(ge=0)
    color_code: str
    external_last_update: Optional[datetime] = None


class HospitalHistoryCreate(HospitalHistoryBase):
    hospital_id: int


class HospitalHistory(HospitalHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hospital_id: int
    scraped_at: datetime


class HospitalWithStatus(Hospital):
    current_status: Optional[HospitalStatus] = None
    
    class Config:
        from_attributes = True


class HospitalStats(BaseModel):
    total_hospitals: int
    overcrowded_hospitals: int
    average_waiting_time: float
    hospitals_by_color: dict[str, int] 