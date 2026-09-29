"""
AeroResilience — Air Quality Data Service
Fetches real data from OpenWeatherMap API, or generates realistic simulated data.
"""
import math
import random
import httpx
from datetime import datetime, timedelta
from app.config import settings


def _aqi_category(aqi: int) -> dict:
    """Return AQI category info based on Indian AQI standards."""
    if aqi <= 50:
        return {"label": "Good", "color": "#10B981", "emoji": "🟢", "advice": "Air quality is satisfactory. Enjoy outdoor activities!"}
    elif aqi <= 100:
        return {"label": "Satisfactory", "color": "#22D3EE", "emoji": "🔵", "advice": "Air quality is acceptable. Sensitive groups should limit prolonged outdoor exertion."}
    elif aqi <= 200:
        return {"label": "Moderate", "color": "#F59E0B", "emoji": "🟡", "advice": "Breathing discomfort for people with lung/heart disease. Reduce outdoor activity."}
    elif aqi <= 300:
        return {"label": "Poor", "color": "#F97316", "emoji": "🟠", "advice": "Breathing discomfort for most people. Avoid prolonged outdoor exertion."}
    elif aqi <= 400:
        return {"label": "Very Poor", "color": "#EF4444", "emoji": "🔴", "advice": "Respiratory illness on prolonged exposure. Avoid all outdoor activity."}
    else:
        return {"label": "Severe", "color": "#7C3AED", "emoji": "🟣", "advice": "Health emergency. Stay indoors. Use air purifiers."}


def _generate_city_data(city: dict, hours_back: int = 168) -> list:
    """
    Generate realistic hourly AQI data for a city for the past `hours_back` hours.
    Uses sinusoidal patterns for diurnal cycles and adds noise.
    """
    now = datetime.now()
    data = []

    for h in range(hours_back, -1, -1):
        timestamp = now - timedelta(hours=h)
        hour = timestamp.hour

        # Diurnal pattern: AQI peaks at rush hours (8-10 AM and 6-8 PM)
        diurnal = (
            math.sin((hour - 9) * math.pi / 12) * 0.3 +      # morning peak
            math.sin((hour - 19) * math.pi / 12) * 0.2 +      # evening peak
            math.cos((hour - 3) * math.pi / 12) * 0.15         # late night dip
        )

        # Weekly pattern: weekdays worse than weekends
        day_of_week = timestamp.weekday()
        weekly_factor = 1.0 if day_of_week < 5 else 0.8

        # Random noise
        noise = random.gauss(0, city["volatility"] * 0.3)

        # Calculate AQI
        aqi = int(city["base_aqi"] * (1 + diurnal) * weekly_factor + noise)
        aqi = max(10, min(500, aqi))

        # Derive pollutant levels from AQI (approximate relationships)
        pm25 = round(aqi * 0.35 + random.gauss(0, 5), 1)
        pm10 = round(pm25 * 1.8 + random.gauss(0, 10), 1)
        no2 = round(aqi * 0.18 + random.gauss(0, 3), 1)
        so2 = round(aqi * 0.08 + random.gauss(0, 2), 1)
        co = round(aqi * 0.012 + random.gauss(0, 0.3), 2)
        o3 = round(max(5, 80 - aqi * 0.15 + random.gauss(0, 5)), 1)  # Ozone inversely related

        # Weather
        temp = round(28 + 8 * math.sin((hour - 14) * math.pi / 12) + random.gauss(0, 1.5), 1)
        humidity = round(55 + 20 * math.cos((hour - 5) * math.pi / 12) + random.gauss(0, 5), 1)
        wind_speed = round(max(0.5, 3 + 2 * math.sin(hour * math.pi / 6) + random.gauss(0, 1)), 1)

        data.append({
            "city": city["name"],
            "lat": city["lat"],
            "lon": city["lon"],
            "aqi": aqi,
            "category": _aqi_category(aqi),
            "pm25": max(0, pm25),
            "pm10": max(0, pm10),
            "no2": max(0, no2),
            "so2": max(0, so2),
            "co": max(0, co),
            "o3": max(0, o3),
            "temperature": temp,
            "humidity": min(100, max(20, humidity)),
            "wind_speed": wind_speed,
            "timestamp": timestamp.isoformat(),
        })

    return data


async def fetch_real_aqi(lat: float, lon: float) -> dict | None:
    """Fetch real AQI from OpenWeatherMap API (if key configured)."""
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Air Pollution API
            air_resp = await client.get(
                f"http://api.openweathermap.org/data/2.5/air_pollution",
                params={"lat": lat, "lon": lon, "appid": api_key},
            )
            air_data = air_resp.json()

            # Weather API
            weather_resp = await client.get(
                f"https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            )
            weather_data = weather_resp.json()

            if air_resp.status_code == 200 and weather_resp.status_code == 200:
                components = air_data["list"][0]["components"]
                aqi_raw = air_data["list"][0]["main"]["aqi"]
                # OWM AQI is 1-5, convert to Indian AQI scale (approximate)
                aqi_map = {1: 35, 2: 80, 3: 150, 4: 250, 5: 400}
                aqi = aqi_map.get(aqi_raw, 100)

                return {
                    "aqi": aqi,
                    "category": _aqi_category(aqi),
                    "pm25": components.get("pm2_5", 0),
                    "pm10": components.get("pm10", 0),
                    "no2": components.get("no2", 0),
                    "so2": components.get("so2", 0),
                    "co": components.get("co", 0),
                    "o3": components.get("o3", 0),
                    "temperature": weather_data["main"].get("temp", 28),
                    "humidity": weather_data["main"].get("humidity", 55),
                    "wind_speed": weather_data["wind"].get("speed", 3),
                }
    except Exception:
        return None

    return None


async def get_current_data() -> list:
    """Get current AQI data for all cities."""
    results = []
    for city in settings.CITIES:
        # Try real API first
        real_data = await fetch_real_aqi(city["lat"], city["lon"])
        if real_data:
            real_data["city"] = city["name"]
            real_data["lat"] = city["lat"]
            real_data["lon"] = city["lon"]
            real_data["timestamp"] = datetime.now().isoformat()
            real_data["source"] = "live"
            results.append(real_data)
        else:
            # Use simulated data (latest point)
            sim = _generate_city_data(city, hours_back=0)[0]
            sim["source"] = "simulated"
            results.append(sim)
    return results


async def get_historical_data(city_name: str = "Delhi", hours: int = 168) -> list:
    """Get historical AQI data for a specific city."""
    city = next((c for c in settings.CITIES if c["name"] == city_name), settings.CITIES[0])
    return _generate_city_data(city, hours_back=hours)


async def get_all_cities_history(hours: int = 24) -> dict:
    """Get recent history for all cities."""
    return {
        city["name"]: _generate_city_data(city, hours_back=hours)
        for city in settings.CITIES
    }
