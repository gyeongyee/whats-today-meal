from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_home_and_static_assets_are_served():
    home = client.get("/")
    assert home.status_code == 200
    assert "오늘 뭐 먹지 AI" in home.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
    assert len(response.json()["recommendations"]) == 3


def test_invalid_extra_input_is_rejected():
    response = client.post("/api/recommend", json={"unknown": "value"})
    assert response.status_code == 422
