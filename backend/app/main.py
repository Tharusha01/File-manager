from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import ensure_initial_user
from .db import SessionLocal, init_db
from .routers import auth as auth_router
from .routers import files as files_router
from .routers import torrents as torrents_router
from .torrent_service import service

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        await ensure_initial_user(session)
    await service.start()
    try:
        yield
    finally:
        await service.stop()


app = FastAPI(title="File Manager", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(torrents_router.router)
app.include_router(torrents_router.ws_router)
app.include_router(files_router.router)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


# ---- React SPA serving --------------------------------------------------------
# In dev (no static dir), the Vite dev server handles the frontend at :5173.
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = STATIC_DIR / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Try to serve a real file out of /static, otherwise fall back to index.html
        # so client-side routing works for /login, /files, /watch, etc.
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "frontend not built"}
