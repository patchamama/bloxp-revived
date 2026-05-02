from fastapi import APIRouter

from config import settings
from tasks.celery_app import celery_app
from tasks.process_blog import get_runtime_queue_stats

router = APIRouter()


@router.get("/system/status")
def system_status() -> dict:
    stats = get_runtime_queue_stats()
    inspector = celery_app.control.inspect(timeout=1.0)
    pong = inspector.ping() if inspector else None
    celery_running = bool(pong)
    workers = len(pong or {})
    active_map = inspector.active() if inspector else None
    reserved_map = inspector.reserved() if inspector else None
    active_tasks = sum(len(tasks or []) for tasks in (active_map or {}).values())
    reserved_tasks = sum(len(tasks or []) for tasks in (reserved_map or {}).values())
    return {
        "backend_version": settings.app_version,
        "celery_running": celery_running,
        "celery_workers": workers,
        "active_jobs": active_tasks,
        "pending_jobs": reserved_tasks + stats["pending_jobs"],
        "max_concurrent_jobs": stats["max_concurrent_jobs"],
    }
