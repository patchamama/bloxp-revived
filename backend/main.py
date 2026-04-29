from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs, download, contact

app = FastAPI(title="Bloxp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(download.router, prefix="/api")
app.include_router(contact.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
