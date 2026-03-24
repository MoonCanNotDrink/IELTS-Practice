"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import init_db, async_session
from app.seed_data import seed_topics, seed_writing_prompts
from app.routes.part2 import router as part2_router
from app.routes.exam import router as exam_router
from app.routes.scoring import router as scoring_router
from app.routes.dev import router as dev_router
from app.routes.auth import router as auth_router
from app.routes.writing import router as writing_router
from app.routes.dashboard import router as dashboard_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


class FrontendStaticFiles(StaticFiles):
    """Serve frontend assets with explicit UTF-8 text charset and no-store cache."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        content_type = response.headers.get("content-type", "")
        is_text_asset = content_type.startswith("text/") or content_type.startswith("application/javascript")
        if content_type and is_text_asset and "charset=" not in content_type.lower():
            response.headers["content-type"] = f"{content_type}; charset=utf-8"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as db:
        await seed_topics(db)
        await seed_writing_prompts(db)
    yield


APP_VERSION = "0.2.6"
app = FastAPI(title=settings.APP_NAME, version=APP_VERSION, lifespan=lifespan)

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
app.include_router(writing_router)
app.include_router(dashboard_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": app.version}


# Static assets
if FRONTEND_DIR.exists():
    app.mount("/static", FrontendStaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/history", include_in_schema=False)
async def serve_history():
    history_path = FRONTEND_DIR / "history.html"
    if history_path.exists():
        return FileResponse(
            str(history_path),
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store, max-age=0"},
        )
    return {"message": "History page not found"}


@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(
            str(index_path),
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store, max-age=0"},
        )
    return {"message": "Frontend not found"}
