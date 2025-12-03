# app/playwright_worker.py
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from app.settings import settings
from app.storage import save_file_local
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class CaptchaRequired(Exception):
    def __init__(self, screenshot_path):
        super().__init__("Captcha required")
        self.screenshot_path = screenshot_path

async def _run_workflow(job_id: int, case_payload: dict):
    storage_dir = Path(settings.STORAGE_LOCAL_PATH)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path = storage_dir / f"job_{job_id}_storage.json"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
        context = await browser.new_context()
        # restore storage if exists
        if storage_state_path.exists():
            await context.storage_state(path=str(storage_state_path))

        page = await context.new_page()

        try:
            # 1) login (example)
            await page.goto("https://example-legal-portal.gov/login", timeout=60000)
            await page.locator("input[name='username']").fill(case_payload["username"])
            await page.locator("input[name='password']").fill(case_payload["password"])
            await page.locator("button[type='submit']").click()
            await page.wait_for_load_state("networkidle")

            # Check if login encountered captcha
            if await page.locator("css=div.captcha, img.captcha-image").count() > 0:
                screenshot = storage_dir / f"job_{job_id}_captcha.png"
                await page.screenshot(path=str(screenshot))
                # persist storage state so resume can reuse cookies/session
                await context.storage_state(path=str(storage_state_path))
                raise CaptchaRequired(str(screenshot))

            # 2) navigate to filing form
            await page.goto("https://example-legal-portal.gov/trademark/new", timeout=60000)

            # Multi-step form example
            # Step 1 - basic applicant info
            await page.locator("input[name='applicant_name']").fill(case_payload["applicant_name"])
            await page.locator("input[name='address']").fill(case_payload["address"])
            await page.locator("button:has-text('Next')").click()
            await page.wait_for_load_state("networkidle")

            # Detect potential captcha on any step
            if await page.locator("img.captcha-image").count() > 0:
                screenshot = storage_dir / f"job_{job_id}_captcha_step2.png"
                await page.screenshot(path=str(screenshot))
                await context.storage_state(path=str(storage_state_path))
                raise CaptchaRequired(str(screenshot))

            # Step 2 - mark details (example)
            await page.locator("input[name='mark']").fill(case_payload["mark"])
            await page.locator("input[name='class']").fill(case_payload["class"])
            await page.locator("button:has-text('Next')").click()
            await page.wait_for_load_state("networkidle")

            # Step 3 - attachments
            # Upload file (some portals accept base64 file upload or file input)
            await page.set_input_files("input[type=file]", case_payload["attachments"])  # local paths
            await page.locator("button:has-text('Submit')").click()
            await page.wait_for_load_state("networkidle")

            # final: capture confirmation
            confirm = await page.locator("css=.filing-id").text_content()
            # persist storage state for reuse
            await context.storage_state(path=str(storage_state_path))
            return {"status": "filed", "filing_id": confirm}
        finally:
            await browser.close()


def run_filing_workflow_sync(job_id:int, case_payload:dict):
    """
    Synchronous wrapper for Celery tasks — runs the async workflow.
    Raises CaptchaRequired exception if human intervention is needed.
    """
    try:
        return asyncio.run(_run_workflow(job_id, case_payload))
    except CaptchaRequired as e:
        # re-raise our custom exception to be handled by the Celery wrapper
        raise e
