"""
Main FastAPI entrypoint re-exporter for Render / Vercel deployment commands: `uvicorn main:app`
"""
from fastapi.middleware.cors import CORSMiddleware
from app.main import app

# Guarantee CORS is enabled for all origins including Vercel (devs-rag.vercel.app)
# Note: CORSMiddleware is also registered in app.main
__all__ = ["app"]
