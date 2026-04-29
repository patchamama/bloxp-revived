from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.job import JobStatusResponse
from tasks.process_blog import create_job, get_state, process_basic, process_advanced

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
    max_posts: int = 250
    # custom selector (advanced) — accepts nested object from frontend
    custom_selector: Optional[Any] = None


@router.post("/jobs", status_code=202)
def create_job_endpoint(req: JobCreateRequest) -> dict:
    state = create_job()

    if req.type == "basic":
        if not req.feed_url.strip():
            raise HTTPException(status_code=422, detail="feed_url is required for basic jobs")
        payload = {
            "feed_url": req.feed_url,
            "links_to_footnotes": req.links_to_footnotes,
            "add_toc": req.add_toc,
            "include_images": req.include_images,
        }
        process_basic.delay(state.job_id, payload)
    else:
        for field, val in [
            ("starting_url", req.starting_url),
            ("site_url", req.site_url),
            ("site_title", req.site_title),
        ]:
            if not str(val).strip():
                raise HTTPException(status_code=422, detail=f"{field} is required for advanced jobs")

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
            "custom_selector": req.custom_selector,
        }
        process_advanced.delay(state.job_id, payload)

    return {"job_id": state.job_id}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    state = get_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")

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
        images_found=state.images_found,
        images_embedded=state.images_embedded,
    )
