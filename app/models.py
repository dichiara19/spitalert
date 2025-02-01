from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    province = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    department = Column(String, nullable=False)
    
    # Relazioni
    current_status = relationship("HospitalStatus", back_populates="hospital", uselist=False)
    history = relationship("HospitalHistory", back_populates="hospital")

class HospitalStatus(Base):
    __tablename__ = "hospital_status"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    available_beds = Column(Integer, nullable=False)
    waiting_time = Column(Integer, nullable=False)  # in minuti
    color_code = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    external_last_update = Column(DateTime, nullable=True)
    
    # Relazione
    hospital = relationship("Hospital", back_populates="current_status")

class HospitalHistory(Base):
    __tablename__ = "hospital_history"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    available_beds = Column(Integer, nullable=False)
    waiting_time = Column(Integer, nullable=False)  # in minuti
    color_code = Column(String, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    external_last_update = Column(DateTime, nullable=True)
    
    # Relazione
    hospital = relationship("Hospital", back_populates="history") 