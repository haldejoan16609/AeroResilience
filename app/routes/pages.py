"""
AeroResilience — Page Routes (serves HTML templates)
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "dashboard"})


@router.get("/map")
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request, "page": "map"})


@router.get("/insights")
async def insights_page(request: Request):
    return templates.TemplateResponse("insights.html", {"request": request, "page": "insights"})


@router.get("/community")
async def community_page(request: Request):
    return templates.TemplateResponse("community.html", {"request": request, "page": "community"})
