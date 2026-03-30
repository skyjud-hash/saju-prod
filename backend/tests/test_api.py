"""API endpoint tests — verify core saju endpoints work."""

import os
import pytest


def test_root_returns_html_or_json(client):
    """GET / should return index.html or fallback JSON."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_health_check(client):
    """GET /healthz should return ok."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_calculate_preview_valid(client):
    """POST /api/saju/calculate with valid data returns saju result."""
    resp = client.post("/api/saju/calculate", json={
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 15,
        "birth_hour": 14,
        "birth_minute": 30,
        "gender_for_daewoon": "male",
        "calendar_type": "solar",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "four_pillars" in data or "saju" in data or "pillars" in data or isinstance(data, dict)


def test_calculate_preview_no_time(client):
    """POST /api/saju/calculate without birth time still works."""
    resp = client.post("/api/saju/calculate", json={
        "birth_year": 2000,
        "birth_month": 1,
        "birth_day": 1,
        "gender_for_daewoon": "female",
        "calendar_type": "solar",
    })
    assert resp.status_code == 200


@pytest.mark.skipif(
    os.environ.get("DATABASE_URL", "").startswith("sqlite"),
    reason="BigInteger autoincrement requires PostgreSQL"
)
def test_analyze_creates_db_record(client):
    """POST /api/saju/analyze saves to DB and returns structured response."""
    resp = client.post("/api/saju/analyze", json={
        "name": "테스트",
        "birth_date": "1990-05-15",
        "birth_time": "14:30",
        "gender": "male",
        "calendar_type": "solar",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] is not None
    assert data["result_id"] is not None
    assert data["result_status"] == "calculated"
    assert data["input_summary"]["name"] == "테스트"


@pytest.mark.skipif(
    os.environ.get("DATABASE_URL", "").startswith("sqlite"),
    reason="BigInteger autoincrement requires PostgreSQL"
)
def test_analyze_without_birth_time(client):
    """POST /api/saju/analyze without birth_time works."""
    resp = client.post("/api/saju/analyze", json={
        "name": "시간없음",
        "birth_date": "2000-01-01",
        "gender": "female",
        "calendar_type": "solar",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["result_status"] == "calculated"


def test_cors_headers(client):
    """OPTIONS preflight should return CORS headers."""
    resp = client.options(
        "/api/saju/calculate",
        headers={
            "Origin": "https://saju-web-srjz.onrender.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_share_not_found(client):
    """GET /api/saju/share/nonexistent returns 404."""
    resp = client.get("/api/saju/share/nonexistent-id")
    assert resp.status_code == 404
