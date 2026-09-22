"""
Script to capture all fresh screenshots for KAI Student OS 2.0 with the new AI Studio Floating Capsule.
Generates pixel-perfect 412x915 screenshots in docs/screenshots/ and repo root.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.async_api import async_playwright
from tests.qa.test_env import (
    BASE_URL,
    get_alice_token,
    setup_test_environment,
    teardown_test_environment,
)

async def capture_all():
    alice_token = get_alice_token()
    print("Test environment running. Alice token generated.")

    docs_dir = REPO_ROOT / "docs" / "screenshots"
    docs_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=1,
            color_scheme="dark",
        )
        page = await context.new_page()

        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL)
        await page.evaluate(f"token => localStorage.setItem('kai_app_auth_token', '{alice_token}')")
        await page.evaluate("localStorage.setItem('kai_theme', 'dark')")
        await page.reload()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        # 1. Hero Dashboard (Focus Tab)
        print("Capturing 1. hero_dashboard.png...")
        await page.locator('.dock-tab[data-tab="focus"]').click()
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(docs_dir / "hero_dashboard.png"))
        await page.screenshot(path=str(REPO_ROOT / "screen_focus.png"))

        # 2. AI Studio (Capsule & Conversation)
        print("Capturing 2. gemini_assistant.png (Google AI Studio)...")
        await page.locator('.dock-tab[data-tab="ai"]').click()
        await page.wait_for_timeout(500)
        # Ensure input is blurred so mobile dock is beautifully visible
        await page.evaluate("document.activeElement && document.activeElement.blur(); document.body.classList.remove('keyboard-active');")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(docs_dir / "gemini_assistant.png"))

        # 3. AI Task Parsed Preview Sheet
        print("Capturing 3. gemini_task_parsed.png (Parsed Task Preview Sheet)...")
        textarea = page.locator("#gemini-text-input")
        await textarea.fill("Лабораторная по физике: Оптика. Сдать в следующую пятницу.")
        await page.wait_for_timeout(300)
        # Click "В задачи" button
        await page.locator("#gemini-submit-btn").click()
        # Wait for preview sheet
        await page.wait_for_selector("#ai-preview-sheet", state="visible", timeout=5000)
        await page.evaluate("document.activeElement && document.activeElement.blur(); document.body.classList.remove('keyboard-active');")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(docs_dir / "gemini_task_parsed.png"))

        # Close preview sheet and dismiss any toast
        cancel_btn = page.locator("#sheet-cancel-btn")
        if await cancel_btn.is_visible():
            await cancel_btn.click()
            await page.wait_for_timeout(400)
        await page.evaluate("const t = document.getElementById('toast'); if(t){ t.className = 'liquid-toast glass-floating'; t.style.display = 'none'; }")

        # 4. Lab Summary Cheat Sheet Modal
        print("Capturing 4. gemini_lab_cheat_sheet.png (Lab Cheat Sheet)...")
        # Trigger openLabSummaryModal(1) directly
        await page.evaluate("window.openLabSummaryModal && window.openLabSummaryModal(1)")
        try:
            await page.wait_for_selector("#lab-summary-overlay.active", state="visible", timeout=6000)
            # Ensure no lingering toast
            await page.evaluate("const t = document.getElementById('toast'); if(t){ t.style.display = 'none'; }")
            await page.wait_for_timeout(800)
            await page.screenshot(path=str(docs_dir / "gemini_lab_cheat_sheet.png"))
        except Exception as e:
            print("Warning on lab summary modal capture:", e)

        # Close lab summary
        close_lab_btn = page.locator("#lab-summary-close-btn")
        if await close_lab_btn.is_visible():
            await close_lab_btn.click()
            await page.wait_for_timeout(400)

        # 5. Full Schedule Timeline (in 'more' tab)
        print("Capturing 5. schedule_timeline.png (Full Schedule Timeline)...")
        await page.locator('.dock-tab[data-tab="more"]').click()
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(docs_dir / "schedule_timeline.png"))
        await page.screenshot(path=str(REPO_ROOT / "screen_schedule.png"))

        # 6. Tasks Submissions (Tasks tab -> Submissions)
        print("Capturing 6. tasks_submissions.png (Tasks Submissions)...")
        await page.locator('.dock-tab[data-tab="tasks"]').click()
        await page.wait_for_timeout(500)
        # Ensure submissions subtab is active
        sub_tab = page.locator("#tab-btn-submissions")
        if await sub_tab.is_visible():
            await sub_tab.click()
            await page.wait_for_timeout(400)
        await page.screenshot(path=str(docs_dir / "tasks_submissions.png"))
        await page.screenshot(path=str(REPO_ROOT / "screen_tasks.png"))
        await page.screenshot(path=str(REPO_ROOT / "screen_tasks_submissions.png"))

        # 7. Tasks Materials (Tasks tab -> Materials)
        print("Capturing 7. tasks_materials.png (Tasks Materials Library)...")
        mat_tab = page.locator("#tab-btn-materials")
        if await mat_tab.is_visible():
            await mat_tab.click()
            await page.wait_for_timeout(500)
        # Click "Физика" chip to showcase real manual attachment
        phys_chip = page.locator(".course-chip:has-text('Физика')")
        if await phys_chip.is_visible():
            await phys_chip.click()
            await page.wait_for_timeout(400)
        await page.screenshot(path=str(docs_dir / "tasks_materials.png"))
        await page.screenshot(path=str(REPO_ROOT / "screen_tasks_materials.png"))

        await browser.close()
        print("Browser closed.")

def main():
    print("Setting up isolated test environment on port 8899...")
    setup_test_environment(mode="local")
    try:
        asyncio.run(capture_all())
    finally:
        teardown_test_environment(keep_data=False)
        print("Test environment teardown complete.")

if __name__ == "__main__":
    main()
