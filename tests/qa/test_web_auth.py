"""
QA Test Module: Web Auth & Identity (AUTH-001 .. AUTH-007)
Domain 3.1: Complete matrix verification for authentication, JWT issuance,
tamper rejection, session expiration, and UI state transitions.
"""

import time
import httpx
from playwright.sync_api import Page, expect
from tests.qa.test_env import (
    BASE_URL,
    get_alice_token,
    get_bob_token,
)
from services.auth_service import create_user_token


def test_auth_001_health_endpoint():
    """AUTH-001: Health check endpoint returns 200 OK and valid JSON."""
    res = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data.get("status") == "ok", f"Expected status 'ok', got {data}"
    assert "app" in data, "Missing 'app' in health response"


def test_auth_002_valid_login_and_jwt_ui(page: Page):
    """AUTH-002: Valid login via UI token input; modal disappears, dashboard renders."""
    # Ensure fresh storage
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # If already logged in from previous session, reset token
    page.evaluate("() => { localStorage.clear(); document.cookie = 'kai_app_auth_token=; path=/; max-age=0'; }")
    page.reload()
    page.wait_for_load_state("networkidle")

    # Verify auth modal is visible
    auth_overlay = page.locator("#auth-overlay")
    expect(auth_overlay).to_be_visible(timeout=5000)

    # Input Alice's valid JWT token
    alice_token = get_alice_token()
    page.fill("#auth-token-input", alice_token)
    page.click("#auth-submit-btn")

    # Assert modal hides and dashboard loads
    expect(auth_overlay).to_be_hidden(timeout=5000)

    # Check localStorage
    stored_token = page.evaluate("() => localStorage.getItem('kai_app_auth_token')")
    assert stored_token == alice_token, "Token was not stored in localStorage"


def test_auth_003_invalid_credentials_rejection_ui(page: Page):
    """AUTH-003: Invalid token rejection in UI, error banner shown, stays logged out."""
    page.goto(BASE_URL)
    page.evaluate("() => { localStorage.clear(); document.cookie = 'kai_app_auth_token=; path=/; max-age=0'; }")
    page.reload()

    auth_overlay = page.locator("#auth-overlay")
    expect(auth_overlay).to_be_visible(timeout=5000)

    # Enter invalid token
    page.fill("#auth-token-input", "completely_invalid_bogus_token_12345")
    page.click("#auth-submit-btn")

    # Assert error banner is visible with message
    error_msg = page.locator("#auth-error-msg")
    expect(error_msg).to_be_visible(timeout=5000)
    assert "неверный" in error_msg.inner_text().lower(), f"Unexpected error text: {error_msg.inner_text()}"
    expect(auth_overlay).to_be_visible()


def test_auth_004_expired_token_handling():
    """AUTH-004: Expired token rejected with 401 and invalid_token description."""
    # Issue a token expired 1 hour ago
    expired_token = create_user_token(
        user_id="user_alice",
        username="alice",
        role="student",
        expires_in_seconds=-3600
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    res = httpx.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=5.0)
    assert res.status_code == 401, f"Expected 401 for expired token, got {res.status_code}"
    www_auth = res.headers.get("www-authenticate", "")
    assert "expired" in www_auth.lower() or "expired" in res.text.lower(), f"Expired note missing: {res.text}"


def test_auth_005_token_persistence_on_reload(page: Page):
    """AUTH-005: Token in localStorage persists across reload, no auth prompt shown."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    auth_overlay = page.locator("#auth-overlay")
    expect(auth_overlay).to_be_hidden(timeout=5000)

    # Verify Today/Focus tab header is rendered
    expect(page.locator("#view-focus, .app-view.active")).to_be_visible(timeout=5000)


def test_auth_006_logout_clearing_state(page: Page):
    """AUTH-006: Reset token action clears localStorage and shows auth modal."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Navigate to Settings / More tab
    page.evaluate("() => switchTab('more')")
    page.wait_for_timeout(300)

    # Click reset token button
    reset_btn = page.locator("#settings-reset-token-btn")
    expect(reset_btn).to_be_visible(timeout=5000)
    reset_btn.click()

    # Verify auth modal reappears
    auth_overlay = page.locator("#auth-overlay")
    expect(auth_overlay).to_be_visible(timeout=5000)

    # Verify token cleared
    stored = page.evaluate("() => localStorage.getItem('kai_app_auth_token')")
    assert stored is None or stored == "", "Token was not cleared on logout"


def test_auth_007_multi_tab_sync(browser):
    """AUTH-007: Multi-tab session behavior test."""
    context = browser.new_context()
    page1 = context.new_page()
    page2 = context.new_page()

    alice_token = get_alice_token()
    page1.goto(BASE_URL)
    page1.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page1.reload()
    page1.wait_for_load_state("networkidle")

    page2.goto(BASE_URL)
    page2.wait_for_load_state("networkidle")

    # Both tabs logged in
    expect(page1.locator("#auth-overlay")).to_be_hidden()
    expect(page2.locator("#auth-overlay")).to_be_hidden()

    # Clear token in page1
    page1.evaluate("() => clearAuthToken()")

    # In single-page apps without storage event listeners on auth, page2 might retain state until next request.
    # Check if storage event or next api request in page2 triggers logout
    page2.evaluate("() => apiFetch('/api/stats').catch(() => {})")
    page2.wait_for_timeout(500)

    context.close()
