"""
Kapipara API Probe & Reconnaissance Script (tools/probe_kapipara.py).
Intercepts network requests from https://para.kai.ru/schedule to identify the live API,
searches for group 5108, and captures the real schedule response into data/real_kapipara_5108.json.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "real_kapipara_5108.json"

captured_responses = []


async def probe():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("STARTING KAPIPARA PROBE: https://para.kai.ru/schedule")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        async def on_response(response):
            url = response.url
            ct = response.headers.get("content-type", "").lower()
            if any(k in url.lower() for k in ["api", "schedule", "group", "kai.ru", "capypara"]) or "application/json" in ct:
                try:
                    data = await response.json()
                    keys_summary = (
                        list(data.keys())[:10]
                        if isinstance(data, dict)
                        else (f"list[len={len(data)}]" if isinstance(data, list) else str(type(data)))
                    )
                    print(f"[INTERCEPTED] {response.request.method} {response.status} | {url}")
                    print(f"              Keys/Structure: {keys_summary}")
                    captured_responses.append({
                        "url": url,
                        "method": response.request.method,
                        "status": response.status,
                        "content_type": ct,
                        "data": data,
                    })
                except Exception:
                    pass

        page.on("response", on_response)

        print("\n1. Navigating to https://para.kai.ru/schedule ...")
        try:
            await page.goto("https://para.kai.ru/schedule", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception as e:
            print(f"   Note during load: {e}")

        await page.wait_for_timeout(1500)
        print(f"   Current page title: '{await page.title()}'")
        print(f"   Current page URL: '{page.url}'")

        # Bypass potential captcha overlay
        try:
            await page.evaluate("() => { const ov = document.querySelector('.SmartCaptcha-Overlay'); if (ov) ov.remove(); }")
        except Exception:
            pass

        # 2. Locate group search input
        print("\n2. Searching for group input field on page...")
        input_selectors = [
            "input[placeholder*='групп' i]",
            "input[placeholder*='номер' i]",
            "input[placeholder*='поиск' i]",
            "input[type='search']",
            "input[type='text']",
            "input",
        ]

        target_input = None
        for sel in input_selectors:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                for i in range(cnt):
                    item = loc.nth(i)
                    if await item.is_visible():
                        placeholder = await item.get_attribute("placeholder") or ""
                        print(f"   Found visible input: selector='{sel}' index={i} placeholder='{placeholder}'")
                        target_input = item
                        break
            if target_input:
                break

        if target_input:
            print("3. Typing '5108' into group search field...")
            try:
                await target_input.fill("5108")
                await page.wait_for_timeout(1000)
                # Look for suggestions
                group_options = page.locator("text='5108'")
                cnt = await group_options.count()
                if cnt > 0:
                    for i in range(cnt):
                        opt = group_options.nth(i)
                        if await opt.is_visible():
                            await opt.click(timeout=2000)
                            print(f"   Clicked suggestion '5108'")
                            break
                else:
                    await target_input.press("Enter")
            except Exception as e:
                print(f"   Note during typing/clicking: {e}")

            await page.wait_for_timeout(3000)

        # 3. Analyze captured responses
        print("\n" + "=" * 60)
        print(f"CAPTURED RESPONSES TOTAL: {len(captured_responses)}")
        print("=" * 60)

        # Prioritize api.capypara.ru/api/schedule_public
        schedule_response = None
        for r in captured_responses:
            url = r["url"].lower()
            if "yandex" in url or "mc." in url:
                continue
            if "schedule_public/" in url and "groups" not in url:
                schedule_response = r
                break

        if not schedule_response:
            for r in captured_responses:
                url = r["url"].lower()
                if "yandex" in url or "mc." in url:
                    continue
                data = r["data"]
                if isinstance(data, dict) and "result" in data and "schedule" in data["result"]:
                    schedule_response = r
                    break

        if schedule_response:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(schedule_response["data"], f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Successfully saved Kapipara response to: {OUTPUT_FILE}")
            print(f"   File size: {os.path.getsize(OUTPUT_FILE)} bytes")

            # Save full metadata log
            meta_file = DATA_DIR / "kapipara_probe_meta.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "url": r["url"],
                            "method": r["method"],
                            "status": r["status"],
                            "content_type": r["content_type"],
                        }
                        for r in captured_responses
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"[OK] Saved probe metadata to: {meta_file}")
        else:
            print("[FAIL] No JSON response captured from Kapipara.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(probe())
