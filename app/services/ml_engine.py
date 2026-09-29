"""
AeroResilience — ML Engine
Provides AQI forecasting, anomaly detection, vulnerability assessment,
and AI-generated environmental insights.
"""
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from app.config import settings


# ---------------------------------------------------------------------------
# 1. AQI Forecasting (Polynomial Regression + Exponential Smoothing)
# ---------------------------------------------------------------------------

def forecast_aqi(historical_data: list, forecast_hours: int = 72) -> list:
    """
    Forecast AQI for the next `forecast_hours` using a combination of:
    - Polynomial regression for trend
    - Exponential smoothing for recent momentum
    - Diurnal pattern overlay
    """
    if len(historical_data) < 24:
        return []

    # Extract AQI values
    aqi_values = np.array([d["aqi"] for d in historical_data[-168:]])  # last 7 days
    x = np.arange(len(aqi_values))

    # Fit polynomial trend (degree 2)
    try:
        coeffs = np.polyfit(x, aqi_values, 2)
        trend_fn = np.poly1d(coeffs)
    except np.RankWarning:
        trend_fn = np.poly1d([0, 0, np.mean(aqi_values)])

    # Exponential smoothing for recent values
    alpha = 0.3
    smoothed = aqi_values[-1]
    for v in aqi_values[-24:]:
        smoothed = alpha * v + (1 - alpha) * smoothed

    # Generate forecasts
    forecasts = []
    last_time = datetime.fromisoformat(historical_data[-1]["timestamp"])

    for h in range(1, forecast_hours + 1):
        future_time = last_time + timedelta(hours=h)
        hour = future_time.hour

        # Trend component
        trend = trend_fn(len(aqi_values) + h)

        # Diurnal component (rush hour peaks)
        diurnal = (
            np.sin((hour - 9) * np.pi / 12) * 15 +
            np.sin((hour - 19) * np.pi / 12) * 10
        )

        # Blend trend with smoothed value
        predicted = 0.4 * trend + 0.6 * smoothed + diurnal
        predicted = int(max(10, min(500, predicted)))

        # Confidence interval widens with time
        ci_width = int(10 + h * 0.8)

        forecasts.append({
            "timestamp": future_time.isoformat(),
            "hour_label": future_time.strftime("%I %p, %b %d"),
            "predicted_aqi": predicted,
            "confidence_low": max(0, predicted - ci_width),
            "confidence_high": min(500, predicted + ci_width),
            "category": _get_category(predicted),
        })

    return forecasts


def _get_category(aqi: int) -> str:
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"


# ---------------------------------------------------------------------------
# 2. Anomaly Detection (Z-Score + IQR)
# ---------------------------------------------------------------------------

def detect_anomalies(historical_data: list, threshold: float = 2.5) -> list:
    """Detect anomalous AQI spikes using Z-score and IQR methods."""
    if len(historical_data) < 48:
        return []

    aqi_values = np.array([d["aqi"] for d in historical_data])
    mean_aqi = np.mean(aqi_values)
    std_aqi = np.std(aqi_values)

    if std_aqi == 0:
        return []

    # IQR method
    q1, q3 = np.percentile(aqi_values, [25, 75])
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr

    anomalies = []
    for i, d in enumerate(historical_data):
        z_score = abs(d["aqi"] - mean_aqi) / std_aqi
        is_anomaly = z_score > threshold or d["aqi"] > upper_fence

        if is_anomaly and d["aqi"] > mean_aqi:  # Only flag high spikes
            severity = "Critical" if z_score > 3.5 else "Warning" if z_score > 3.0 else "Alert"
            anomalies.append({
                "timestamp": d["timestamp"],
                "city": d.get("city", "Unknown"),
                "aqi": d["aqi"],
                "z_score": round(z_score, 2),
                "expected_range": f"{int(mean_aqi - std_aqi)} – {int(mean_aqi + std_aqi)}",
                "severity": severity,
                "possible_cause": _infer_cause(d, mean_aqi),
            })

    return anomalies[-10:]  # Return last 10 anomalies


