import asyncio
import os
import json
import time
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\karim\.gemini\antigravity\brain\c206c1c6-370f-43e1-9669-a3b6efc39dfd\scratch\qa_journey_fixed"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def run_journey():
    metrics = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Standard iPhone 14 / modern viewport
        context = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await context.new_page()
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGEERROR: {err}"))

        # Step 1: Open app in the morning
        t0 = time.time()
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")
        load_time = round((time.time() - t0) * 1000)

        # Check if auth modal appeared
        auth_visible = await page.is_visible("#auth-overlay")
        print(f"Step 1: Opened app. Auth modal visible: {auth_visible}. Load time: {load_time}ms")

        # If auth modal is visible, enter token
        clicks_step1 = 0
        if auth_visible:
            await page.fill("#auth-token-input", "kai5108_secret_passcode_2026")
            await page.click("#auth-submit-btn")
            clicks_step1 = 2
            await page.wait_for_selector("#auth-overlay", state="hidden")
            # Wait for data to finish loading into DOM
            await page.wait_for_selector(".urgent-task-item, .empty-state-card", timeout=10000)
            await page.wait_for_function("() => !document.getElementById('next-action-title').textContent.includes('Загрузка')", timeout=10000)
            await page.wait_for_timeout(300)

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step1_open_app.png"))

        greeting = await page.text_content("h1.intro-greeting")
        date_str = await page.text_content("#focus-date-label")
        print(f"Greeting: {greeting.strip()}, Date: {date_str.strip()}")

        # Step 2: Understand what the first pair is
        hero_status = await page.text_content("#hero-status-text")
        hero_title = await page.text_content("#hero-lesson-title")
        hero_building = await page.text_content("#hero-building-chip")
        hero_teacher = await page.text_content("#hero-teacher-text")
        today_peek = await page.text_content("#today-peek-container")
        print(f"Step 2 (First pair): Hero status='{hero_status}', Title='{hero_title}', Bldg='{hero_building}', Teacher='{hero_teacher}'")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step2_first_pair.png"))

        # Step 3: Understand what needs to be done today
        next_action_title = await page.text_content("#next-action-title")
        next_action_time = await page.text_content("#next-action-time")
        urgent_tasks = await page.text_content("#urgent-tasks-container")
        print(f"Step 3 (Tasks today): Next action='{next_action_title}', Time='{next_action_time}'")
        print(f"Urgent tasks snippet: {urgent_tasks[:100]}...")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step3_tasks_today.png"))

        # Step 4: Open the nearest task
        # Click on next action button or first urgent task
        task_sheet_open = False
        clicks_step4 = 0
        next_btn = await page.query_selector("#next-action-btn")
        if next_btn and await next_btn.is_visible():
            await next_btn.click()
            clicks_step4 = 1
        else:
            first_urgent = await page.query_selector(".urgent-task-item")
            if first_urgent:
                await first_urgent.click()
                clicks_step4 = 1

        await page.wait_for_timeout(400)
        sheet_active = await page.is_visible("#task-detail-overlay.active")
        task_title = await page.text_content("#task-detail-title")
        task_subj = await page.text_content("#task-detail-subject")
        task_status = await page.text_content("#task-detail-status")
        print(f"Step 4 (Open nearest task): Sheet active={sheet_active}, Title='{task_title}', Subj='{task_subj}', Status='{task_status}'")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step4_open_task.png"))

        # Step 5: Find методичка
        files_visible = await page.is_visible("#task-detail-files-box")
        files_text = await page.text_content("#task-detail-files-list") if files_visible else "None (Box Hidden)"
        print(f"Step 5 (Find методичка): Files box visible={files_visible}, Files content='{files_text}'")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step5_metodichka.png"))

        # Step 6: Understand deadline
        deadline_text = await page.text_content("#task-detail-deadline")
        print(f"Step 6 (Deadline): Deadline display='{deadline_text.strip()}'")

        # Step 7: Mark progress
        clicks_step7 = 1
        prev_status = await page.text_content("#task-detail-status")
        await page.click("#task-detail-toggle-btn")
        await page.wait_for_timeout(600)
        new_status = await page.text_content("#task-detail-status")
        toast_text = await page.text_content("#toast") if await page.is_visible("#toast") else ""
        print(f"Step 7 (Mark progress): Prev status='{prev_status}', New status='{new_status}', Toast='{toast_text}'")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step7_mark_progress.png"))

        # Close task sheet
        await page.click("#task-detail-close-btn")
        await page.wait_for_timeout(300)

        # Step 8: Open AI
        # Click dock tab AI
        clicks_step8 = 1
        await page.click("button.dock-tab[data-tab='ai']")
        await page.wait_for_timeout(300)
        ai_tab_visible = await page.is_visible("#view-ai.active")
        print(f"Step 8 (Open AI): AI tab active={ai_tab_visible}")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step8_open_ai.png"))

        # Step 9: Paste message from староста
        starosta_msg = "К следующей среде по физике сделать отчет по лабе 2 и распечатать титульник в 301 аудитории"
        await page.fill("#gemini-text-input", starosta_msg)
        clicks_step9 = 1 # tap input and paste
        await page.click("#gemini-submit-btn")
        clicks_step9 += 1
        print(f"Step 9 (Paste message): Submitted message to Gemini parser")

        # Step 10: View AI interpretation
        # Wait for shimmer to disappear and result to appear
        t_ai_start = time.time()
        await page.wait_for_selector("#gemini-result-card .ai-preview-sheet, #gemini-result-card .ai-fallback-box", timeout=15000)
        ai_duration = round((time.time() - t_ai_start) * 1000)
        preview_text = await page.text_content("#gemini-result-card")
        print(f"Step 10 (View interpretation in {ai_duration}ms): Preview text={preview_text[:200]}...")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step10_ai_preview.png"))

        # Step 11: Confirm changes
        clicks_step11 = 1
        confirm_btn = await page.query_selector("#sheet-confirm-btn")
        if confirm_btn:
            await confirm_btn.click()
            await page.wait_for_timeout(800)
            success_visible = await page.is_visible(".ai-success-sheet")
            success_text = await page.text_content(".ai-success-sheet") if success_visible else ""
            print(f"Step 11 (Confirm changes): Success sheet visible={success_visible}, Text='{success_text.strip()}'")
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step11_confirm.png"))
        else:
            print("Step 11: Confirm button not found (fallback or error occurred)")

        # Step 12: Return to Today via new CTA button (or fallback to dock)
        clicks_step12 = 1
        goto_btn = await page.query_selector(".success-goto-btn")
        if goto_btn and await goto_btn.is_visible():
            await goto_btn.click()
            print("Step 12: Clicked .success-goto-btn")
        else:
            await page.click("button.dock-tab[data-tab='focus']")
            print("Step 12: Clicked dock tab focus")
        await page.wait_for_timeout(500)
        focus_active = await page.is_visible("#view-focus.active")
        print(f"Step 12 (Return to Today): Focus view active={focus_active}")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step12_back_today.png"))

        # Step 13: Understand next step
        new_next_action = await page.text_content("#next-action-title")
        new_next_time = await page.text_content("#next-action-time")
        new_urgent = await page.text_content("#urgent-tasks-container")
        print(f"Step 13 (Next step): Next action='{new_next_action}', Time='{new_next_time}'")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step13_next_step.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_journey())
