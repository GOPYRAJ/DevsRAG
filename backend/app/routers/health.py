from fastapi import APIRouter
from app.routers.documents import vector_service
from app.config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_check():
    """
    Service health check & infrastructure diagnostics.
    """
    try:
        count = vector_service.collection.count()
        vector_status = f"connected ({count} total chunks)"
    except Exception as e:
        vector_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "vector_store": vector_status,
        "upload_dir": str(settings.UPLOAD_DIR),
        "embedding_provider": settings.EMBEDDING_PROVIDER
    }
