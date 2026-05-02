from enum import Enum
from typing import Optional
from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    parsing = "parsing"
    crawling = "crawling"
    downloading_images = "downloading_images"
    generating = "generating"
    done = "done"
    error = "error"


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    progress: int = 0
    posts_found: int = 0
    posts_crawled: int = 0
    images_found: int = 0
    images_embedded: int = 0
    error_message: Optional[str] = None
    epub_path: Optional[str] = None
    mobi_path: Optional[str] = None
    pdf_path: Optional[str] = None
    ebook_title: Optional[str] = None
    created_at: float = 0.0
    expires_at: float = 0.0


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    posts_found: int
    posts_crawled: int
    images_found: int = 0
    images_embedded: int = 0
    error_message: Optional[str] = None
    has_epub: bool = False
    has_mobi: bool = False
    has_pdf: bool = False
    ebook_title: Optional[str] = None
    queue_position: Optional[int] = None
