from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class DocumentRead(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    status: str
    status_message: Optional[str] = None
    page_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentRead]
    total: int

class Citation(BaseModel):
    citation_id: int
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    snippet: str

class QueryRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    top_k: int = 4
    chat_history: Optional[List[ChatMessage]] = Field(default_factory=list)

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    execution_time_ms: int
