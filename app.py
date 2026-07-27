from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_service import AISemanticService
from menu_data import MENU_CATALOG
from models import RecommendRequest, RecommendResponse
from recommendation_engine import RecommendationEngine

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(
    title="오늘 뭐 먹지 AI",
    description="최근 3일 식사를 고려한 점심 메뉴 추천 서비스",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

ai_service = AISemanticService.from_env()
recommendation_engine = RecommendationEngine(ai_service)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    menu_groups: dict[str, list[str]] = {}
    for menu in MENU_CATALOG:
        menu_groups.setdefault(menu["cuisine"], []).append(menu["name"])
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ai_configured": ai_service.configured,
            "menu_groups": menu_groups,
            "menu_count": len(MENU_CATALOG),
        },
    )


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "ai_configured": ai_service.configured,
    }


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(payload: RecommendRequest) -> RecommendResponse:
    return await recommendation_engine.recommend(payload)


@app.get("/api/menus/{menu_name}")
async def menu_details(menu_name: str) -> dict[str, object]:
    menu = next((item for item in MENU_CATALOG if item["name"] == menu_name), None)
    if menu is None:
        raise HTTPException(status_code=404, detail="메뉴 정보를 찾을 수 없어요.")
    description, calorie_min, calorie_max, visual_key, emoji = (
        recommendation_engine._menu_details(menu)
    )
    return {
        "menu": menu["name"],
        "cuisine": menu["cuisine"],
        "kind": menu["kind"],
        "tags": menu["tags"],
        "description": description,
        "calorie_min": calorie_min,
        "calorie_max": calorie_max,
        "visual_key": visual_key,
        "emoji": emoji,
    }
