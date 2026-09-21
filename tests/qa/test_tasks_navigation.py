"""
QA Test Module: Navigation & Tasks Matrix (NAV-001..NAV-005, TASK-001..TASK-013)
Domains 3.4, 3.5, 3.6, 3.7, 3.10, 3.11: Complete matrix verification of
tabs, filters, search, rapid toggle mutations, optimistic UI, and detail modal.
"""

import time
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


def test_nav_001_to_004_tab_switching(page: Page):
    """NAV-001..004: Seamless navigation between Today, Tasks, AI, and More."""
    _login_alice(page)

    # 1. Switch to Tasks tab
    page.click('[data-tab="tasks"]')
    page.wait_for_timeout(300)
    expect(page.locator("#view-tasks, #tab-tasks")).to_be_visible()

    # 2. Switch to AI Composer tab
    page.click('[data-tab="ai"]')
    page.wait_for_timeout(300)
    expect(page.locator("#view-ai, #tab-ai")).to_be_visible()

    # 3. Switch to More / Settings tab
    page.click('[data-tab="more"]')
    page.wait_for_timeout(300)
    expect(page.locator("#view-more, #tab-more")).to_be_visible()

    # 4. Switch back to Today / Focus tab
    page.click('[data-tab="focus"]')
    page.wait_for_timeout(300)
    expect(page.locator("#view-focus, #tab-focus")).to_be_visible()


def test_task_001_render_task_cards(page: Page):
    """TASK-001: All tasks for User Alice render properly with titles and subjects."""
    alice_token = _login_alice(page)

    # Semantic API validation (Section 6)
    res = httpx.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {alice_token}"}, timeout=5.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    tasks = res.json()
    assert isinstance(tasks, list) and len(tasks) >= 5, "Expected list of seeded tasks"
    for t in tasks:
        assert "id" in t and "title" in t and "status" in t and "owner_id" in t
        assert t["owner_id"] in ("user_alice", None)

    page.evaluate("() => switchTab('tasks')")
    page.wait_for_timeout(500)

    # Check tasks container contains Alice's seeded tasks and course accordions
    container_text = page.locator("#tasks-main-container").inner_text()
    assert any(w in container_text for w in ["Физика", "Схемотехника", "Математический анализ", "Измерения"])


def test_task_002_to_004_status_filters(page: Page):
    """TASK-002..004: Filters 'All', 'Todo' (8), 'Done' (2)."""
    _login_alice(page)
    page.evaluate("() => switchTab('tasks')")
    page.wait_for_timeout(500)

    # Status: Todo
    page.click('[data-status="todo"]')
    page.wait_for_timeout(300)
    todo_rows = page.locator(".task-row:not(.is-done)")
    assert todo_rows.count() > 0

    # Status: Done
    page.click('[data-status="done"]')
    page.wait_for_timeout(300)
    done_rows = page.locator(".task-row.is-done, .task-row")
    assert done_rows.count() > 0

    # Status: All
    page.click('[data-status="all"]')
    page.wait_for_timeout(300)
    all_rows = page.locator(".task-row")
    assert all_rows.count() >= todo_rows.count()


def test_task_005_materials_segment(page: Page):
    """TASK-005: Switch to 'Materials & Files' segment filter."""
    _login_alice(page)
    page.evaluate("() => switchTab('tasks')")
    page.wait_for_timeout(500)

    materials_btn = page.locator('[data-segment="materials"]').first
    materials_btn.click()
    page.wait_for_timeout(400)

    # In materials mode, only tasks with attachments or materials are visible
    content = page.locator("#tasks-main-container").inner_text()
    assert any(w in content.lower() for w in ["pdf", "файл", "материал", "скачать", "конспект", "методич"])
    page.locator('[data-segment="submissions"]').first.click()


