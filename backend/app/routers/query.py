import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.database import get_session
from app.models import QueryLog
from app.schemas import QueryRequest, QueryResponse
from app.routers.documents import embedding_service, vector_service
from app.services.rag_service import RAGService

router = APIRouter(prefix="/query", tags=["query"])
rag_service = RAGService(embedding_service=embedding_service, vector_service=vector_service)

@router.post("", response_model=QueryResponse)
def query_documents(request: QueryRequest, session: Session = Depends(get_session)):
    """
    Execute natural language query against uploaded document collection or scoped to a single document.
    Supports multi-turn chat history context, query re-writing, document diff mode, and metadata questions.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    response = rag_service.query(
        query_text=request.query.strip(),
        scope_document_id=request.document_id,
        top_k=request.top_k,
        chat_history=request.chat_history,
        session=session
    )

    # Log query to audit database table
    try:
        retrieved_ids = [c.chunk_id for c in response.citations]
        log_entry = QueryLog(
            query_text=request.query,
            scope_document_id=request.document_id,
            retrieved_chunk_ids=json.dumps(retrieved_ids),
            response_text=response.answer,
            execution_time_ms=response.execution_time_ms
        )
        session.add(log_entry)
        session.commit()
    except Exception:
        pass

    return response
