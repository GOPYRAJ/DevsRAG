"""
Main FastAPI entrypoint re-exporter for Render / Vercel deployment commands: `uvicorn main:app`
"""
from fastapi.middleware.cors import CORSMiddleware
from app.main import app

# Guarantee CORS is enabled for all origins including Vercel (devs-rag.vercel.app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://devs-rag.vercel.app",
        "https://devs-rag-git-main-gopyraj1.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

__all__ = ["app"]