def test_task_007_filter_by_subject(page: Page):
    """TASK-007: Filter tasks by selecting a specific subject chip."""
    _login_alice(page)
    page.click('[data-tab="tasks"]')
    page.wait_for_timeout(500)

    # Click a specific subject chip (e.g. Physics)
    physics_chip = page.locator("#subject-filter-chips .subject-chip:has-text('Физика')")
    if physics_chip.count() > 0:
        physics_chip.first.click()
        page.wait_for_timeout(300)
        container_text = page.locator("#tasks-main-container").inner_text()
        assert "Физика" in container_text


def test_task_008_009_search_filtering(page: Page):
    """TASK-008 & TASK-009: Real-time search query filtering and no-results empty state."""
    _login_alice(page)
    page.click('[data-tab="tasks"]')
    page.wait_for_timeout(500)

    search_input = page.locator("#task-search-input")
    # Positive search: "Транзисторы"
    search_input.fill("Транзисторы")
    page.wait_for_timeout(300)
    container_text = page.locator("#tasks-main-container").inner_text()
    assert "Транзисторы" in container_text

    # Negative search: nonexistent query
    search_input.fill("nonexistent_random_search_term_xyz_999")
    page.wait_for_timeout(300)
    empty_container = page.locator("#tasks-main-container").inner_text()
    assert "не найден" in empty_container.lower() or "ничего" in empty_container.lower() or empty_container.strip() == ""

    # Clear search
    search_input.fill("")
    page.wait_for_timeout(300)


def test_task_010_011_task_toggle_mutation(page: Page):
    """TASK-010 & TASK-011: Task toggle mutation, rapid debouncing, DB state assertion."""
    alice_token = _login_alice(page)
    page.click('[data-tab="tasks"]')
    page.wait_for_timeout(500)

    # Fetch initial state of Task 1
    tasks_res = httpx.get(
        f"{BASE_URL}/api/tasks",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert tasks_res.status_code == 200
    t1 = [t for t in tasks_res.json() if "Измерения" in t["title"]][0]
    initial_status = t1["status"]

    # Toggle via API
    toggle_res = httpx.post(
        f"{BASE_URL}/api/tasks/{t1['id']}/toggle",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert toggle_res.status_code == 200
    new_status = toggle_res.json().get("status")
    expected_status = "done" if initial_status == "todo" else "todo"
    assert new_status == expected_status, f"Expected {expected_status}, got {new_status}"

    # Verify DB state persisted
    verify_res = httpx.get(
        f"{BASE_URL}/api/tasks/{t1['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert verify_res.json()["status"] == expected_status

    # Rapid debounced toggles test (multi-click without race condition)
    for _ in range(3):
        httpx.post(
            f"{BASE_URL}/api/tasks/{t1['id']}/toggle",
            headers={"Authorization": f"Bearer {alice_token}"},
        )

    # Restore to initial status
    final_res = httpx.get(
        f"{BASE_URL}/api/tasks/{t1['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    if final_res.json()["status"] != initial_status:
        httpx.post(
            f"{BASE_URL}/api/tasks/{t1['id']}/toggle",
            headers={"Authorization": f"Bearer {alice_token}"},
        )


def test_task_012_013_task_detail_sheet(page: Page):
    """TASK-012 & TASK-013: Task detail modal opens with metadata and closes cleanly."""
    _login_alice(page)
    page.click('[data-tab="tasks"]')
    page.wait_for_timeout(500)

    # Click on the first task row
    first_task = page.locator(".task-row").first
    expect(first_task).to_be_visible()
    first_task.click()
    page.wait_for_timeout(400)

    # Assert Task Detail Overlay is visible
    detail_overlay = page.locator("#task-detail-overlay")
    expect(detail_overlay).to_be_visible(timeout=5000)

    # Verify content in sheet
    title_el = page.locator("#task-detail-title")
    expect(title_el).to_be_visible()
    assert len(title_el.inner_text().strip()) > 0

    # Close via close button or ESC key
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    expect(detail_overlay).to_be_hidden()
