# app/storage.py
from pathlib import Path
import boto3
from app.settings import settings
import shutil

def save_file_local(src_path, dest_name):
    dest_dir = Path(settings.STORAGE_LOCAL_PATH)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / dest_name
    shutil.copy(src_path, dest)
    return str(dest)

def upload_to_s3(local_path, key):
    if not settings.S3_BUCKET:
        raise RuntimeError("S3 not configured")
    s3 = boto3.client("s3")
    s3.upload_file(local_path, settings.S3_BUCKET, key)
    return f"s3://{settings.S3_BUCKET}/{key}"
