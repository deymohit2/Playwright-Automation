# app/db.py
import sqlite3
from typing import Any
from pathlib import Path

DB_PATH = Path("jobs.db")
conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT,
  status TEXT,
  attempt INTEGER DEFAULT 0,
  storage_state_path TEXT,
  captcha_screenshot_path TEXT,
  result TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def create_job(case_id: str) -> int:
    cur = conn.cursor()
    cur.execute("INSERT INTO jobs(case_id, status) VALUES (?, ?)", (case_id, "created"))
    conn.commit()
    return cur.lastrowid

def update_job(job_id:int, **kwargs:Any):
    keys = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    conn.execute(f"UPDATE jobs SET {keys} WHERE id=?", values)
    conn.commit()

def get_job(job_id:int):
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    return cur.fetchone()
