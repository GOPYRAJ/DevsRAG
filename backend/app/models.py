import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class DocumentStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    filename: str = Field(index=True)
    file_hash: str = Field(index=True)
    file_path: str
    file_size_bytes: int
    mime_type: str
    status: str = Field(default=DocumentStatus.PENDING, index=True)
    status_message: Optional[str] = Field(default=None)
    page_count: int = Field(default=0)
    chunk_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    chunks: list["DocumentChunk"] = Relationship(back_populates="document", cascade_delete=True)

class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    chunk_index: int
    content: str
    token_count: int
    page_number: int = Field(default=1)
    vector_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.now)

    document: Optional[Document] = Relationship(back_populates="chunks")

class QueryLog(SQLModel, table=True):
    __tablename__ = "query_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    query_text: str
    scope_document_id: Optional[str] = Field(default=None)
    retrieved_chunk_ids: str = Field(default="[]")  # JSON array string
    response_text: str
    execution_time_ms: int
    created_at: datetime = Field(default_factory=datetime.now)
