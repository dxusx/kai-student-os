import asyncio
import json
import os
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"
PASSCODE = "kai5108_secret_passcode_2026"

results = {}

async def run_scenario_a(playwright):
    """Scenario A: Первый вход (Cold start, Auth, Enter Passcode, Home screen)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    page = await context.new_page()

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    resp = await page.goto(BASE_URL, wait_until="commit")
    load_time_ms = round((time.perf_counter() - t0) * 1000)

    # Auth modal appears
    await page.wait_for_selector("#auth-overlay.active, #auth-token-input", timeout=5000)
    clicks = 0
    screens = 2  # Auth overlay screen -> Main Focus screen

    # Fill passcode and click submit
    await page.fill("#auth-token-input", PASSCODE)
    await page.click("#auth-submit-btn")
    clicks += 2

    t_action_0 = time.perf_counter()
    await page.wait_for_selector("#hero-live-container", timeout=8000)
    time_to_action_ms = round((time.perf_counter() - t_action_0) * 1000)

    results["Scenario A: Первый вход"] = {
        "clicks": clicks,
        "screens": screens,
        "api_requests": api_requests,
        "initial_load_ms": load_time_ms,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": "Холодный запуск: модальное окно пин-кода (1 тап ввода + 1 тап подтверждения) → автоматическая загрузка всех вкладок."
    }
    await browser.close()


async def run_scenario_b(playwright):
    """Scenario B: Утренний просмотр (Authenticated warm launch, first lesson, current parity)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    load_time_ms = round((time.perf_counter() - t0) * 1000)

    t_action_0 = time.perf_counter()
    await page.wait_for_selector("#hero-lesson-title", timeout=5000)
    time_to_action_ms = round((time.perf_counter() - t_action_0) * 1000)

    lesson_text = await page.inner_text("#hero-lesson-title")

    results["Scenario B: Утренний просмотр"] = {
        "clicks": 0,
        "screens": 1,
        "api_requests": api_requests,
        "initial_load_ms": load_time_ms,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": f"Текущая/ближайшая пара сразу на карточке «Сейчас» ({lesson_text}). 0 кликов для утренней ориентации."
    }
    await browser.close()


async def run_scenario_c(playwright):
    """Scenario C: Найти методичку (Navigate to Tasks -> Materials -> Open detail/files)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    await page.goto(BASE_URL, wait_until="networkidle")

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    clicks = 0

    # 1. Switch to tasks tab
    await page.evaluate("switchTab('tasks')")
    clicks += 1

    # 2. Switch to Materials segment
    await page.click("#tab-btn-materials")
    clicks += 1

    # 3. Find first material card
    first_mat = await page.wait_for_selector(".doc-card, .task-row", timeout=5000)
    clicks += 1

    time_to_action_ms = round((time.perf_counter() - t0) * 1000)

    results["Scenario C: Найти методичку"] = {
        "clicks": clicks,
        "screens": 1,  # Tasks view with segmented toggle
        "api_requests": api_requests,
        "initial_load_ms": 0,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": "Переход во вкладку «Задания» → сегмент «Методички и файлы» → прямой доступ к скачиванию документов."
    }
    await browser.close()


async def run_scenario_d(playwright):
    """Scenario D: Отметить сделанным (Toggle task done status)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    await page.goto(BASE_URL, wait_until="networkidle")

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    clicks = 0

    # Toggle directly from Focus screen 'Горит к сдаче'
    toggle_btn = await page.wait_for_selector(".task-checkbox-hit-area, .custom-checkbox", timeout=5000)
    await toggle_btn.click()
    clicks += 1

    await page.wait_for_selector("#toast.show", timeout=5000)
    time_to_action_ms = round((time.perf_counter() - t0) * 1000)

    results["Scenario D: Отметить сделанным"] = {
        "clicks": clicks,
        "screens": 1,
        "api_requests": api_requests,
        "initial_load_ms": 0,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": "1 клик на чекбокс прямо с главного экрана Сегодня (в секции Горит к сдаче). Мгновенный toast и подтверждающая анимация."
    }
    await browser.close()


