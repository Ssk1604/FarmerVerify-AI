# backend/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api.routes import register_routes
from backend.utils import logger


def create_app() -> FastAPI:
    app = FastAPI(
        title="FarmerVerify AI",
        description="AI-powered multilingual document verification platform",
        version="1.0.0",
    )

    # ── CORS — allow ALL origins including localhost:3000 ──────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],           # allows all origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # ── Register API routes FIRST ──────────────────────────────────────────
    register_routes(app)
    logger.info("✅ API routes registered")
    

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        logger.error(
            "Unhandled exception on {} {}: {}\n{}",
            request.method, request.url.path,
            exc, traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path,
            },
        )

    # ── Static file mounts AFTER routes ───────────────────────────────────
    base_dir = Path(__file__).resolve().parent.parent

    uploads_dir = base_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)
    app.mount("/results", StaticFiles(directory=str(results_dir)), name="results")

    chatbot_dir = base_dir / "chatbot"
    if chatbot_dir.exists():
        app.mount("/chat", StaticFiles(directory=str(chatbot_dir), html=True), name="chatbot")

    dashboard_dir = base_dir / "dashboard"
    if dashboard_dir.exists():
        app.mount("/admin", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

    logger.info("✅ Static file mounts configured")

    @app.get("/")
    async def root():
        return {
            "service": "FarmerVerify AI",
            "status": "running",
            "docs": "/docs",
            "chatbot": "/chat",
            "admin": "/admin",
        }

    return app


app = create_app()