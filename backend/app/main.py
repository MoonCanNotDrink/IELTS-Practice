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
from app.routes.auth import router as auth_router
from app.routes.writing import router as writing_router
from app.routes.dashboard import router as dashboard_router
from app.limiter import limiter

# slowapi rate limit handler
from slowapi import _rate_limit_exceeded_handler  # type: ignore
from slowapi.errors import RateLimitExceeded  # type: ignore

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


APP_VERSION = "0.2.9"
app = FastAPI(title=settings.APP_NAME, version=APP_VERSION, lifespan=lifespan)

# attach limiter instance to app state for route decorators to use
app.state.limiter = limiter

# register rate limit exceeded handler (returns 429)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or (["*"] if settings.DEBUG else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (MUST come before static file mounts)
app.include_router(auth_router)
app.include_router(part2_router)
app.include_router(exam_router)
app.include_router(scoring_router)
app.include_router(writing_router)
app.include_router(dashboard_router)

if settings.DEBUG:
    from app.routes.dev import router as dev_router
    app.include_router(dev_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": app.version}


# Static assets
if FRONTEND_DIR.exists():
    app.mount("/static", FrontendStaticFiles(directory=str(FRONTEND_DIR)), name="static")


PAGE_ROUTES = {
    "/": "index.html",
    "/speaking": "speaking.html",
    "/writing": "writing.html",
    "/history": "history.html",
    "/reset-password": "reset-password.html",
}


for _route, _filename in PAGE_ROUTES.items():
    _page_path = FRONTEND_DIR / _filename

    def _make_handler(page_path: Path = _page_path, name: str = _filename):
        async def serve_page():
            if page_path.exists():
                return FileResponse(
                    str(page_path),
                    media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-store, max-age=0"},
                )
            return {"message": f"{name} not found"}
        return serve_page

    app.get(_route, include_in_schema=False)(_make_handler())
