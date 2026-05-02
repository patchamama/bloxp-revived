from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from models.job import JobStatus, JobStatusResponse
from tasks.process_blog import (
    create_job,
    get_state,
    submit_job,
    get_queue_position,
    cancel_job,
    set_job_source_url,
)

router = APIRouter()


class JobCreateRequest(BaseModel):
    type: Literal["basic", "advanced"]
    # basic
    feed_url: str = ""
    # advanced
    starting_url: str = ""
    starting_title: str = ""
    site_url: str = ""
    site_title: str = ""
    site_description: str = ""
    # shared
    links_to_footnotes: bool = False
    add_toc: bool = True
    include_images: bool = True
    max_posts: int = Field(default=250, ge=1)
    post_range_start: int = Field(default=1, ge=1)
    post_range_end: int | None = Field(default=None, ge=1)
    # custom selector (advanced) — accepts nested object from frontend
    custom_selector: Optional[Any] = None


@router.post("/jobs", status_code=202)
def create_job_endpoint(req: JobCreateRequest) -> dict:
    state = create_job()
    max_limit = settings.max_posts_limit
    if req.max_posts > max_limit:
        raise HTTPException(status_code=422, detail=f"max_posts must be <= {max_limit}")
    if req.post_range_start > max_limit:
        raise HTTPException(status_code=422, detail=f"post_range_start must be <= {max_limit}")
    if req.post_range_end is not None and req.post_range_end > max_limit:
        raise HTTPException(status_code=422, detail=f"post_range_end must be <= {max_limit}")

    if req.type == "basic":
        if not req.feed_url.strip():
            raise HTTPException(status_code=422, detail="feed_url is required for basic jobs")
        set_job_source_url(state.job_id, req.feed_url)
        payload = {
            "feed_url": req.feed_url,
            "links_to_footnotes": req.links_to_footnotes,
            "add_toc": req.add_toc,
            "include_images": req.include_images,
            "max_posts": req.max_posts,
            "post_range_start": req.post_range_start,
            "post_range_end": req.post_range_end,
        }
        submit_job(state.job_id, "basic", payload)
    else:
        for field, val in [
            ("starting_url", req.starting_url),
            ("site_url", req.site_url),
            ("site_title", req.site_title),
        ]:
            if not str(val).strip():
                raise HTTPException(status_code=422, detail=f"{field} is required for advanced jobs")

        set_job_source_url(state.job_id, req.site_url)
        payload = {
            "starting_url": req.starting_url,
            "starting_title": req.starting_title,
            "site_url": req.site_url,
            "site_title": req.site_title,
            "site_description": req.site_description,
            "links_to_footnotes": req.links_to_footnotes,
            "add_toc": req.add_toc,
            "include_images": req.include_images,
            "max_posts": req.max_posts,
            "post_range_start": req.post_range_start,
            "post_range_end": req.post_range_end,
            "custom_selector": req.custom_selector,
        }
        submit_job(state.job_id, "advanced", payload)

    return {"job_id": state.job_id}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    state = get_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")

    queue_position = (
        get_queue_position(state.job_id) if state.status == JobStatus.queued else None
    )

    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status,
        progress=state.progress,
        posts_found=state.posts_found,
        posts_crawled=state.posts_crawled,
        error_message=state.error_message,
        has_epub=bool(state.epub_path),
        has_mobi=bool(state.mobi_path),
        has_pdf=bool(state.pdf_path),
        ebook_title=state.ebook_title,
        source_url=state.source_url,
        images_found=state.images_found,
        images_embedded=state.images_embedded,
        queue_position=queue_position,
    )


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> None:
    existed = cancel_job(job_id)
    if not existed:
        raise HTTPException(status_code=404, detail="Job not found")
