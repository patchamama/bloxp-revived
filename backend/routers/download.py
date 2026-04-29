from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from models.job import JobStatus
from tasks.process_blog import get_state

router = APIRouter()

_CONTENT_TYPES = {
    "epub": "application/epub+zip",
    "mobi": "application/x-mobipocket-ebook",
    "pdf": "application/pdf",
}


@router.get("/jobs/{job_id}/download/{format}")
def download(job_id: str, format: str) -> FileResponse:
    if format not in _CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid format. Use epub, mobi, or pdf.")

    state = get_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")

    if state.status != JobStatus.done:
        raise HTTPException(status_code=425, detail="Job not done yet")

    file_path_str = getattr(state, f"{format}_path", None)
    if not file_path_str:
        raise HTTPException(
            status_code=503,
            detail=f"{format.upper()} not available (Calibre may not be installed)",
        )

    file_path = Path(file_path_str)
    if not file_path.exists():
        raise HTTPException(status_code=503, detail=f"{format.upper()} file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=_CONTENT_TYPES[format],
        filename=f"output.{format}",
    )
