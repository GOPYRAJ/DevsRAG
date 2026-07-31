import logging
import traceback
from sqlmodel import Session, select
from app.database import engine
from app.models import Document, DocumentChunk, DocumentStatus
from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

def process_document_pipeline(
    document_id: str,
    embedding_service: EmbeddingService,
    vector_service: VectorService
):
    """
    Background worker pipeline executing text extraction, chunking, embedding, vector store insertion,
    and DB metadata updates.
    """
    logger.info(f"Starting background pipeline for document: {document_id}")
    
    with Session(engine) as session:
        doc = session.get(Document, document_id)
        if not doc:
            logger.error(f"Pipeline error: Document ID {document_id} not found.")
            return

        try:
            # Step 1: Update status to processing
            doc.status = DocumentStatus.PROCESSING
            doc.status_message = "Extracting and parsing document content..."
            session.add(doc)
            session.commit()

            # Step 2: Parse document
            ext = f".{doc.filename.split('.')[-1]}" if "." in doc.filename else ".txt"
            parse_result = ParserService.parse_file(doc.file_path, ext)
            doc.page_count = parse_result.total_pages

            # Step 3: Chunk text
            doc.status_message = "Generating token chunks..."
            session.add(doc)
            session.commit()
            
            chunker = ChunkerService()
            chunks = chunker.chunk_document(parse_result)
            if not chunks:
                raise ValueError("Document contains no valid text blocks after chunking.")

            # Step 4: Generate Embeddings
            doc.status_message = f"Generating embeddings for {len(chunks)} text chunks..."
            session.add(doc)
            session.commit()

            chunk_texts = [c.content for c in chunks]
            embeddings = embedding_service.embed_texts(chunk_texts)

            # Step 5: Insert into Vector Store (ChromaDB)
            vector_ids = vector_service.upsert_chunks(
                document_id=doc.id,
                document_name=doc.filename,
                chunks=chunks,
                embeddings=embeddings
            )

            # Step 6: Save chunk records to SQL Database
            # Clean up old chunks if re-processing
            existing_chunks = session.exec(select(DocumentChunk).where(DocumentChunk.document_id == doc.id)).all()
            for old_c in existing_chunks:
                session.delete(old_c)

            db_chunks = []
            for idx, c in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    token_count=c.token_count,
                    page_number=c.page_number,
                    vector_id=vector_ids[idx] if idx < len(vector_ids) else f"{doc.id}_{c.chunk_index}"
                )
                db_chunks.append(db_chunk)
                session.add(db_chunk)

            # Step 7: Update document status to ready
            doc.status = DocumentStatus.READY
            doc.chunk_count = len(chunks)
            doc.status_message = "Document processed successfully and indexed for natural language querying."
            session.add(doc)
            session.commit()
            logger.info(f"Successfully processed and indexed document {document_id} with {len(chunks)} chunks.")

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Failed pipeline processing for document {document_id}: {err_msg}\n{traceback.format_exc()}")
            doc.status = DocumentStatus.FAILED
            doc.status_message = f"Processing failed: {err_msg}"
            session.add(doc)
            session.commit()