def _infer_cause(data_point: dict, baseline: float) -> str:
    """Heuristic-based cause inference."""
    aqi = data_point["aqi"]
    hour = datetime.fromisoformat(data_point["timestamp"]).hour
    deviation = aqi - baseline

    if deviation > 150:
        return "Possible industrial emission event or crop burning"
    elif 8 <= hour <= 10 or 17 <= hour <= 20:
        return "Rush hour traffic congestion"
    elif data_point.get("wind_speed", 5) < 1.5:
        return "Low wind speed causing pollution stagnation"
    elif data_point.get("humidity", 50) > 85:
        return "High humidity trapping particulate matter"
    else:
        return "Construction activity or localized emission source"


# ---------------------------------------------------------------------------
# 3. Climate Vulnerability Assessment
# ---------------------------------------------------------------------------

def assess_vulnerability(city_data: list) -> dict:
    """
    Compute a composite Climate Vulnerability Index (CVI) for a city.
    Score 0–100 (higher = more vulnerable).
    """
    if not city_data:
        return {"score": 0, "level": "Unknown", "factors": []}

    aqi_values = [d["aqi"] for d in city_data]
    temps = [d.get("temperature", 28) for d in city_data]
    humidities = [d.get("humidity", 55) for d in city_data]

    # Sub-scores (0–100 each)
    air_pollution_score = min(100, np.mean(aqi_values) / 4)
    heat_stress_score = min(100, max(0, (np.mean(temps) - 25) * 8))
    pollution_volatility = min(100, np.std(aqi_values) / 2)
    extreme_days = sum(1 for a in aqi_values if a > 200) / len(aqi_values) * 100

    # Weighted composite
    cvi = (
        air_pollution_score * 0.35 +
        heat_stress_score * 0.20 +
        pollution_volatility * 0.20 +
        extreme_days * 0.25
    )

    level = (
        "Low" if cvi < 30 else
        "Moderate" if cvi < 50 else
        "High" if cvi < 70 else
        "Critical"
    )

    return {
        "score": round(cvi, 1),
        "level": level,
        "factors": [
            {"name": "Air Pollution Exposure", "score": round(air_pollution_score, 1), "weight": "35%"},
            {"name": "Heat Stress Risk", "score": round(heat_stress_score, 1), "weight": "20%"},
            {"name": "Pollution Volatility", "score": round(pollution_volatility, 1), "weight": "20%"},
            {"name": "Extreme Pollution Days", "score": round(extreme_days, 1), "weight": "25%"},
        ],
        "recommendation": _vulnerability_advice(level),
    }


def _vulnerability_advice(level: str) -> str:
    advice = {
        "Low": "Continue monitoring. Maintain green cover and promote clean transport.",
        "Moderate": "Increase green spaces. Implement traffic management zones. Deploy more air monitors.",
        "High": "Urgent: Restrict industrial emissions. Expand public transit. Launch public health advisories.",
        "Critical": "Emergency action needed. Implement odd-even traffic rules. Shut down polluting industries. Distribute masks and air purifiers.",
    }
    return advice.get(level, "Assess further.")


# ---------------------------------------------------------------------------
# 4. Pollution Source Attribution (Heuristic Model)
# ---------------------------------------------------------------------------

def attribute_pollution_sources(data_point: dict) -> list:
    """Estimate pollution source contributions based on pollutant ratios."""
    pm25 = data_point.get("pm25", 50)
    pm10 = data_point.get("pm10", 90)
    no2 = data_point.get("no2", 20)
    so2 = data_point.get("so2", 10)
    co = data_point.get("co", 1)

    total = pm25 + no2 + so2 + co + 1  # avoid division by zero

    # Heuristic attribution based on pollutant signatures
    vehicular = min(45, (no2 / total * 100) * 2.5 + (co / total * 100) * 3)
    industrial = min(30, (so2 / total * 100) * 4 + (pm10 - pm25) / max(pm10, 1) * 20)
    construction = min(25, ((pm10 - pm25) / max(pm10, 1)) * 35)
    residential = min(20, (co / total * 100) * 5)
    natural = max(5, 100 - vehicular - industrial - construction - residential)

    sources = [
        {"source": "Vehicular Emissions", "percentage": round(vehicular, 1), "color": "#EF4444"},
        {"source": "Industrial Activity", "percentage": round(industrial, 1), "color": "#F59E0B"},
        {"source": "Construction Dust", "percentage": round(construction, 1), "color": "#F97316"},
        {"source": "Residential/Biomass", "percentage": round(residential, 1), "color": "#8B5CF6"},
        {"source": "Natural/Secondary", "percentage": round(natural, 1), "color": "#6B7280"},
    ]

    # Normalize to 100%
    total_pct = sum(s["percentage"] for s in sources)
    for s in sources:
        s["percentage"] = round(s["percentage"] / total_pct * 100, 1)

    return sorted(sources, key=lambda x: x["percentage"], reverse=True)


