"""
Sprint 6 Security Hardening & AI Pipeline Tests.
Validates:
- 401 Unauthorized for unprotected requests across all /api/* endpoints
- 200 OK for requests authenticated via:
    * Authorization: Bearer <token>
    * X-App-Token: <token>
- 401 Unauthorized for query parameter ?token=<token> (tokens strictly forbidden in URLs)
- 401 Unauthorized for invalid tokens
- Public access for /api/health and static assets
- File download protection (/api/tasks/{id}/download)
- Date resolver (resolve_relative_deadline) with European/Moscow timezone
- Task creation via POST /api/tasks with parsed deadline datetime
"""

import asyncio
from datetime import datetime
from fastapi.testclient import TestClient

from api.app import app
from core.config import settings
from database.connection import init_db
from services.gemini_service import resolve_relative_deadline, MSK_TZ


def setup_database():
    asyncio.run(init_db())


def get_client():
    return TestClient(app)


def get_auth_headers():
    token = settings.app_auth_token or "kai5108_secret_passcode_2026"
    return {"Authorization": f"Bearer {token}"}


def get_x_token_headers():
    token = settings.app_auth_token or "kai5108_secret_passcode_2026"
    return {"X-App-Token": token}
    return {"X-App-Token": token}


def test_public_health_and_static(client):
    """Verify health check and static endpoints are accessible without authentication."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp_root = client.get("/")
    assert resp_root.status_code == 200

    resp_manifest = client.get("/manifest.json")
    assert resp_manifest.status_code == 200


def test_protected_endpoints_reject_unauthorized(client):
    """Verify all protected /api/* endpoints return 401 Unauthorized when no token is supplied."""
    endpoints = [
        ("GET", "/api/stats"),
        ("GET", "/api/subjects"),
        ("GET", "/api/tasks"),
        ("GET", "/api/tasks/1/download"),
        ("POST", "/api/tasks/1/toggle"),
        ("GET", "/api/schedule"),
        ("GET", "/api/schedule/week"),
        ("POST", "/api/sync-bb"),
        ("POST", "/api/ai/parse-task"),
        ("POST", "/api/tasks"),
        ("POST", "/api/ai/summarize-task/1"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} should return 401 Unauthorized, got {resp.status_code}"
        assert "WWW-Authenticate" in resp.headers


def test_protected_endpoints_reject_invalid_token(client):
    """Verify endpoints reject invalid token with 401."""
    bad_headers = {"Authorization": "Bearer wrong_invalid_secret_token_123"}
    resp = client.get("/api/stats", headers=bad_headers)
    assert resp.status_code == 401

    bad_x_headers = {"X-App-Token": "bad_token"}
    resp_x = client.get("/api/stats", headers=bad_x_headers)
    assert resp_x.status_code == 401

    resp_q = client.get("/api/stats?token=invalid_query_token")
    assert resp_q.status_code == 401


def test_auth_via_bearer_header(client, auth_headers):
    """Verify access granted with valid Authorization: Bearer token."""
    resp = client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    assert "total_tasks" in resp.json()

    resp_tasks = client.get("/api/tasks", headers=auth_headers)
    assert resp_tasks.status_code == 200
    assert isinstance(resp_tasks.json(), list)


def test_auth_via_x_app_token_header(client, x_token_headers):
    """Verify access granted with valid X-App-Token header."""
    resp = client.get("/api/stats", headers=x_token_headers)
    assert resp.status_code == 200
    assert "total_tasks" in resp.json()


def test_auth_via_query_token_strictly_rejected(client):
    """Verify ?token=<token> is strictly rejected (401) to prevent tokens leaking in URLs."""
    token = settings.app_auth_token or "kai5108_secret_passcode_2026"

    # Query without token should fail with 401
    resp_no_token = client.get("/api/tasks/1/download")
    assert resp_no_token.status_code == 401

    # Query with valid token in query params must be strictly rejected with 401
    resp_with_token = client.get(f"/api/tasks/1/download?token={token}")
    assert resp_with_token.status_code == 401, f"Expected 401 for ?token= query parameter, got {resp_with_token.status_code}"


def test_date_resolver_relative_phrases():
    """Verify resolve_relative_deadline converts Russian relative phrases to Moscow timezone datetimes."""
    base_wed = datetime(2026, 9, 16, 12, 0, tzinfo=MSK_TZ)

    # 1. 'к следующей среде' -> Wednesday next week at 18:00
    res_wed = resolve_relative_deadline('к следующей среде', base_dt=base_wed)
    assert res_wed is not None
    assert res_wed.year == 2026
    assert res_wed.month == 9
    assert res_wed.day == 23
    assert res_wed.hour == 18
    assert res_wed.minute == 0

    # 2. 'до пятницы' -> upcoming Friday at 18:00
    res_fri = resolve_relative_deadline('до пятницы', base_dt=base_wed)
    assert res_fri is not None
    assert res_fri.day == 18
    assert res_fri.hour == 18

    # 3. 'завтра' -> tomorrow at 23:59
    res_tmrw = resolve_relative_deadline('завтра', base_dt=base_wed)
    assert res_tmrw is not None
    assert res_tmrw.day == 17
    assert res_tmrw.hour == 23
    assert res_tmrw.minute == 59

    # 4. 'через 2 дня' -> base + 2 days at 18:00
    res_2d = resolve_relative_deadline('через 2 дня', base_dt=base_wed)
    assert res_2d is not None
    assert res_2d.day == 18
    assert res_2d.hour == 18

    # 5. 'до 25 октября' -> 25th of October
    res_date = resolve_relative_deadline('до 25 октября', base_dt=base_wed)
    assert res_date is not None
    assert res_date.month == 10
    assert res_date.day == 25
    assert res_date.hour == 18

    # 6. Empty / none
    assert resolve_relative_deadline(None) is None
    assert resolve_relative_deadline('') is None


def test_task_creation_with_parsed_deadline(client, auth_headers):
    """Verify POST /api/tasks persists task with calculated deadline datetime."""
    task_payload = {
        "subject_name": "Тестовая Дисциплина 5108",
        "title": "Лабораторная работа по микроэлектронике №1",
        "task_type": "лабораторная",
        "deadline_raw": "до пятницы",
        "requirements": "Титульный лист и протокол измерений",
        "source": "manual_ai"
    }

    resp = client.post("/api/tasks", json=task_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] > 0
    assert data["subject_name"] == "Тестовая Дисциплина 5108"
    assert data["title"] == "Лабораторная работа по микроэлектронике №1"
    assert data["task_type"] == "лабораторная"
    assert data["status"] == "todo"
    assert data["deadline"] is not None
    assert "T" in data["deadline"]
    assert "⏰ Срок: до пятницы" in data["details"]
    assert "📝 Требования: Титульный лист" in data["details"]


if __name__ == "__main__":
    setup_database()
    c = get_client()
    print("Testing public health and static...")
    test_public_health_and_static(c)
    print("Testing protected endpoints reject unauthorized (401)...")
    test_protected_endpoints_reject_unauthorized(c)
    print("Testing protected endpoints reject invalid token (401)...")
    test_protected_endpoints_reject_invalid_token(c)
    print("Testing auth via Bearer header (200)...")
    test_auth_via_bearer_header(c, get_auth_headers())
    print("Testing auth via X-App-Token header (200)...")
    test_auth_via_x_app_token_header(c, get_x_token_headers())
    print("Testing auth via query token ?token= strictly rejected (401)...")
    test_auth_via_query_token_strictly_rejected(c)
    print("Testing date resolver relative phrases...")
    test_date_resolver_relative_phrases()
    print("Testing task creation with parsed deadline datetime...")
    test_task_creation_with_parsed_deadline(c, get_auth_headers())
    print("\n[SUCCESS] ALL SPRINT 6 SECURITY & AI PIPELINE TESTS PASSED SUCCESSFULLY!")