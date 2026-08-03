from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_service import AISemanticService
from menu_data import MENU_CATALOG
from menu_expansion import image_alias_for
from models import RecommendRequest, RecommendResponse
from recommendation_engine import RecommendationEngine

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _load_refreshed_image_overrides() -> dict[str, str]:
    refreshed_dir = BASE_DIR / "static" / "images" / "generated" / "refreshed"
    manifest_paths = (
        refreshed_dir / "audit_batch_a.tsv",
        BASE_DIR / "audit_batch_b.tsv",
        refreshed_dir / "audit_batch_b.tsv",
        BASE_DIR / "audit_batch_c.tsv",
        refreshed_dir / "audit_batch_c.tsv",
    )
    overrides: dict[str, str] = {}
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            separator = "|" if "|" in line else "\t"
            menu_name, separator, image_path = line.partition(separator)
            if separator and menu_name.strip() and image_path.strip():
                overrides[menu_name.strip()] = image_path.strip()
    return overrides


REFRESHED_IMAGE_OVERRIDES = _load_refreshed_image_overrides()

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
    generated_image_count = 118
    base_image_map = {
        menu["name"]: f"/static/images/generated/menu-{index:03d}.jpg"
        for index, menu in enumerate(
            MENU_CATALOG[:generated_image_count],
            start=1,
        )
    }
    fallback_by_kind = {
        "국밥": "돼지국밥",
        "탕": "갈비탕",
        "찌개": "김치찌개",
        "전골": "샤브샤브",
        "면": "잔치국수",
        "덮밥": "비빔밥",
        "볶음밥": "볶음밥",
        "볶음": "제육볶음",
        "구이": "생선구이",
        "정식": "쌈밥",
        "분식": "김밥",
        "튀김": "돈가스",
        "간편식": "김밥",
        "초밥": "초밥",
    }
    menu_image_map: dict[str, str] = {}
    for menu in MENU_CATALOG:
        direct_image = base_image_map.get(menu["name"])
        if direct_image:
            menu_image_map[menu["name"]] = direct_image
            continue
        alias = image_alias_for(menu["name"]) or fallback_by_kind.get(menu["kind"])
        menu_image_map[menu["name"]] = base_image_map.get(
            alias or "",
            "/static/images/food-card-bg.webp",
        )
    menu_image_map.update(
        {
            menu_name: image_path
            for menu_name, image_path in REFRESHED_IMAGE_OVERRIDES.items()
            if menu_name in menu_image_map
        }
    )
    # Photos the user explicitly reviewed always take precedence over the
    # broad ingredient-based refresh batch.
    menu_image_map.update(
        {
            "물밀면": "/static/images/generated/mul-milmyeon.jpg",
            "물회": "/static/images/generated/mulhoe.jpg",
            "중국냉면": "/static/images/generated/chinese-naengmyeon.jpg",
            "장어덮밥": "/static/images/generated/eel-rice-bowl.jpg",
            "막국수": "/static/images/generated/makguksu.png",
            "비빔막국수": "/static/images/generated/makguksu.png",
            "곱창전골": "/static/images/generated/gopchang-jeongol.png",
            "고등어구이": "/static/images/generated/grilled-mackerel.png",
            "삼치구이": "/static/images/generated/grilled-spanish-mackerel.png",
            "갈치구이": "/static/images/generated/grilled-cutlassfish.png",
            "임연수구이": "/static/images/generated/grilled-atka-mackerel.png",
            "조기구이": "/static/images/generated/grilled-yellow-croaker.png",
            "생선구이정식": "/static/images/generated/grilled-fish-set.png",
            "만두": "/static/images/generated/mandu.png",
            "김치만두": "/static/images/generated/kimchi-mandu.png",
            "고기만두": "/static/images/generated/meat-mandu.png",
            "라볶이": "/static/images/generated/rabokki.png",
            "떡갈비정식": "/static/images/generated/tteokgalbi-set.png",
            "굴국밥": "/static/images/generated/oyster-gukbap.png",
            "선지해장국": "/static/images/generated/seonji-haejangguk.png",
            "내장국밥": "/static/images/generated/offal-gukbap.png",
            "뼈해장국": "/static/images/generated/pork-bone-haejangguk.png",
            "양평해장국": "/static/images/generated/yangpyeong-haejangguk.png",
            "올갱이국": "/static/images/generated/olgaengi-soup.png",
            "재첩국": "/static/images/generated/jaecheop-soup.png",
            "미역국": "/static/images/generated/seaweed-soup.png",
            "소고기무국": "/static/images/generated/beef-radish-soup.png",
            "나주곰탕": "/static/images/generated/naju-gomtang.png",
            "도가니탕": "/static/images/generated/dogani-tang.png",
            "꼬리곰탕": "/static/images/generated/oxtail-gomtang.png",
            "반계탕": "/static/images/generated/half-chicken-soup.png",
            "백숙": "/static/images/generated/baeksuk.png",
            "추어탕": "/static/images/generated/chueotang.png",
            "감자탕": "/static/images/generated/gamjatang.png",
            "매운갈비탕": "/static/images/generated/spicy-galbitang.png",
            "사골우거지탕": "/static/images/generated/sagol-ugeojitang.png",
            "버섯들깨탕": "/static/images/generated/mushroom-perilla-soup.png",
            "들깨수제비": "/static/images/generated/perilla-sujebi.png",
            "청국장찌개": "/static/images/generated/menu-075.jpg",
            "군만두": "/static/images/generated/mandu.png",
            "찐만두": "/static/images/generated/mandu.png",
            "떡만둣국": "/static/images/generated/menu-085.jpg",
            "만둣국": "/static/images/generated/menu-085.jpg",
            "순두부국밥": "/static/images/generated/menu-006.jpg",
            "감자수제비": "/static/images/generated/menu-106.jpg",
            "김치콩나물국밥": "/static/images/generated/kimchi-bean-sprout-gukbap.jpg",
            "꽃게탕": "/static/images/generated/flower-crab-stew.jpg",
            "오징어찌개": "/static/images/generated/squid-stew.jpg",
            "버섯전골": "/static/images/generated/mushroom-jeongol.jpg",
            "불고기전골": "/static/images/generated/bulgogi-jeongol.jpg",
            "만두전골": "/static/images/generated/mandu-jeongol.jpg",
            "두부전골": "/static/images/generated/tofu-jeongol.jpg",
        }
    )
    monthly_menus = {
        1: ["떡국", "만두전골", "김치찌개", "설렁탕", "부대찌개"],
        2: ["순두부찌개", "감자탕", "잔치국수", "돈가스", "닭갈비"],
        3: ["쭈꾸미볶음", "바지락칼국수", "산채비빔밥", "샤브샤브", "비빔밥"],
        4: ["비빔국수", "제육볶음", "연어덮밥", "샌드위치", "포케"],
        5: ["냉면", "회덮밥", "초밥", "쌀국수", "막국수"],
        6: ["물밀면", "콩국수", "비빔밀면", "물회", "삼계탕"],
        7: ["물냉면", "콩국수", "삼계탕", "물회", "중국냉면"],
        8: ["메밀소바", "막국수", "회덮밥", "장어덮밥", "초밥"],
        9: ["버섯전골", "추어탕", "고등어구이", "들깨칼국수", "장어덮밥"],
        10: ["갈비탕", "육개장", "불고기전골", "김치찜", "추어탕"],
        11: ["칼국수", "부대찌개", "곱창전골", "알탕", "감자탕"],
        12: ["굴국밥", "만두전골", "김치찌개", "설렁탕", "갈비탕"],
    }
    korea_time = timezone(timedelta(hours=9))
    current_month = datetime.now(korea_time).month
    monthly_recommendation = {
        "month": current_month,
        "emoji": "📅",
        "description": "이달의 날씨와 계절감을 반영한 점심 메뉴",
        "menus": monthly_menus[current_month],
    }
    situation_recommendations = [
        {
            "id": "rainy",
            "label": "비 오는 날",
            "emoji": "🌧️",
            "menus": ["바지락칼국수", "수제비", "김치찌개"],
        },
        {
            "id": "tired",
            "label": "힘든 날",
            "emoji": "💪",
            "menus": ["제육볶음", "닭갈비", "갈비탕"],
        },
        {
            "id": "dinner",
            "label": "회식",
            "emoji": "🍻",
            "menus": ["보쌈", "족발", "곱창전골"],
        },
        {
            "id": "hangover",
            "label": "해장",
            "emoji": "🥣",
            "menus": ["뼈해장국", "콩나물국밥", "황태해장국"],
        },
    ]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ai_configured": ai_service.configured,
            "menu_groups": menu_groups,
            "menu_count": len(MENU_CATALOG),
            "menu_image_map": menu_image_map,
            "monthly_recommendation": monthly_recommendation,
            "situation_recommendations": situation_recommendations,
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
