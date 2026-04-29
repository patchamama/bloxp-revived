from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.job import JobStatusResponse
from tasks.process_blog import create_job, get_state, process_basic, process_advanced

router = APIRouter()


class JobCreateRequest(BaseModel):
    type: Literal["basic", "advanced"]
    # basic
    feed_url: Optional[str] = None
    # advanced
    starting_url: Optional[str] = None
    starting_title: Optional[str] = None
    site_url: Optional[str] = None
    site_title: Optional[str] = None
    site_description: str = ""
    # shared
    links_to_footnotes: bool = False
    add_toc: bool = True
    max_posts: int = 250
    # custom selector (advanced)
    custom_search_opt: bool = False
    tag_name: str = ""
    attr_name: str = ""
    attr_value: str = ""
    pre_string: str = ""
    parent_tag: bool = False


@router.post("/jobs")
def create_job_endpoint(req: JobCreateRequest) -> dict:
    state = create_job()

    if req.type == "basic":
        if not req.feed_url:
            raise HTTPException(status_code=422, detail="feed_url is required for basic jobs")
        payload = {
            "feed_url": req.feed_url,
            "links_to_footnotes": req.links_to_footnotes,
            "add_toc": req.add_toc,
        }
        process_basic.delay(state.job_id, payload)
    else:
        missing = [f for f, v in [
            ("starting_url", req.starting_url),
            ("starting_title", req.starting_title),
            ("site_url", req.site_url),
            ("site_title", req.site_title),
        ] if not v]
        if missing:
            raise HTTPException(status_code=422, detail=f"Required fields missing: {', '.join(missing)}")

        custom_selector = None
        if req.custom_search_opt:
            custom_selector = {
                "tag_name": req.tag_name,
                "attr_name": req.attr_name,
                "attr_value": req.attr_value,
                "pre_string": req.pre_string,
                "parent_tag": req.parent_tag,
            }
        payload = {
            "starting_url": req.starting_url,
            "starting_title": req.starting_title,
            "site_url": req.site_url,
            "site_title": req.site_title,
            "site_description": req.site_description,
            "links_to_footnotes": req.links_to_footnotes,
            "add_toc": req.add_toc,
            "max_posts": req.max_posts,
            "custom_selector": custom_selector,
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
    )
