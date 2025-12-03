# app/main.py
from fastapi import FastAPI, BackgroundTasks
from app.db import create_job, update_job, get_job
from app.tasks import process_case
from pydantic import BaseModel
from typing import List

app = FastAPI()

class CaseIn(BaseModel):
    case_id: str
    username: str
    password: str
    applicant_name: str
    address: str
    mark: str
    class_field: str
    attachments: List[str] = []  # for demo use local file paths or pre-uploaded s3 paths

@app.post("/cases")
def create_case(case: CaseIn):
    job_id = create_job(case.case_id)
    update_job(job_id, status="queued")
    # enqueue celery task
    process_case.delay(job_id, case.dict())
    return {"job_id": job_id, "status": "queued"}

class CaptchaSolutionIn(BaseModel):
    job_id: int
    captcha_input: str

@app.post("/cases/{job_id}/resume")
def resume_after_captcha(job_id:int, solution: CaptchaSolutionIn):
    # admin provides captcha text (or file) to resume
    job = get_job(job_id)
    if not job:
        return {"error": "not found"}
    # update DB with captcha solution (this simple example)
    update_job(job_id, status="resumed")
    # Re-enqueue the job or call a resume task that loads storage state and continues workflow.
    process_case.delay(job_id, {"resume_captcha": solution.captcha_input})
    return {"status":"resumed"}