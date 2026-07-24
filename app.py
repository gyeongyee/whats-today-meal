from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_service import AISemanticService
from kakao_client import KakaoLocalClient
from models import RecommendRequest, RecommendResponse, RestaurantSearchResponse
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
kakao_client = KakaoLocalClient.from_env()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"ai_configured": ai_service.configured, "kakao_configured": kakao_client.configured},
    )


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "ai_configured": ai_service.configured,
        "kakao_api_configured": kakao_client.configured,
    }


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(payload: RecommendRequest) -> RecommendResponse:
    return await recommendation_engine.recommend(payload)


@app.get("/api/geocode")
async def geocode(address: str = Query(min_length=2, max_length=150)) -> dict[str, str]:
    return await kakao_client.geocode(address)


@app.get("/api/restaurants", response_model=RestaurantSearchResponse)
async def restaurants(
    query: str = Query(min_length=1, max_length=50),
    x: float = Query(ge=-180, le=180),
    y: float = Query(ge=-90, le=90),
    radius: int = Query(default=1500, ge=500, le=3000),
) -> RestaurantSearchResponse:
    return await kakao_client.search_restaurants(query=query, x=x, y=y, radius=radius)
