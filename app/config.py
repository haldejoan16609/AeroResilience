"""
AeroResilience — Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "AeroResilience"
    APP_DESCRIPTION: str = "AI for Clean Air & Climate Resilience"
    APP_VERSION: str = "1.0.0"

    # Database: paste Supabase URI into DATABASE_URL, or leave empty for local SQLite
    DATABASE_URL: str = os.getenv("DATABASE_URL", "") or "sqlite+aiosqlite:///./aeroresilience.db"
    USE_SUPABASE: bool = "asyncpg" in (os.getenv("DATABASE_URL", "") or "")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192").strip('"').strip("'")

    # Indian cities with coordinates for demo
    CITIES = [
        {"name": "Delhi",      "lat": 28.6139, "lon": 77.2090, "base_aqi": 220, "volatility": 80},
        {"name": "Mumbai",     "lat": 19.0760, "lon": 72.8777, "base_aqi": 120, "volatility": 40},
        {"name": "Bangalore",  "lat": 12.9716, "lon": 77.5946, "base_aqi": 75,  "volatility": 25},
        {"name": "Chennai",    "lat": 13.0827, "lon": 80.2707, "base_aqi": 90,  "volatility": 30},
        {"name": "Kolkata",    "lat": 22.5726, "lon": 88.3639, "base_aqi": 160, "volatility": 50},
        {"name": "Hyderabad",  "lat": 17.3850, "lon": 78.4867, "base_aqi": 95,  "volatility": 30},
        {"name": "Pune",       "lat": 18.5204, "lon": 73.8567, "base_aqi": 85,  "volatility": 25},
        {"name": "Ahmedabad",  "lat": 23.0225, "lon": 72.5714, "base_aqi": 130, "volatility": 45},
        {"name": "Jaipur",     "lat": 26.9124, "lon": 75.7873, "base_aqi": 140, "volatility": 50},
        {"name": "Lucknow",    "lat": 26.8467, "lon": 80.9462, "base_aqi": 180, "volatility": 60},
    ]

    POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]


settings = Settings()
