"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import init_db, async_session
from app.seed_data import seed_topics
from app.routes.part2 import router as part2_router
from app.routes.exam import router as exam_router
from app.routes.scoring import router as scoring_router
from app.routes.dev import router as dev_router
from app.routes.auth import router as auth_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as db:
        await seed_topics(db)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.2.6", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (MUST come before static file mounts)
app.include_router(auth_router)
app.include_router(part2_router)
app.include_router(exam_router)
app.include_router(scoring_router)
app.include_router(dev_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.2.0"}


# Static assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/history", include_in_schema=False)
async def serve_history():
    history_path = FRONTEND_DIR / "history.html"
    if history_path.exists():
        return FileResponse(str(history_path))
    return {"message": "History page not found"}


@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend not found"}
