import time
import redis as redis_lib
from config import settings
from storage.file_manager import cleanup_job
from tasks.celery_app import celery_app

_redis = redis_lib.from_url(settings.redis_url)


@celery_app.task
def cleanup_expired_jobs() -> dict:
    """Scan Redis for expired job keys and remove generated files."""
    now = time.time()
    removed = 0

    for key in _redis.scan_iter("job:*"):
        raw = _redis.get(key)
        if not raw:
            continue
        try:
            import json
            state = json.loads(raw)
            if state.get("expires_at", 0) < now:
                job_id = state.get("job_id")
                if job_id:
                    cleanup_job(job_id)
                _redis.delete(key)
                removed += 1
        except Exception:
            continue

    return {"removed": removed}
