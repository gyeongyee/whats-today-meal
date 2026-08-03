from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_home_and_static_assets_are_served():
    home = client.get("/")
    current_month = datetime.now(timezone(timedelta(hours=9))).month
    assert home.status_code == 200
    assert 'class="hero shell"' in home.text
    assert "고민은 짧게" in home.text
    assert "점심은 맛있게" in home.text
    assert "어제와는 다르게" not in home.text
    assert "오늘 뭐 먹지 AI" in home.text
    assert "지금 만날 수 있는 270가지 메뉴" in home.text
    assert "아무것도 선택하지 않아도 정상 작동합니다." in home.text
    assert 'class="filter-group mood-filter-group"' in home.text
    assert "팀원을 추가하면 모두의 어제 메뉴를 제외하고" not in home.text
    assert 'value="다이어트"' in home.text
    assert 'value="비건"' in home.text
    assert 'value="시원한 국물"' in home.text
    assert 'value="보양식"' in home.text
    assert f"{current_month}월의 추천 메뉴" in home.text
    assert "HOW IT WORKS" not in home.text
    assert home.text.count('class="season-menu"') == 3
    assert home.text.count('class="season-menu situation-menu"') == 12
    assert f"{current_month}월 추천" in home.text
    assert "MONTHLY TOP 3" in home.text
    assert "TOP 5" not in home.text
    assert home.text.count('class="rank-medal rank-') == 3
    assert "비 오는 날" in home.text and "바지락칼국수" in home.text
    assert "힘든 날" in home.text and "제육볶음" in home.text
    assert "회식" in home.text and "보쌈" in home.text
    assert "해장" in home.text and "뼈해장국" in home.text
    assert 'class="catalog-menu"' in home.text
    assert 'id="menuDetailDialog"' in home.text
    assert "점진적으로 메뉴 추가 예정" in home.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert "style.css?v=29" in home.text
    assert 'class="timeline-disclosure"' in home.text
    assert 'media="(prefers-color-scheme: dark)"' in home.text
    assert "app.js?v=18" in home.text
    assert home.text.count('value="매운맛"') == 1
    assert home.text.count('id="avoidSpicy"') == 1
    assert home.text.count('class="season-card monthly-card"') == 1
    assert home.text.count('class="season-card situation-card"') == 1
    assert home.text.count('class="catalog-group"') >= 5
    assert client.get("/static/images/menus/tofu-rice-bowl.png").status_code == 200
    assert client.get("/static/images/menus/vegan-gimbap.png").status_code == 200
    assert home.text.count("/static/images/generated/menu-") == 252
    assert "/static/images/generated/makguksu.png" in home.text
    assert "/static/images/generated/gopchang-jeongol.png" in home.text
    for filename in (
        "grilled-mackerel.png",
        "grilled-spanish-mackerel.png",
        "grilled-cutlassfish.png",
        "grilled-atka-mackerel.png",
        "grilled-yellow-croaker.png",
        "grilled-fish-set.png",
        "mandu.png",
        "kimchi-mandu.png",
        "meat-mandu.png",
        "rabokki.png",
        "tteokgalbi-set.png",
    ):
        assert f"/static/images/generated/{filename}" in home.text
        assert client.get(f"/static/images/generated/{filename}").status_code == 200
    for index in (1, 22, 46, 118):
        assert client.get(f"/static/images/generated/menu-{index:03d}.jpg").status_code == 200
    for filename in ("mul-milmyeon.jpg", "mulhoe.jpg", "chinese-naengmyeon.jpg", "eel-rice-bowl.jpg"):
        assert client.get(f"/static/images/generated/{filename}").status_code == 200


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "kakao_api_configured" not in response.json()


def test_removed_restaurant_endpoints_are_not_exposed():
    assert client.get("/api/geocode", params={"address": "서울시청"}).status_code == 404
    assert client.get(
        "/api/restaurants",
        params={"query": "돈가스", "x": 126.97, "y": 37.56},
    ).status_code == 404


def test_recommend_endpoint_validates_and_returns_three_items():
    response = client.post(
        "/api/recommend",
        json={
            "yesterday": "짜장면",
            "two_days_ago": "돈가스",
            "three_days_ago": "김치찌개",
            "mode": "strict",
            "prefer_light": True,
        },
    )
    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert len(recommendations) == 3
    assert all(item["description"] for item in recommendations)
    assert all(item["calorie_min"] < item["calorie_max"] for item in recommendations)
    assert all(item["visual_key"] and item["emoji"] for item in recommendations)


def test_invalid_extra_input_is_rejected():
    response = client.post("/api/recommend", json={"unknown": "value"})
    assert response.status_code == 422


def test_menu_details_api_returns_description_and_calories():
    response = client.get("/api/menus/라면")
    assert response.status_code == 200
    item = response.json()
    assert item["menu"] == "라면"
    assert item["cuisine"] == "한식"
    assert item["description"]
    assert item["calorie_min"] < item["calorie_max"]
    assert isinstance(item["tags"], list)


def test_menu_details_api_returns_404_for_unknown_menu():
    response = client.get("/api/menus/없는메뉴")
    assert response.status_code == 404


def test_team_members_are_accepted_and_counted():
    response = client.post(
        "/api/recommend",
        json={
            "yesterday": "돈가스",
            "team_members": [
                {
                    "name": "동료 1",
                    "yesterday": "햄버거",
                    "two_days_ago": "부리또",
                    "three_days_ago": "초밥",
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["participant_count"] == 2
    assert all(
        item["menu"] not in {"돈가스", "햄버거"}
        for item in response.json()["recommendations"]
    )


def test_team_member_limit_is_validated():
    response = client.post(
        "/api/recommend",
        json={
            "team_members": [
                {"name": f"동료 {index}"}
                for index in range(10)
            ]
        },
    )
    assert response.status_code == 422
