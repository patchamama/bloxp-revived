from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers import contact, download, jobs

app = FastAPI(title="Bloxp API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(jobs.router, prefix="/api")
app.include_router(download.router, prefix="/api")
app.include_router(contact.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": "2.0.0"}


# ── Frontend static files (production build) ──────────────────────────────────
# The deploy.sh script copies frontend/dist → backend/static.
# In development (no static/ dir) the Vite dev server handles the frontend.
_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Serve the React SPA for any non-API route (client-side routing support)."""
        requested = _STATIC_DIR / full_path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(_STATIC_DIR / "index.html")
