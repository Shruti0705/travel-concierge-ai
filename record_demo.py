import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def run_demo():
    artifact_dir = "/config/.gemini/antigravity/brain/2455d53e-be8b-4c41-83c3-f9f3f4cca17c"
    scratch_dir = os.path.join(artifact_dir, "scratch")
    os.makedirs(scratch_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=scratch_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        print("Navigating to live Travel Concierge AI app...")
        await page.goto("https://travel-concierge-frontend-255199647468.us-east1.run.app/", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # Turn 1: Click quick example prompt chip "🌲 Parks near Seattle"
        print("Turn 1: Asking about parks near Seattle...")
        chip = page.locator(".chip", has_text="Parks near Seattle")
        await chip.click()
        
        # Wait for agent response 1
        await page.wait_for_selector(".msg.agent", timeout=30000)
        await page.wait_for_timeout(4000)

        # Turn 2: Generate destination image / weather lookup
        print("Turn 2: Asking for destination image & weather...")
        prompt_2 = "Check weather in Seattle and generate a picture of Space Needle at sunset"
        await page.fill("#input", prompt_2)
        await page.wait_for_timeout(1000)
        await page.click("button.send-btn")

        # Wait for agent response 2 using nth(1)
        agent_msgs = page.locator(".msg.agent")
        await agent_msgs.nth(1).wait_for(timeout=45000)
        await page.wait_for_timeout(5000)

        raw_video_path = await page.video.path()
        await context.close()
        await browser.close()

        final_webm = os.path.join(artifact_dir, "demo_walkthrough.webm")
        shutil.move(raw_video_path, final_webm)
        print(f"Recorded demo video successfully: {final_webm}")

if __name__ == "__main__":
    asyncio.run(run_demo())
