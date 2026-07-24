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
    from menu_data import MENU_CATALOG

    assert "부리또" in {menu["name"] for menu in MENU_CATALOG}


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
