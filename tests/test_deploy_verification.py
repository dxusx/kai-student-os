"""
Tests for Deployment Verification & Version Endpoint (GET /api/version)
and Hardened Cookie Authentication & Service Auth Scoping.
"""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from core.config import settings
from core.version import get_version_payload, resolve_git_info
from services.auth_service import create_user_token


@pytest.fixture
def client():
    return TestClient(app)


def test_api_version_endpoint(client):
    """GET /api/version must return commit metadata, version info, and security spec."""
    resp = client.get("/api/version")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("app") == "KAI Student OS"
    assert data.get("version") == "2.0.0"
    assert data.get("release_stage") == "beta"

    # Git metadata
    git_sha = data.get("git_commit")
    git_short = data.get("git_commit_short")
    assert git_sha and len(git_sha) >= 7
    assert git_short == git_sha[:7]
    assert "git_branch" in data

    # Hardened Session Auth specification
    session_auth = data.get("session_auth", {})
    assert session_auth.get("type") == "cookie"
    assert session_auth.get("cookie_name") == "kai_app_auth_token"
    assert session_auth.get("httponly") is True
    assert session_auth.get("samesite") == "lax"
    assert session_auth.get("secure") is True

    # Scoped Service Auth specification
    service_auth = data.get("service_auth", {})
    assert service_auth.get("header") == "X-App-Token"
    assert service_auth.get("scope") == "internal_only"


def test_auth_login_sets_httponly_cookie(client):
    """POST /api/auth/login must set HttpOnly SameSite=Lax session cookie."""
    # Test login via app passcode
    passcode = settings.app_auth_token or "secret"
    resp = client.post("/api/auth/login", json={"token": passcode})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "user" in data

    # Check Set-Cookie response header
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "kai_app_auth_token=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


def test_auth_login_with_jwt_user_token(client):
    """POST /api/auth/login with signed user JWT sets cookie for that user."""
    user_token = create_user_token(user_id="user_alice", username="alice", role="student")
    resp = client.post("/api/auth/login", json={"token": user_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["id"] == "user_alice"

    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "kai_app_auth_token=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()


def test_auth_login_invalid_credentials_rejected(client):
    """POST /api/auth/login with invalid token must return 401."""
    resp = client.post("/api/auth/login", json={"token": "invalid_fake_key_999"})
    assert resp.status_code == 401
    assert "неверный" in resp.json()["detail"].lower()


def test_auth_logout_clears_cookie(client):
    """POST /api/auth/logout must clear the session cookie."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "kai_app_auth_token=" in set_cookie_header
    # Either max-age=0 or expires in past
    assert "max-age=0" in set_cookie_header.lower() or "expires=" in set_cookie_header.lower()


def test_service_auth_header_isolation(client):
    """X-App-Token is accepted for service auth, but rejects user impersonation."""
    app_token = settings.app_auth_token or "secret"

    # Valid service auth without spoofing
    resp_svc = client.get("/api/stats", headers={"X-App-Token": app_token})
    assert resp_svc.status_code == 200

    # Service auth attempting to impersonate another student without user JWT -> 403 Forbidden
    resp_spoof = client.get("/api/stats", headers={"X-App-Token": app_token, "X-User-Id": "impersonated_victim"})
    assert resp_spoof.status_code == 403
    assert "запрещен" in resp_spoof.json()["detail"].lower()


def test_git_info_resolver():
    """Verify resolve_git_info retrieves valid repo commit data."""
    info = resolve_git_info()
    assert "git_commit" in info
    assert "git_commit_short" in info
    assert len(info["git_commit_short"]) <= 7