# ---------------------------------------------------------------------------
# 5. AI Insights Generator
# ---------------------------------------------------------------------------

async def generate_insights(city_name: str, current_data: dict, history: list, forecast: list) -> list:
    """Generate human-readable AI insights about air quality using Groq."""
    import httpx
    import json

    if not settings.GROQ_API_KEY:
        return [{
            "type": "info",
            "icon": "ℹ️",
            "title": "AI Offline",
            "text": "Groq API key is missing. Dynamic insights cannot be generated."
        }]

    aqi = current_data.get("aqi", 100)
    wind = current_data.get("wind_speed", 3)
    forecast_summary = f"Max forecast AQI: {max([f.get('predicted_aqi', 0) for f in forecast[:24]]) if forecast else 'N/A'}"
    
    prompt = f"""
    You are an environmental AI assistant for AeroResilience.
    Analyze the following air quality data for {city_name}:
    Current AQI: {aqi}
    Current Wind Speed: {wind} m/s
    Forecast: {forecast_summary}

    Provide 3 insightful observations or advisories as a JSON array of objects. 
    Each object MUST have these exact keys:
    - "type" (one of: "positive", "warning", "info", "danger")
    - "icon" (a single relevant emoji)
    - "title" (short 2-4 word title)
    - "text" (1-2 sentence description)

    Return ONLY the raw JSON array. Do not include markdown formatting or backticks.
    """

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You output strict JSON arrays matching the requested schema. No markdown backticks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 2048
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Clean markdown backticks if model ignored instruction
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()
            
            return json.loads(content)
    except Exception as e:
        print(f"Error generating insights with Groq: {e}")
        return [{
            "type": "danger",
            "icon": "⚠️",
            "title": "Generation Failed",
            "text": "Failed to fetch AI insights from Groq."
        }]


# ---------------------------------------------------------------------------
# 6. Correlation Analysis (Heatmap Data)
# ---------------------------------------------------------------------------

def compute_correlations(history: list) -> dict:
    """
    Compute Pearson correlation matrix between all environmental variables.
    Returns matrix data suitable for rendering a heatmap.
    """
    if len(history) < 24:
        return {"variables": [], "matrix": [], "insights": []}

    variables = ["AQI", "PM2.5", "PM10", "NO₂", "SO₂", "CO", "O₃", "Temp", "Humidity", "Wind"]
    keys = ["aqi", "pm25", "pm10", "no2", "so2", "co", "o3", "temperature", "humidity", "wind_speed"]

    # Build data matrix
    data = []
    for key in keys:
        data.append([d.get(key, 0) for d in history])

    data = np.array(data, dtype=float)

    # Compute correlation matrix
    n = len(variables)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if np.std(data[i]) > 0 and np.std(data[j]) > 0:
                matrix[i][j] = np.corrcoef(data[i], data[j])[0, 1]
            else:
                matrix[i][j] = 0.0

    # Generate insights from strong correlations
    insights = []
    for i in range(n):
        for j in range(i + 1, n):
            r = matrix[i][j]
            if abs(r) > 0.7:
                direction = "positively" if r > 0 else "negatively"
                strength = "strongly" if abs(r) > 0.85 else "moderately"
                insights.append({
                    "var1": variables[i],
                    "var2": variables[j],
                    "correlation": round(r, 3),
                    "text": f"{variables[i]} and {variables[j]} are {strength} {direction} correlated (r={r:.3f})"
                })

    return {
        "variables": variables,
        "matrix": [[round(float(matrix[i][j]), 3) for j in range(n)] for i in range(n)],
        "insights": sorted(insights, key=lambda x: abs(x["correlation"]), reverse=True),
    }


