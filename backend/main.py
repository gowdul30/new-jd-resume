"""
FastAPI Application Entry Point
Serves both the REST API and static frontend files.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from routers.optimize import router as optimize_router

load_dotenv()

app = FastAPI(
    title="Resume Tailor & ATS Scorer",
    description="Zero-Format-Loss resume optimization powered by Groq (llama-3.3-70b-versatile)",
    version="1.0.0",
)

# CORS — allow frontend dev on any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(optimize_router, prefix="/api")

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    # Catch-all for SPA routing
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        index = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return {"error": "Frontend not found"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": "llama-3.3-70b-versatile", "provider": "Groq"}
