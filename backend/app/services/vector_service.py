import logging
from typing import Optional, Dict, Any, List
import chromadb
from app.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name="document_understanding_collection",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(
        self,
        document_id: str,
        document_name: str,
        chunks: List[Any],
        embeddings: List[List[float]]
    ) -> List[str]:
        if not chunks or not embeddings:
            return []

        ids = [f"{document_id}_chunk_{c.chunk_index}" for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "document_name": document_name,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "token_count": c.token_count
            }
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Upserted {len(ids)} vector chunks into ChromaDB for doc {document_id}")
        return ids

    def query_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        scope_document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_clause = None
        if scope_document_id:
            where_clause = {"document_id": scope_document_id}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results = []
        if not results or not results["ids"] or not results["ids"][0]:
            return formatted_results

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for idx in range(len(ids)):
            # Convert cosine distance to cosine similarity score (1 - distance)
            distance = distances[idx] if idx < len(distances) else 1.0
            similarity = 1.0 - distance if distance <= 1.0 else max(0.0, 1.0 - (distance / 2.0))

            formatted_results.append({
                "chunk_id": ids[idx],
                "content": documents[idx] if idx < len(documents) else "",
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "similarity_score": round(similarity, 4)
            })

        return formatted_results

    def delete_document_vectors(self, document_id: str) -> None:
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted vector chunks from ChromaDB for doc {document_id}")
        except Exception as e:
            logger.error(f"Error deleting vectors for doc {document_id}: {e}")