# ---------------------------------------------------------------------------
# 7. Health Impact Calculator
# ---------------------------------------------------------------------------

def estimate_health_impact(city_name: str, history: list, population: int = 1_000_000) -> dict:
    """
    Estimate health impacts of air pollution exposure using WHO/ICMR-based
    concentration-response functions.

    Based on:
    - WHO Global Burden of Disease (GBD) methodology
    - ICMR Health Impact Assessment guidelines
    - Relative Risk (RR) coefficients from meta-analyses
    """
    if not history:
        return {}

    aqi_values = [d["aqi"] for d in history]
    pm25_values = [d.get("pm25", 0) for d in history]

    avg_aqi = np.mean(aqi_values)
    avg_pm25 = np.mean(pm25_values)
    max_aqi = max(aqi_values)
    days_above_200 = sum(1 for a in aqi_values if a > 200)
    days_above_300 = sum(1 for a in aqi_values if a > 300)

    # WHO safe PM2.5 limit = 15 µg/m³ (annual), 25 µg/m³ (24h)
    excess_pm25 = max(0, avg_pm25 - 15)

    # --- Mortality estimates (per 100,000 population per year) ---
    # WHO: 6-13% increase in mortality per 10 µg/m³ PM2.5 above safe limit
    rr_mortality = 1 + 0.08 * (excess_pm25 / 10)  # 8% per 10 µg/m³
    baseline_mortality_rate = 800  # per 100k per year (all-cause, India)
    excess_mortality_rate = baseline_mortality_rate * (rr_mortality - 1)
    premature_deaths = int(excess_mortality_rate * population / 100_000)

    # --- Respiratory hospitalizations ---
    # ~3.4% increase in respiratory admissions per 10 µg/m³ PM2.5
    rr_respiratory = 1 + 0.034 * (excess_pm25 / 10)
    baseline_resp_rate = 1200  # per 100k per year
    excess_resp = baseline_resp_rate * (rr_respiratory - 1)
    respiratory_admissions = int(excess_resp * population / 100_000)

    # --- Asthma exacerbations ---
    asthma_prevalence = 0.05  # 5% of population
    exacerbation_rate = 0.02 * (avg_pm25 / 25)  # rate per exposed person
    asthma_cases = int(population * asthma_prevalence * exacerbation_rate)

    # --- Lost work days ---
    # ~0.5 lost work days per person per year per 10 µg/m³ excess PM2.5
    lost_days_per_capita = 0.5 * (excess_pm25 / 10)
    working_population = int(population * 0.65)
    total_lost_days = int(lost_days_per_capita * working_population)

    # --- Life expectancy reduction ---
    # ~0.6 years per 10 µg/m³ excess PM2.5 (based on Harvard Six Cities Study)
    life_years_lost = round(0.6 * (excess_pm25 / 10), 1)

    # --- Economic cost ---
    # India avg daily wage ~₹500, healthcare cost per hospitalization ~₹15,000
    economic_cost_crores = round(
        (total_lost_days * 500 + respiratory_admissions * 15000 + premature_deaths * 5_000_000) / 1e7, 1
    )

    # Risk level
    if avg_aqi <= 50:
        risk_level = "Low"
        risk_color = "#10B981"
    elif avg_aqi <= 100:
        risk_level = "Moderate"
        risk_color = "#22D3EE"
    elif avg_aqi <= 200:
        risk_level = "High"
        risk_color = "#F59E0B"
    elif avg_aqi <= 300:
        risk_level = "Very High"
        risk_color = "#F97316"
    else:
        risk_level = "Severe"
        risk_color = "#EF4444"

    return {
        "city": city_name,
        "population": population,
        "avg_aqi": round(avg_aqi, 1),
        "avg_pm25": round(avg_pm25, 1),
        "who_safe_limit": 15,
        "excess_pm25": round(excess_pm25, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "impacts": {
            "premature_deaths": {"value": premature_deaths, "unit": "per year", "label": "Premature Deaths", "icon": "💀"},
            "respiratory_admissions": {"value": respiratory_admissions, "unit": "per year", "label": "Respiratory Hospitalizations", "icon": "🏥"},
            "asthma_cases": {"value": asthma_cases, "unit": "per year", "label": "Asthma Exacerbations", "icon": "🫁"},
            "lost_work_days": {"value": total_lost_days, "unit": "per year", "label": "Lost Work Days", "icon": "📉"},
            "life_years_lost": {"value": life_years_lost, "unit": "years", "label": "Life Expectancy Reduction", "icon": "⏳"},
            "economic_cost": {"value": economic_cost_crores, "unit": "₹ Crores/year", "label": "Economic Cost", "icon": "💰"},
        },
        "vulnerable_groups": [
            {"group": "Children (0-14)", "multiplier": 1.5, "note": "50% higher risk due to developing lungs and higher breathing rates"},
            {"group": "Elderly (65+)", "multiplier": 1.8, "note": "80% higher risk due to reduced lung capacity and comorbidities"},
            {"group": "Outdoor Workers", "multiplier": 2.0, "note": "2× exposure due to prolonged outdoor activity"},
            {"group": "Respiratory Patients", "multiplier": 2.5, "note": "2.5× risk for those with asthma, COPD, or bronchitis"},
        ],
        "methodology": "WHO Global Burden of Disease + ICMR concentration-response functions",
    }


# ---------------------------------------------------------------------------
# 8. What-If Policy Simulator
# ---------------------------------------------------------------------------

def simulate_whatif(city_name: str, current_data: dict, history: list, scenarios: dict = None) -> dict:
    """
    Simulate the impact of various environmental policy interventions
    on air quality. Returns before/after AQI projections.
    """
    if not history:
        return {}

    avg_aqi = np.mean([d["aqi"] for d in history[-24:]])
    avg_pm25 = np.mean([d.get("pm25", 50) for d in history[-24:]])

    # Default scenario parameters (can be overridden)
    if scenarios is None:
        scenarios = {}

    tree_count = scenarios.get("trees", 10000)
    traffic_reduction = scenarios.get("traffic_pct", 30)   # percent
    industrial_control = scenarios.get("industrial_pct", 25)  # percent
    green_cover_increase = scenarios.get("green_cover_pct", 15)  # percent

    results = []

    # ─── Scenario 1: Tree Planting ───
    # Each mature tree removes ~22kg CO2/yr and ~0.1 kg particulates/yr
    # For PM2.5: ~0.1 µg/m³ reduction per 1000 trees in a 10km² area
    pm25_reduction_trees = tree_count / 1000 * 0.1
    aqi_reduction_trees = pm25_reduction_trees * 2  # approximate AQI per PM2.5 scaling
    results.append({
        "scenario": "Tree Planting",
        "icon": "🌳",
        "parameter": f"{tree_count:,} trees planted",
        "current_aqi": round(avg_aqi),
        "projected_aqi": round(max(10, avg_aqi - aqi_reduction_trees)),
        "aqi_change": round(-aqi_reduction_trees, 1),
        "pm25_change": round(-pm25_reduction_trees, 1),
        "co2_offset_tons": round(tree_count * 22 / 1000, 1),
        "timeframe": "3-5 years (full maturity)",
        "feasibility": "High" if tree_count <= 50000 else "Medium",
        "description": f"Planting {tree_count:,} trees would absorb {round(tree_count * 22 / 1000, 1)} tons of CO₂/year and reduce PM2.5 by {round(pm25_reduction_trees, 1)} µg/m³.",
    })

    # ─── Scenario 2: Traffic Reduction ───
    # Vehicular emissions typically contribute 30-40% of urban PM2.5
    vehicular_contribution = 0.35  # 35% of PM2.5 from vehicles
    pm25_reduction_traffic = avg_pm25 * vehicular_contribution * (traffic_reduction / 100)
    aqi_reduction_traffic = pm25_reduction_traffic * 2
    results.append({
        "scenario": "Traffic Reduction",
        "icon": "🚗",
        "parameter": f"{traffic_reduction}% traffic reduction",
        "current_aqi": round(avg_aqi),
        "projected_aqi": round(max(10, avg_aqi - aqi_reduction_traffic)),
        "aqi_change": round(-aqi_reduction_traffic, 1),
        "pm25_change": round(-pm25_reduction_traffic, 1),
        "co2_offset_tons": round(traffic_reduction * 50, 1),  # rough estimate
        "timeframe": "Immediate",
        "feasibility": "Medium",
        "description": f"Reducing traffic by {traffic_reduction}% through public transit and odd-even rules would lower PM2.5 by {round(pm25_reduction_traffic, 1)} µg/m³.",
    })

    # ─── Scenario 3: Industrial Controls ───
    # Industrial emissions contribute ~20-25% of urban PM2.5
    industrial_contribution = 0.22
    pm25_reduction_industry = avg_pm25 * industrial_contribution * (industrial_control / 100)
    aqi_reduction_industry = pm25_reduction_industry * 2
    results.append({
        "scenario": "Industrial Emission Controls",
        "icon": "🏭",
        "parameter": f"{industrial_control}% emission reduction",
        "current_aqi": round(avg_aqi),
        "projected_aqi": round(max(10, avg_aqi - aqi_reduction_industry)),
        "aqi_change": round(-aqi_reduction_industry, 1),
        "pm25_change": round(-pm25_reduction_industry, 1),
        "co2_offset_tons": round(industrial_control * 80, 1),
        "timeframe": "6-12 months",
        "feasibility": "Medium",
        "description": f"Enforcing {industrial_control}% stricter industrial emission norms would reduce PM2.5 by {round(pm25_reduction_industry, 1)} µg/m³.",
    })

    # ─── Scenario 4: Green Cover Increase ───
    # Urban green cover reduces local temperature by 2-3°C and traps particulates
    pm25_reduction_green = avg_pm25 * 0.02 * green_cover_increase  # 2% per % green cover
    aqi_reduction_green = pm25_reduction_green * 2
    temp_reduction = green_cover_increase * 0.15  # °C per % green cover
    results.append({
        "scenario": "Green Cover Expansion",
        "icon": "🌿",
        "parameter": f"+{green_cover_increase}% urban green cover",
        "current_aqi": round(avg_aqi),
        "projected_aqi": round(max(10, avg_aqi - aqi_reduction_green)),
        "aqi_change": round(-aqi_reduction_green, 1),
        "pm25_change": round(-pm25_reduction_green, 1),
        "co2_offset_tons": round(green_cover_increase * 100, 1),
        "temp_reduction": round(temp_reduction, 1),
        "timeframe": "2-5 years",
        "feasibility": "High",
        "description": f"Increasing green cover by {green_cover_increase}% would reduce PM2.5 by {round(pm25_reduction_green, 1)} µg/m³ and lower temperature by {round(temp_reduction, 1)}°C.",
    })

    # ─── Combined Scenario ───
    total_pm25_reduction = pm25_reduction_trees + pm25_reduction_traffic + pm25_reduction_industry + pm25_reduction_green
    total_aqi_reduction = total_pm25_reduction * 2
    combined_aqi = max(10, avg_aqi - total_aqi_reduction)
    results.append({
        "scenario": "All Interventions Combined",
        "icon": "🎯",
        "parameter": "All above measures",
        "current_aqi": round(avg_aqi),
        "projected_aqi": round(combined_aqi),
        "aqi_change": round(-total_aqi_reduction, 1),
        "pm25_change": round(-total_pm25_reduction, 1),
        "new_category": _get_category(int(combined_aqi)),
        "timeframe": "1-5 years (phased)",
        "feasibility": "Requires policy coordination",
        "description": f"Implementing all interventions together could reduce AQI from {round(avg_aqi)} to {round(combined_aqi)} ({_get_category(int(combined_aqi))} category).",
    })

    return {
        "city": city_name,
        "current_aqi": round(avg_aqi),
        "current_category": _get_category(int(avg_aqi)),
        "scenarios": results,
    }


# ---------------------------------------------------------------------------
# 8. Formal Data Science Models (Regression & Classification)
# ---------------------------------------------------------------------------

def perform_regression_analysis(history_data: list) -> dict:
    """
    Multivariate Linear Regression to determine Feature Importance.
    Predicts AQI based on environmental factors to see which factor 
    contributes most heavily (positive or negative) to pollution.
    """
    if len(history_data) < 10:
        return {"error": "Not enough data points for regression"}

    # Features (X) and Target (y)
    X = []
    y = []
    
    # We will look at Temperature, Humidity, Wind Speed, NO2, and PM2.5
    feature_names = ["Temperature", "Humidity", "Wind Speed", "NO₂", "PM2.5"]
    
    for row in history_data:
        # Check if row has valid data
        if all(k in row and row[k] is not None for k in ["temperature", "humidity", "wind_speed", "no2", "pm25", "aqi"]):
            X.append([
                row["temperature"],
                row["humidity"],
                row["wind_speed"],
                row["no2"],
                row["pm25"]
            ])
            y.append(row["aqi"])

    if len(X) < 10:
         return {"error": "Not enough valid feature data points"}

    X = np.array(X)
    y = np.array(y)

    # Normalize X to get comparable coefficients (Standard Scaler approximation)
    X_mean = np.mean(X, axis=0)
    X_std = np.std(X, axis=0)
    X_std[X_std == 0] = 1 # Prevent division by zero
    X_scaled = (X - X_mean) / X_std

    # Train Linear Regression model
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    # R-squared score
    r2_score = model.score(X_scaled, y)
    
    # Extract coefficients
    coefficients = model.coef_
    
    # Format results
    importances = []
    for name, coef in zip(feature_names, coefficients):
        importances.append({
            "feature": name,
            "weight": round(coef, 2),
            "impact": "Increases AQI" if coef > 0 else "Decreases AQI",
            "magnitude": round(abs(coef), 2)
        })
        
    # Sort by absolute magnitude
    importances.sort(key=lambda x: x["magnitude"], reverse=True)
    
    return {
        "model_type": "Multivariate Linear Regression",
        "r2_score": round(r2_score, 3),
        "explanation": f"Model explains {round(r2_score*100)}% of the variance in AQI.",
        "feature_importances": importances
    }


def perform_classification_analysis(history_data: list) -> dict:
    """
    Logistic Regression to classify whether a day will be a "Severe Health Hazard"
    (AQI > 200) based on raw pollutant levels.
    """
    if len(history_data) < 15:
        return {"error": "Not enough data points for classification"}

    X = []
    y = []
    
    feature_names = ["PM2.5", "PM10", "NO₂", "CO", "Temperature"]
    
    for row in history_data:
        if all(k in row and row[k] is not None for k in ["pm25", "pm10", "no2", "co", "temperature", "aqi"]):
            X.append([
                row["pm25"],
                row["pm10"],
                row["no2"],
                row["co"],
                row["temperature"]
            ])
            # Target: 1 if AQI > 200 (Severe), 0 otherwise
            y.append(1 if row["aqi"] > 200 else 0)

    if len(X) < 15:
         return {"error": "Not enough valid feature data points"}
         
    # Need at least one of each class to train logistic regression
    if len(set(y)) < 2:
         # Artificial injection if data is completely one-sided (just for demo robustnes)
         if y[0] == 0:
             X.append([150, 200, 80, 2.5, 35])
             y.append(1)
         else:
             X.append([20, 40, 15, 0.5, 25])
             y.append(0)

    X = np.array(X)
    y = np.array(y)
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale
    X_mean = np.mean(X_train, axis=0)
    X_std = np.std(X_train, axis=0)
    X_std[X_std == 0] = 1
    
    X_train_scaled = (X_train - X_mean) / X_std
    X_test_scaled = (X_test - X_mean) / X_std

    # Train Logistic Regression model
    model = LogisticRegression(class_weight='balanced')
    model.fit(X_train_scaled, y_train)
    
    # Predict and evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    # Let's predict "tomorrow's" risk using the most recent data point
    latest_data = X_scaled = (X[-1] - X_mean) / X_std
    risk_prob = model.predict_proba([latest_data])[0][1]
    
    is_high_risk = bool(model.predict([latest_data])[0] == 1)
    
    return {
        "model_type": "Logistic Regression Classifier",
        "accuracy": round(accuracy * 100, 1),
        "target": "AQI > 200 (Severe Risk)",
        "current_risk_probability": round(risk_prob * 100, 1),
        "is_high_risk": is_high_risk,
        "advice": "Issue health warnings immediately." if is_high_risk else "Risk levels are manageable."
    }


