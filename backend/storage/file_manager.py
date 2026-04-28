import os
from pathlib import Path
from config import settings


def job_dir(job_id: str) -> Path:
    d = Path(settings.generated_dir) / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def epub_path(job_id: str) -> Path:
    return job_dir(job_id) / "output.epub"


def mobi_path(job_id: str) -> Path:
    return job_dir(job_id) / "output.mobi"


def pdf_path(job_id: str) -> Path:
    return job_dir(job_id) / "output.pdf"


def cleanup_job(job_id: str) -> None:
    import shutil
    d = job_dir(job_id)
    if d.exists():
        shutil.rmtree(d)
