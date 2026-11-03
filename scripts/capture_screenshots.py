import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

CHROME_PATH = r"C:\Users\user\AppData\Local\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844, "is_mobile": True, "has_touch": True},
}

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)

        for device_name, vp in VIEWPORTS.items():
            context = await browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = await context.new_page()

            # 1. Login Page
            await page.goto("http://127.0.0.1:8000/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUTPUT_DIR / f"login_{device_name}.png"), full_page=True)
            print(f"[OK] login_{device_name}.png")

            # Perform Login
            await page.fill('input[type="email"]', 'admin@demo.test')
            await page.fill('input[type="password"]', 'DemoPass123!')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1500)

            # 2. Patients List
            await page.goto("http://127.0.0.1:8000/patients", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUTPUT_DIR / f"patients_{device_name}.png"), full_page=True)
            print(f"[OK] patients_{device_name}.png")

            # 3. Patient Detail (Arjun Sharma)
            await page.goto("http://127.0.0.1:8000/patients/pt-uuid-pt-0001", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUTPUT_DIR / f"patient_detail_{device_name}.png"), full_page=True)
            print(f"[OK] patient_detail_{device_name}.png")

            # Switch to Query Letters tab
            try:
                await page.click('button:has-text("Query Letters")')
                await page.wait_for_timeout(800)
                await page.screenshot(path=str(OUTPUT_DIR / f"letter_detail_{device_name}.png"), full_page=True)
                print(f"[OK] letter_detail_{device_name}.png")
            except Exception as e:
                print(f"Tab click notice: {e}")

            # 4. Admin Dashboard
            await page.goto("http://127.0.0.1:8000/admin", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUTPUT_DIR / f"admin_{device_name}.png"), full_page=True)
            print(f"[OK] admin_{device_name}.png")

            # 5. Magic Upload
            await page.goto("http://127.0.0.1:8000/upload/sample-token", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUTPUT_DIR / f"magic_upload_{device_name}.png"), full_page=True)
            print(f"[OK] magic_upload_{device_name}.png")

            await context.close()

        await browser.close()
        print("All responsive screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture())
