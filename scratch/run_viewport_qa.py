import asyncio
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

VIEWPORTS = [
    {"name": "android_360x740", "width": 360, "height": 740, "device": "Android Small"},
    {"name": "iphone_390x844", "width": 390, "height": 844, "device": "iPhone Standard"},
    {"name": "iphone_max_430x932", "width": 430, "height": 932, "device": "iPhone Pro Max"},
    {"name": "ipad_768x1024", "width": 768, "height": 1024, "device": "iPad Portrait"},
    {"name": "ipad_pro_1024x1366", "width": 1024, "height": 1366, "device": "iPad Pro"},
    {"name": "desktop_1440x900", "width": 1440, "height": 900, "device": "Desktop HD"},
]

THEMES = ["dark", "light"]
ARTIFACTS_DIR = "C:/Users/karim/.gemini/antigravity/brain/c206c1c6-370f-43e1-9669-a3b6efc39dfd"
PASSCODE = "kai5108_secret_passcode_2026"

qa_results = []

async def run_qa():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            for theme in THEMES:
                context = await browser.new_context(
                    viewport={"width": vp["width"], "height": vp["height"]},
                    device_scale_factor=2 if vp["width"] < 768 else 1,
                )
                await context.add_cookies([{"name": "kai_app_auth_token", "value": PASSCODE, "domain": "127.0.0.1", "path": "/"}])
                page = await context.new_page()

                await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
                await page.evaluate(f"document.documentElement.setAttribute('data-theme', '{theme}')")
                await page.wait_for_timeout(600)

                # Check horizontal scroll overflow
                has_h_scroll = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth")

                # Check minimum touch target on primary nav buttons
                min_nav_target = await page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll('.desktop-nav-btn, .bottom-nav-item, .glass-icon-btn, .glass-pill'));
                    let minW = 999, minH = 999;
                    btns.forEach(b => {
                        const rect = b.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            if (rect.width < minW) minW = rect.width;
                            if (rect.height < minH) minH = rect.height;
                        }
                    });
                    return { minW, minH };
                }''')

                filename = f"qa_{vp['name']}_{theme}.png"
                filepath = os.path.join(ARTIFACTS_DIR, filename)
                await page.screenshot(path=filepath, full_page=False)

                qa_results.append({
                    "viewport": f"{vp['width']}x{vp['height']}",
                    "device": vp["device"],
                    "theme": theme,
                    "overflow_x": has_h_scroll,
                    "min_touch_target": min_nav_target,
                    "screenshot": filename,
                    "status": "PASS" if not has_h_scroll and min_nav_target["minH"] >= 36 else "WARN"
                })
                print(f"[{vp['name']} - {theme}] Overflow: {has_h_scroll}, MinTarget: {min_nav_target['minW']:.1f}x{min_nav_target['minH']:.1f} -> SAVED {filename}")
                await context.close()

        await browser.close()

    with open("docs_viewport_qa_raw.json", "w", encoding="utf-8") as f:
        json.dump(qa_results, f, ensure_ascii=False, indent=2)
    print("ALL 12 VIEWPORT COMBINATIONS VERIFIED & LOGGED")

if __name__ == "__main__":
    asyncio.run(run_qa())
