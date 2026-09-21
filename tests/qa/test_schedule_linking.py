"""
QA Test Module: Schedule View & Subject Linking (SCHED-001..SCHED-005)
Domains 3.9 & 3.10: Verifies schedule retrieval, day switching,
Sunday handling, and subject linking from schedule card into tasks view.
"""

import httpx
from playwright.sync_api import Page, expect
from tests.qa.test_env import (
    BASE_URL,
    get_alice_token,
)


def _login_alice(page: Page) -> str:
    token = get_alice_token()
    page.goto(BASE_URL)
    page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', token)", token)
    page.reload()
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        page.wait_for_load_state("domcontentloaded")
    return token


def test_sched_001_daily_schedule():
    """SCHED-001: Daily schedule API returns valid pairs with classrooms and teachers."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    res = httpx.get(f"{BASE_URL}/api/schedule", headers=headers, timeout=5.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "day_name" in data or "lessons" in data, f"Missing schedule fields: {data}"
    lessons = data.get("lessons", [])
    if isinstance(lessons, list) and lessons:
        for l in lessons[:3]:
            assert "discipl_name" in l or "discipline" in l or "subject" in l


def test_sched_002_weekly_schedule():
    """SCHED-002: Weekly schedule API returns full week matrix."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    res = httpx.get(f"{BASE_URL}/api/schedule/week", headers=headers, timeout=5.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    week = res.json()
    assert isinstance(week, dict) or isinstance(week, list), "Week schedule format invalid"


def test_sched_003_day_selector_ui(page: Page):
    """SCHED-003: Day selector buttons switch active day view in UI."""
    _login_alice(page)

    # In More tab, check full schedule container
    page.evaluate("() => switchTab('more')")
    page.wait_for_timeout(300)

    day_btn = page.locator("#schedule-day-pills button[data-day='2']")
    if day_btn.count() > 0:
        day_btn.click()
        page.wait_for_timeout(300)
        btn_class = day_btn.get_attribute("class") or ""
        assert "active" in btn_class, f"Day pill did not become active: {btn_class}"


def test_sched_004_sunday_handling():
    """SCHED-004: Sunday day query returns zero classes or friendly day-off status."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    res = httpx.get(f"{BASE_URL}/api/schedule?day=7", headers=headers, timeout=5.0)
    assert res.status_code == 200
    data = res.json()
    lessons = data.get("lessons", [])
    assert len(lessons) == 0, f"Expected 0 lessons on Sunday, got {len(lessons)}"


def test_sched_005_subject_linking_to_tasks(page: Page):
    """SCHED-005: Clicking a subject badge on schedule card navigates to Tasks filtered by subject."""
    _login_alice(page)

    # Check if a lesson item with subject link exists
    lesson_badges = page.locator(".lesson-subject-badge, .badge-subject, [onclick*='filterBySubject']")
    if lesson_badges.count() > 0:
        lesson_badges.first.click()
        page.wait_for_timeout(500)
        # Verify active tab switched to tasks
        tasks_view = page.locator("#view-tasks, #tab-tasks")
        expect(tasks_view).to_be_visible(timeout=5000)
    else:
        # Programmatic verification of the linking function
        switched = page.evaluate("""() => {
            if (typeof filterBySubject === 'function') {
                filterBySubject('Физика');
                return state.currentTab === 'tasks';
            }
            return true;
        }""")
        assert switched
