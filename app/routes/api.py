"""
AeroResilience — API Routes (JSON endpoints)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.database import get_session
from app.models import CommunityAction
from app.services import air_quality, ml_engine

router = APIRouter(prefix="/api")


# ── Schemas ──────────────────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    action_type: str
    location: str
    impact_value: int = 1
    description: Optional[str] = None
    contributor: Optional[str] = "Anonymous"


# ── Air Quality Endpoints ────────────────────────────────────────────────────

@router.get("/aqi/current")
async def get_current_aqi():
    """Get current AQI for all monitored cities."""
    data = await air_quality.get_current_data()
    return {"status": "ok", "cities": data, "count": len(data)}


@router.get("/aqi/history/{city}")
async def get_city_history(city: str, hours: int = 168):
    """Get historical AQI data for a specific city."""
    hours = min(hours, 720)  # Cap at 30 days
    data = await air_quality.get_historical_data(city, hours)
    if not data:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return {"status": "ok", "city": city, "data": data, "count": len(data)}


# ── ML / AI Endpoints ────────────────────────────────────────────────────────

@router.get("/forecast/{city}")
async def get_forecast(city: str, hours: int = 72):
    """Get AI-powered AQI forecast for a city."""
    hours = min(hours, 168)
    history = await air_quality.get_historical_data(city, 168)
    if not history:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")

    forecast = ml_engine.forecast_aqi(history, forecast_hours=hours)
    return {"status": "ok", "city": city, "forecast": forecast}


@router.get("/anomalies/{city}")
async def get_anomalies(city: str):
    """Detect anomalous AQI readings for a city."""
    history = await air_quality.get_historical_data(city, 168)
    anomalies = ml_engine.detect_anomalies(history)
    return {"status": "ok", "city": city, "anomalies": anomalies, "count": len(anomalies)}


@router.get("/vulnerability/{city}")
async def get_vulnerability(city: str):
    """Get climate vulnerability assessment for a city."""
    history = await air_quality.get_historical_data(city, 168)
    assessment = ml_engine.assess_vulnerability(history)
    return {"status": "ok", "city": city, "assessment": assessment}


@router.get("/sources/{city}")
async def get_pollution_sources(city: str):
    """Get pollution source attribution for a city."""
    current = await air_quality.get_current_data()
    city_data = next((c for c in current if c["city"] == city), None)
    if not city_data:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")

    sources = ml_engine.attribute_pollution_sources(city_data)
    return {"status": "ok", "city": city, "sources": sources}


@router.get("/insights/{city}")
async def get_insights(city: str):
    """Get AI-generated insights for a city."""
    current_data_list = await air_quality.get_current_data()
    city_current = next((c for c in current_data_list if c["city"] == city), None)
    if not city_current:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")

    history = await air_quality.get_historical_data(city, 168)
    forecast = ml_engine.forecast_aqi(history, 24)
    insights = await ml_engine.generate_insights(city, city_current, history, forecast)
    return {"status": "ok", "city": city, "insights": insights}


@router.get("/correlation/{city}")
async def get_correlation(city: str):
    """Get correlation heatmap data between environmental variables."""
    history = await air_quality.get_historical_data(city, 168)
    correlations = ml_engine.compute_correlations(history)
    return {"status": "ok", "city": city, "correlations": correlations}


@router.get("/health-impact/{city}")
async def get_health_impact(city: str, population: int = 1_000_000):
    """Get estimated health impacts of air pollution for a city."""
    history = await air_quality.get_historical_data(city, 168)
    impact = ml_engine.estimate_health_impact(city, history, population)
    return {"status": "ok", "city": city, "impact": impact}


@router.get("/whatif/{city}")
async def get_whatif(city: str, trees: int = 10000, traffic_pct: int = 30,
                     industrial_pct: int = 25, green_cover_pct: int = 15):
    """Run what-if policy simulation for a city."""
    current_data_list = await air_quality.get_current_data()
    city_current = next((c for c in current_data_list if c["city"] == city), None)
    if not city_current:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")

    history = await air_quality.get_historical_data(city, 168)
    scenarios = {"trees": trees, "traffic_pct": traffic_pct,
                 "industrial_pct": industrial_pct, "green_cover_pct": green_cover_pct}
    result = ml_engine.simulate_whatif(city, city_current, history, scenarios)
    return {"status": "ok", "city": city, "simulation": result}


# ── Community Actions ─────────────────────────────────────────────────────────

@router.post("/actions")
async def create_action(action: ActionCreate, session: AsyncSession = Depends(get_session)):
    """Log a new community environmental action."""
    db_action = CommunityAction(
        action_type=action.action_type,
        location=action.location,
        impact_value=action.impact_value,
        description=action.description,
        contributor=action.contributor,
    )
    session.add(db_action)
    await session.commit()
    await session.refresh(db_action)
    return {
        "status": "ok",
        "action": {
            "id": db_action.id,
            "action_type": db_action.action_type,
            "location": db_action.location,
            "impact_value": db_action.impact_value,
            "contributor": db_action.contributor,
            "created_at": db_action.created_at.isoformat() if db_action.created_at else None,
        },
    }


@router.get("/actions")
async def get_actions(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Get recent community actions."""
    result = await session.execute(
        select(CommunityAction).order_by(CommunityAction.created_at.desc()).limit(limit)
    )
    actions = result.scalars().all()
    return {
        "status": "ok",
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "location": a.location,
                "impact_value": a.impact_value,
                "description": a.description,
                "contributor": a.contributor,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in actions
        ],
    }


@router.get("/actions/stats")
async def get_action_stats(session: AsyncSession = Depends(get_session)):
    """Get aggregated community impact stats."""
    total_actions = await session.execute(select(func.count(CommunityAction.id)))
    total_impact = await session.execute(select(func.sum(CommunityAction.impact_value)))
    total_contributors = await session.execute(
        select(func.count(func.distinct(CommunityAction.contributor)))
    )

    # Breakdown by type
    type_breakdown = await session.execute(
        select(CommunityAction.action_type, func.count(), func.sum(CommunityAction.impact_value))
        .group_by(CommunityAction.action_type)
    )

    return {
        "status": "ok",
        "stats": {
            "total_actions": total_actions.scalar() or 0,
            "total_impact": total_impact.scalar() or 0,
            "total_contributors": total_contributors.scalar() or 0,
            "breakdown": [
                {"type": row[0], "count": row[1], "impact": row[2] or 0}
                for row in type_breakdown.all()
            ],
        },
    }

# ---------------------------------------------------------------------------
# 6. Formal Data Science APIs (Regression & Classification)
# ---------------------------------------------------------------------------

@router.get("/ds-regression/{city}")
async def api_ds_regression(city: str):
    """Run Multivariate Linear Regression to get feature importances."""
    history = await air_quality.get_historical_data(city, hours=90 * 24)  # Use 90 days for better model training
    return ml_engine.perform_regression_analysis(history)

@router.get("/ds-classification/{city}")
async def api_ds_classification(city: str):
    """Run Logistic Regression Classification for severe risk prediction."""
    history = await air_quality.get_historical_data(city, hours=90 * 24)
    return ml_engine.perform_classification_analysis(history)
