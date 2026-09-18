import asyncio
import os
from playwright.async_api import async_playwright

BRAIN_DIR = r"C:\Users\karim\.gemini\antigravity\brain\c206c1c6-370f-43e1-9669-a3b6efc39dfd"

async def capture():
    token = "kai5108_secret_passcode_2026"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Mobile Dark
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await page.evaluate(f"localStorage.setItem('kai_app_auth_token', '{token}'); localStorage.setItem('kai_theme', 'dark');")
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_focus_dark.png"))
        
        # Click Tasks
        await page.evaluate("switchTab('tasks')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_tasks_dark.png"))
        
        # Open task sheet
        await page.click(".task-row")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_task_sheet_dark.png"))
        await page.click("#task-detail-close-btn")
        await page.wait_for_timeout(300)

        # Click AI
        await page.evaluate("switchTab('ai')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_ai_dark.png"))
        
        # Click More
        await page.evaluate("switchTab('more')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_more_dark.png"))

        # Switch to light
        await page.click("#theme-toggle-btn")
        await page.wait_for_timeout(400)
        await page.evaluate("switchTab('focus')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(BRAIN_DIR, "polished_mobile_focus_light.png"))
        
        # Desktop Dark
        dpage = await browser.new_page(viewport={"width": 1280, "height": 800})
        await dpage.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await dpage.evaluate(f"localStorage.setItem('kai_app_auth_token', '{token}'); localStorage.setItem('kai_theme', 'dark');")
        await dpage.reload(wait_until="networkidle")
        await dpage.wait_for_timeout(1000)
        await dpage.screenshot(path=os.path.join(BRAIN_DIR, "polished_desktop_focus_dark.png"))

        await browser.close()
        print("Captured all polished screenshots!")

if __name__ == "__main__":
    asyncio.run(capture())
