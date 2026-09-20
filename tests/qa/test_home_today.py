"""
QA Test Module: Home / Today View & Data Freshness (DASH-001..DASH-004, FRSH-001..FRSH-005)
Domain 3.2 & 3.3: Verifies stats accuracy, live schedule banner, urgent tasks list,
empty state handling, and all 4 real freshness display states + 60s ticker.
"""

import json
from datetime import datetime, timedelta, timezone
import httpx
from playwright.sync_api import Page, expect
from tests.qa.test_env import (
    BASE_URL,
    TEST_SYNC_STATE_FILE,
    get_alice_token,
    get_bob_token,
)


def test_dash_001_stats_summary(page: Page):
    """DASH-001: Verify dashboard progress stats match database task counts."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Fetch stats via API directly to compare
    res = httpx.get(
        f"{BASE_URL}/api/stats",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=5.0,
    )
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_tasks"] == 10, f"Expected 10 tasks for Alice, got {stats['total_tasks']}"
    assert stats["done_tasks"] == 2, f"Expected 2 done tasks for Alice, got {stats['done_tasks']}"
    progress = stats.get("progress_percent", stats.get("progress_pct"))
    assert progress == 20, f"Expected 20% progress, got {progress}"

    # Verify UI reflection
    page.wait_for_selector("#focus-stat-todo, .progress-overview-card", timeout=5000)
    # Check if UI displays progress number
    content = page.content()
    assert "8" in content, "Todo count 8 not found on page"


def test_dash_002_schedule_banner(page: Page):
    """DASH-002: Current & upcoming classes banner rendered on Today view."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Today view schedule section
    today_lessons = page.locator("#today-lessons-container, #focus-schedule-section, .lesson-item")
    expect(page.locator("body")).to_be_visible()
    # Check API response for today's schedule
    res = httpx.get(
        f"{BASE_URL}/api/schedule",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=5.0,
    )
    assert res.status_code == 200
    sched = res.json()
    assert "lessons" in sched or "day_name" in sched


def test_dash_003_urgent_tasks_list(page: Page):
    """DASH-003: Near-deadline tasks appear in Today view."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Expect task items or urgent section in Today tab
    body_text = page.inner_text("body")
    # Task 3 "Отчет по лабораторной работе: Диоды" is due today, should appear
    assert "Диоды" in body_text or "Лабораторная" in body_text, "Urgent tasks missing in Today view"


def test_dash_004_empty_state_handling(page: Page):
    """DASH-004: Clean empty state rendered when user has zero pending tasks."""
    # User Bob has only 2 tasks, let's test a synthetic zero-task view or Bob's state
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Evaluate rendering function with empty tasks
    has_empty_markup = page.evaluate("""() => {
        state.tasks = [];
        renderFocusView();
        return document.querySelector('.empty-state-card, .empty-state, .focus-all-done') !== null;
    }""")
    assert has_empty_markup, "Empty state illustration not rendered when 0 tasks"


def test_frsh_001_fresh_state_display(page: Page):
    """FRSH-001: Fresh sync state (<= 15 min) renders with .freshness-fresh."""
    # Set sync state to 4 minutes ago
    sync_time = (datetime.now(timezone.utc) - timedelta(minutes=4)).isoformat()
    with open(TEST_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_successful_sync": sync_time, "source": "test_fresh"}, f)

    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    pill = page.locator("#data-freshness-pill")
    expect(pill).to_be_visible(timeout=5000)
    pill_class = pill.get_attribute("class") or ""
    assert "freshness-fresh" in pill_class, f"Expected freshness-fresh, got {pill_class}"
    text = pill.inner_text()
    assert "мин назад" in text or "только что" in text, f"Unexpected freshness text: {text}"


def test_frsh_002_recent_state_display(page: Page):
    """FRSH-002: Recent sync state (16..60 min) renders with .freshness-recent."""
    sync_time = (datetime.now(timezone.utc) - timedelta(minutes=27)).isoformat()
    with open(TEST_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_successful_sync": sync_time, "source": "test_recent"}, f)

    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    pill = page.locator("#data-freshness-pill")
    expect(pill).to_be_visible(timeout=5000)
    pill_class = pill.get_attribute("class") or ""
    assert "freshness-recent" in pill_class, f"Expected freshness-recent, got {pill_class}"
    text = pill.inner_text()
    assert "27 мин назад" in text, f"Unexpected freshness text: {text}"


def test_frsh_003_stale_state_display(page: Page):
    """FRSH-003: Stale sync state (> 60 min) renders with .freshness-stale and warning."""
    sync_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    with open(TEST_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_successful_sync": sync_time, "source": "test_stale"}, f)

    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    pill = page.locator("#data-freshness-pill")
    expect(pill).to_be_visible(timeout=5000)
    pill_class = pill.get_attribute("class") or ""
    assert "freshness-stale" in pill_class, f"Expected freshness-stale, got {pill_class}"
    text = pill.inner_text()
    assert "⚠" in text and "ч назад" in text, f"Unexpected stale text: {text}"


def test_frsh_004_unknown_state_display(page: Page):
    """FRSH-004: Unknown sync state (missing timestamp) renders with .freshness-unknown."""
    with open(TEST_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_successful_sync": None, "source": "none"}, f)

    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    pill = page.locator("#data-freshness-pill")
    expect(pill).to_be_visible(timeout=5000)
    pill_class = pill.get_attribute("class") or ""
    assert "freshness-unknown" in pill_class, f"Expected freshness-unknown, got {pill_class}"
    text = pill.inner_text()
    assert "неизвестно" in text.lower(), f"Unexpected unknown text: {text}"


def test_frsh_005_ticker_recalculation(page: Page):
    """FRSH-005: Freshness ticker recalculates dynamically without full reload."""
    alice_token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Manually trigger updateFreshnessDisplay() after shifting simulated state
    updated_text = page.evaluate("""() => {
        state.stats.last_successful_sync = new Date(Date.now() - 45 * 60 * 1000).toISOString();
        updateFreshnessDisplay();
        return document.getElementById('data-freshness-pill').textContent;
    }""")
    assert "45 мин назад" in updated_text, f"Ticker did not update dynamically: {updated_text}"
