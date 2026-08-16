"""
Nexus Canon API — DraftKings Beta
Backend Live / UI Deferred / Operator Runtime Active

FastAPI application entry point.
All engines, protocols, and agents are registered and ready.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.core.config import settings
from backend.core.db import engine
from backend.models.base import Base

# Import all ORM models so SQLAlchemy can create tables
import backend.models.project
import backend.models.source
import backend.models.section
import backend.models.evidence_anchor
import backend.models.bridge
import backend.models.protocol
import backend.models.flywheel
import backend.models.merge_decision
import backend.models.output_artifact

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Nexus Canon API — DraftKings Master Brief Operating System. "
        "Runtime mode: Backend Live / UI Deferred / Operator Runtime Active."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ─────────────────────────────────────────────────────────
from backend.api.routes_orchestrate import router as orchestrate_router
from backend.api.routes_projects import router as projects_router
from backend.api.routes_sources import router as sources_router
from backend.api.routes_sections import router as sections_router
from backend.api.routes_bridges import router as bridges_router
from backend.api.routes_agents import router as agents_router
from backend.api.routes_merge import router as merge_router
from backend.api.routes_export import router as export_router
from backend.api.routes_dashboard import router as dashboard_router

PREFIX = settings.api_prefix  # "/api"

app.include_router(orchestrate_router, prefix=PREFIX)
app.include_router(projects_router,    prefix=PREFIX)
app.include_router(sources_router,     prefix=PREFIX)
app.include_router(sections_router,    prefix=PREFIX)
app.include_router(bridges_router,     prefix=PREFIX)
app.include_router(agents_router,      prefix=PREFIX)
app.include_router(merge_router,       prefix=PREFIX)
app.include_router(export_router,      prefix=PREFIX)
app.include_router(dashboard_router,   prefix=PREFIX)

# ── Static files / frontend ────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/terminal", include_in_schema=False)
    def serve_terminal():
        terminal_path = os.path.join(FRONTEND_DIR, "nexus_terminal.html")
        if os.path.exists(terminal_path):
            return FileResponse(terminal_path)
        return {"error": "Terminal UI not yet deployed — backend runtime active"}


# ── Root / health ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "system": settings.app_name,
        "version": settings.version,
        "runtime_mode": "Backend Live / UI Deferred / Operator Runtime Active",
        "status": "operational",
        "endpoints": {
            "orchestrate": f"{PREFIX}/orchestrate",
            "engines": f"{PREFIX}/orchestrate/engines",
            "protocols": f"{PREFIX}/orchestrate/protocols",
            "examples": f"{PREFIX}/orchestrate/directives/examples",
            "projects": f"{PREFIX}/projects",
            "sources": f"{PREFIX}/sources",
            "sections": f"{PREFIX}/sections",
            "bridges": f"{PREFIX}/bridges",
            "agents": f"{PREFIX}/agents",
            "merge": f"{PREFIX}/merge",
            "export": f"{PREFIX}/export",
            "dashboard": f"{PREFIX}/dashboard",
            "docs": "/docs",
            "redoc": "/redoc",
            "terminal": "/terminal",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.version}
