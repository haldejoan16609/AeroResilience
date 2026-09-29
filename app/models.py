"""
AeroResilience — Database Models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class CommunityAction(Base):
    __tablename__ = "community_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    impact_value = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    contributor = Column(String(100), default="Anonymous")
    created_at = Column(DateTime, server_default=func.now())


class AQIReading(Base):
    __tablename__ = "aqi_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False)
    aqi = Column(Integer, nullable=False)
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    recorded_at = Column(DateTime, server_default=func.now())
