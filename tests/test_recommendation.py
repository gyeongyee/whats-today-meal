import asyncio

from ai_service import AISemanticService, AISettings
from models import RecommendRequest, TeamMemberMeals
from recommendation_engine import RecommendationEngine


def make_engine() -> RecommendationEngine:
    return RecommendationEngine(AISemanticService(AISettings("", "", "")))


def test_recommendation_works_without_ai_key():
    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(
                yesterday="돈가스",
                two_days_ago="김치찌개",
                three_days_ago="짜장면",
            )
        )
    )
    assert result.engine == "local"
    assert len(result.recommendations) == 3
    assert all(item.menu != "돈가스" for item in result.recommendations)
    assert all(item.menu != "치킨가스" for item in result.recommendations)


def test_relaxed_mode_still_excludes_exact_yesterday_menu():
    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(
                yesterday="김치찌개",
                two_days_ago="샐러드",
                three_days_ago="우동",
                mode="relaxed",
                retry_count=2,
            )
        )
    )
    assert len(result.recommendations) == 3
    assert all(item.menu != "김치찌개" for item in result.recommendations)
    assert result.relax_level == 2


def test_spicy_items_are_avoided_when_requested():
    result = asyncio.run(
        make_engine().recommend(RecommendRequest(avoid_spicy=True))
    )
    spicy_names = {"제육볶음", "김치찌개", "순두부찌개", "부대찌개", "떡볶이", "짬뽕", "닭갈비"}
    assert not {item.menu for item in result.recommendations} & spicy_names


def test_all_of_yesterdays_multiple_meals_are_excluded():
    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(
                yesterday="돈가스, 햄버거",
                two_days_ago="김치찌개, 샐러드",
                three_days_ago="짜장면, 우동",
                mode="relaxed",
            )
        )
    )
    names = {item.menu for item in result.recommendations}
    assert "돈가스" not in names
    assert "햄버거" not in names


def test_new_diverse_menus_include_burrito():
    from menu_data import ALIASES, MENU_CATALOG

    by_name = {menu["name"]: menu for menu in MENU_CATALOG}
    assert "부리또" in by_name
    assert len(MENU_CATALOG) == 113
    assert by_name["카레"]["cuisine"] == "일식"
    assert by_name["난과 커리"]["cuisine"] == "인도"
    assert by_name["로코모코"]["cuisine"] == "양식"
    assert by_name["갈릭 쉬림프"]["cuisine"] == "양식"
    assert by_name["포케"]["cuisine"] == "양식"
    assert by_name["치킨"]["cuisine"] == "양식"
    assert by_name["오므라이스"]["cuisine"] == "일식"
    assert by_name["함박스테이크"]["cuisine"] == "일식"
    assert ALIASES["커리"] == "난과 커리"
    southeast_asian = {
        "쌀국수", "팟타이", "분짜", "반미", "월남쌈",
        "나시고렝", "똠얌꿍", "태국커리", "카오팟",
    }
    assert all(by_name[name]["cuisine"] == "동남아" for name in southeast_asian)


def test_requested_korean_and_chinese_menus_are_classified():
    from menu_data import MENU_CATALOG

    by_name = {menu["name"]: menu for menu in MENU_CATALOG}
    chinese = {
        "탕수육", "사천 탕수육", "깐풍기", "짬뽕밥", "백짬뽕",
        "차돌짬뽕", "밀면", "울면", "잡채밥", "중화비빔밥",
    }
    korean = {"김밥", "떡볶이", "라면", "수제비", "김치찜", "족발"}
    assert all(by_name[name]["cuisine"] == "중식" for name in chinese)
    assert all(by_name[name]["cuisine"] == "한식" for name in korean)
    assert not any(menu["cuisine"] == "분식" for menu in MENU_CATALOG)


def test_diet_filter_returns_requested_diet_menus_only():
    result = asyncio.run(
        make_engine().recommend(RecommendRequest(preferred_tags=["다이어트"]))
    )
    assert {item.menu for item in result.recommendations} <= {
        "포케", "샐러드", "샌드위치", "두부덮밥",
    }
    assert len(result.recommendations) == 3


def test_vegan_filter_returns_only_explicit_vegan_menus():
    from menu_data import MENU_CATALOG

    by_name = {menu["name"]: menu for menu in MENU_CATALOG}
    result = asyncio.run(
        make_engine().recommend(RecommendRequest(preferred_tags=["비건"]))
    )
    assert len(result.recommendations) == 3
    assert all("비건" in by_name[item.menu]["tags"] for item in result.recommendations)


def test_combined_diet_and_vegan_filters_still_return_three_vegan_menus():
    from menu_data import MENU_CATALOG

    by_name = {menu["name"]: menu for menu in MENU_CATALOG}
    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(preferred_tags=["다이어트", "비건"])
        )
    )
    assert len(result.recommendations) == 3
    assert all("비건" in by_name[item.menu]["tags"] for item in result.recommendations)


def test_team_recommendation_excludes_everyones_yesterday_meals():
    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(
                yesterday="돈가스",
                two_days_ago="김치찌개",
                three_days_ago="짜장면",
                mode="relaxed",
                team_members=[
                    TeamMemberMeals(
                        name="민지",
                        yesterday="햄버거, 부리또",
                        two_days_ago="초밥",
                        three_days_ago="쌀국수",
                    ),
                    TeamMemberMeals(
                        name="현우",
                        yesterday="제육볶음",
                        two_days_ago="파스타",
                        three_days_ago="샐러드",
                    ),
                ],
            )
        )
    )
    names = {item.menu for item in result.recommendations}
    assert not names & {"돈가스", "햄버거", "부리또", "제육볶음"}
    assert result.participant_count == 3
    assert all("3명" in item.reason for item in result.recommendations)


def test_detailed_preferences_narrow_results_and_add_menu_details():
    from menu_data import MENU_CATALOG

    result = asyncio.run(
        make_engine().recommend(
            RecommendRequest(
                preferred_cuisines=["세계"],
                preferred_tags=["닭고기", "향신료"],
                prefer_hearty=True,
            )
        )
    )
    by_name = {menu["name"]: menu for menu in MENU_CATALOG}
    matches = [
        item for item in result.recommendations
        if set(by_name[item.menu]["tags"]) & {"닭고기", "향신료"}
    ]
    assert len(matches) >= 2
    assert all(item.description for item in result.recommendations)
    assert all(item.calorie_min < item.calorie_max for item in result.recommendations)
