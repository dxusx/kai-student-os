import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 412, "height": 915})

        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: print(f"[Browser {msg.type}] {msg.text}") if msg.type in ["error", "warn"] else None)

        print("Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("Taking Focus tab screenshot...")
        await page.screenshot(path="screen_focus.png")

        print("Taking Schedule timeline screenshot...")
        await page.locator("button[data-tab='schedule']").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="screen_schedule.png")

        print("Taking Tasks (Submissions) screenshot...")
        await page.locator("button[data-tab='tasks']").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="screen_tasks_submissions.png")

        print("Taking Tasks (Materials) screenshot...")
        await page.locator("#tab-btn-materials").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="screen_tasks_materials.png")

        await b.close()
        if errors:
            print("PAGE ERRORS DETECTED:", errors)
        else:
            print("NO JS ERRORS DETECTED!")

asyncio.run(run())
print("ALL SCREENS DONE")
