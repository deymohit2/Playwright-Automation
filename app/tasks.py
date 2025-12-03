# app/tasks.py
from celery import Celery
from app.settings import settings
from app.db import update_job
from app.playwright_worker import run_filing_workflow_sync
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

celery = Celery("worker", broker=settings.BROKER_URL, backend=settings.RESULT_BACKEND)
celery.conf.task_routes = {"app.tasks.process_case": {"queue": "filings"}}
logger = logging.getLogger(__name__)

# Retry on generic exceptions (but not on CaptchaRequired which we'll handle separately)
@celery.task(bind=True, acks_late=True, name="app.tasks.process_case", max_retries=5)
def process_case(self, job_id: int, case_payload: dict):
    """
    Celery task wrapper that calls an async Playwright worker via asyncio.run.
    job_id: DB id for tracking
    case_payload: everything required to file (client data, attachments)
    """
    try:
        # run_filing_workflow_sync will raise a CaptchaRequired exception if captcha encountered.
        result = run_filing_workflow_sync(job_id, case_payload)
        update_job(job_id, status="done", result=str(result))
        return result
    except CaptchaRequired as e:
        # Put job into "awaiting_captcha" and store screenshot path returned by exception
        screenshot_path = e.screenshot_path
        update_job(job_id, status="awaiting_captcha", captcha_screenshot_path=screenshot_path)
        # Notify admin (HTTP webhook, slack, whatever)
        notify_admin(job_id, screenshot_path)
        return {"status": "awaiting_captcha", "screenshot": screenshot_path}
    except Exception as exc:
        logger.exception("Worker failed")
        # Celery's retry
        try:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries+1))
        except self.MaxRetriesExceededError:
            update_job(job_id, status="failed", result=str(exc))
            raise

def notify_admin(job_id, screenshot_path):
    # Example: call webhook or send slack message so human can solve captcha
    import requests
    if settings.ADMIN_WEBHOOK:
        requests.post(settings.ADMIN_WEBHOOK, json={
            "text": f"Job {job_id} awaiting CAPTCHA. Screenshot: {screenshot_path}",
            "job_id": job_id,
            "screenshot": screenshot_path
        })