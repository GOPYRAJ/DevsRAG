from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Query, BackgroundTasks, HTTPException, status
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Document, DocumentChunk, DocumentStatus
from app.schemas import DocumentRead, DocumentListResponse
from app.services.file_service import FileService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.pipeline_service import process_document_pipeline

router = APIRouter(prefix="/documents", tags=["documents"])

# Global shared service instances
embedding_service = EmbeddingService()
vector_service = VectorService()

@router.post("", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    overwrite: bool = Query(True, description="Set true to overwrite if duplicate SHA-256 or filename exists"),
    session: Session = Depends(get_session)
):
    """
    Upload a document file (PDF, DOCX, TXT, MD). Returns 202 Accepted and queues async vector processing.
    Automatically overwrites duplicate files and re-indexes cleanly.
    """
    doc, is_duplicate = await FileService.save_and_create_document(file, session, overwrite=overwrite)
    
    # If duplicate, purge old ChromaDB vector chunks before re-processing
    if is_duplicate:
        vector_service.delete_document_vectors(doc.id)

    # Dispatch background worker
    background_tasks.add_task(
        process_document_pipeline,
        document_id=doc.id,
        embedding_service=embedding_service,
        vector_service=vector_service
    )

    return doc

@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    session: Session = Depends(get_session)
):
    """
    Retrieve all uploaded documents with status and metadata.
    """
    query = select(Document)
    if status_filter:
        query = query.where(Document.status == status_filter)
    
    query = query.order_by(Document.created_at.desc())
    documents = session.exec(query).all()
    
    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )

@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, session: Session = Depends(get_session)):
    """
    Get detailed document status and metadata by ID.
    """
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return doc

@router.delete("/{document_id}")
def delete_document(document_id: str, session: Session = Depends(get_session)):
    """
    Delete document record, source file, and associated ChromaDB vector chunks.
    """
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 1. Remove vector chunks from ChromaDB
    try:
        vector_service.delete_document_vectors(document_id)
    except Exception as e:
        pass

    # 2. Remove physical file
    file_p = Path(doc.file_path)
    if file_p.exists():
        try:
            file_p.unlink()
        except Exception:
            pass

    # 3. Remove DB record
    session.delete(doc)
    session.commit()

    return {"id": document_id, "deleted": True, "message": "Document and all associated vector indices cleanly removed."}
