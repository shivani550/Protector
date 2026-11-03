import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.db import engine, Base, AsyncSessionLocal
from backend.app.routers import (
    auth, files, patients, documents, letters, messages, insurer, webhooks, admin, events, upload
)
from backend.app.pipeline.jobs import run_worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure storage dirs exist
    Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    Path("./data/inbox").mkdir(parents=True, exist_ok=True)
    Path("./data/seed_generated").mkdir(parents=True, exist_ok=True)

    # Ensure database is seeded with 10 patient profiles if empty
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func, select
        from backend.app.models import Patient
        count = (await session.execute(select(func.count(Patient.id)))).scalar() or 0
        if count == 0:
            from scripts.seed import seed_database
            await seed_database()

    # Start background job worker
    worker_task = asyncio.create_task(run_worker_loop())

    yield

    # Shutdown: cancel background worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title="Protector - Patient Locker & Auto Query Response",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEMO_MODE else None,
    redoc_url="/redoc" if settings.DEMO_MODE else None,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        settings.PUBLIC_BASE_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "protector-api",
        "version": "1.0.0",
        "env": settings.ENV,
        "demo_mode": settings.DEMO_MODE,
        "delivery_mode": settings.DELIVERY_MODE,
        "llm_provider": settings.LLM_PROVIDER
    }

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(letters.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(insurer.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(upload.router, prefix="/api")

# Serve built frontend in production if dist exists
dist_path = Path("frontend/dist")
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=dist_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return None
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")