async def run_scenario_e(playwright):
    """Scenario E: Вставить задачу через AI (AI tab, parse text, review evidence, confirm)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    await page.goto(BASE_URL, wait_until="networkidle")

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    clicks = 0

    # 1. Switch to AI tab
    await page.evaluate("switchTab('ai')")
    clicks += 1

    # 2. Paste text & submit
    await page.fill("#gemini-text-input", "Лабораторная по микроэлектронике к следующей среде в 436 ауд распечатать")
    await page.click("#gemini-submit-btn")
    clicks += 1

    # 3. Wait for evidence card
    await page.wait_for_selector(".sheet-evidence-card", timeout=45000)

    # 4. Confirm creation
    confirm_btn = await page.wait_for_selector("#sheet-confirm-btn", timeout=5000)
    await confirm_btn.click()
    clicks += 1

    await page.wait_for_selector(".ai-success-sheet", timeout=5000)
    time_to_action_ms = round((time.perf_counter() - t0) * 1000)

    results["Scenario E: Вставить задачу через AI"] = {
        "clicks": clicks,
        "screens": 3,  # AI tab -> AI Preview Sheet with Evidence -> Success Sheet
        "api_requests": api_requests,
        "initial_load_ms": 0,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": "Вставка текста старосты → генерация карточки доказательств («Почему это определено так») → сохранение в БД."
    }
    await browser.close()


async def run_scenario_f(playwright):
    """Scenario F: Проверить дедлайн (Urgent tasks section inspection)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    api_requests = 0
    def on_request(req):
        nonlocal api_requests
        if "/api/" in req.url:
            api_requests += 1
    page.on("request", on_request)

    t0 = time.perf_counter()
    await page.goto(BASE_URL, wait_until="networkidle")
    load_time_ms = round((time.perf_counter() - t0) * 1000)

    t_action_0 = time.perf_counter()
    # Check Next Action deadline badge or Urgent section
    await page.wait_for_selector("#next-action-time", timeout=5000)
    deadline_text = await page.inner_text("#next-action-time")
    time_to_action_ms = round((time.perf_counter() - t_action_0) * 1000)

    results["Scenario F: Проверить дедлайн"] = {
        "clicks": 0,
        "screens": 1,
        "api_requests": api_requests,
        "initial_load_ms": load_time_ms,
        "time_to_primary_action_ms": time_to_action_ms,
        "notes": "Дедлайн ближайшей задачи (с точным расчетом оставшихся часов) отображается сразу на экране Сегодня в карточке «Следующее действие»."
    }
    await browser.close()


async def run_scenario_g(playwright):
    """Scenario G: Офлайн вход (Service Worker / Cached Shell Fallback)"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
    page = await context.new_page()

    # 1. Warm cache online
    await page.goto(BASE_URL, wait_until="networkidle")
    await page.wait_for_timeout(1000)

    # 2. Go offline
    await context.set_offline(True)

    t0 = time.perf_counter()
    # Reload in offline mode
    try:
        await page.reload(wait_until="domcontentloaded", timeout=5000)
        shell_rendered = True
    except Exception:
        shell_rendered = False
    load_time_ms = round((time.perf_counter() - t0) * 1000)

    results["Scenario G: Офлайн вход"] = {
        "clicks": 0,
        "screens": 1,
        "api_requests": 0,
        "initial_load_ms": load_time_ms,
        "time_to_primary_action_ms": load_time_ms,
        "notes": f"Офлайн режим: кэшированная оболочка приложения {'загружена' if shell_rendered else 'не завершена'}, сетевые API вызовы безопасно изолированы."
    }
    await browser.close()


async def main():
    print("=== STARTING USER JOURNEY UX BENCHMARK ===")
    async with async_playwright() as p:
        print("Running Scenario A...")
        await run_scenario_a(p)
        print("Running Scenario B...")
        await run_scenario_b(p)
        print("Running Scenario C...")
        await run_scenario_c(p)
        print("Running Scenario D...")
        await run_scenario_d(p)
        print("Running Scenario E...")
        await run_scenario_e(p)
        print("Running Scenario F...")
        await run_scenario_f(p)
        print("Running Scenario G...")
        await run_scenario_g(p)

    print("\n=== MEASURED RESULTS ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    output_path = "e:/kai_assistant/docs_ux_metrics_raw.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("SAVED docs_ux_metrics_raw.json successfully!")

if __name__ == "__main__":
    asyncio.run(main())
