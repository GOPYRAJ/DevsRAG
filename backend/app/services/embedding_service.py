import logging
import math
import re
from app.config import settings

logger = logging.getLogger(__name__)

def _local_hash_embedding(text: str, dim: int = 384) -> list[float]:
    """
    Enhanced deterministic feature-hash vectorizer with exact sub-word n-gram support.
    Ensures exact terms (e.g. 'GEMINI_API_KEY', technical settings, numbers) score high similarity.
    Dimensions fixed to 384 for ChromaDB compatibility.
    """
    tokens = re.findall(r'[A-Za-z0-9_]+', text)
    vec = [0.0] * dim
    if not tokens:
        return vec

    for token in tokens:
        token_lower = token.lower()
        # Word-level hashes
        h1 = sum(ord(c) * (31 ** i) for i, c in enumerate(token_lower)) % dim
        h2 = sum(ord(c) * (17 ** i) for i, c in enumerate(token_lower)) % dim
        vec[h1] += 2.0
        vec[h2] += 1.0

        # Exact case match boost
        if token.isupper() or "_" in token:
            h_exact = sum(ord(c) * (37 ** i) for i, c in enumerate(token)) % dim
            vec[h_exact] += 3.0

        # Character tri-gram hashes for partial/exact keyword matches
        if len(token_lower) >= 3:
            for i in range(len(token_lower) - 2):
                ngram = token_lower[i:i+3]
                h_ng = sum(ord(c) * (13 ** j) for j, c in enumerate(ngram)) % dim
                vec[h_ng] += 0.5

    # Normalize vector to unit length
    magnitude = math.sqrt(sum(x * x for x in vec))
    if magnitude > 0:
        vec = [x / magnitude for x in vec]
    return vec

class EmbeddingService:
    def __init__(self):
        self.gemini_client = None
        self.openai_client = None
        
        key = settings.GEMINI_API_KEY.strip()
        if key and not key.startswith("your_"):
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=key)
                logger.info("Initialized Google Gemini embedding client successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini embedding client: {e}")

        o_key = settings.OPENAI_API_KEY.strip()
        if o_key and not o_key.startswith("your_"):
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=o_key)
                logger.info("Initialized OpenAI embedding client successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI embedding client: {e}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # Try Gemini API if client is initialized
        if self.gemini_client:
            try:
                embeddings = []
                for text in texts:
                    res = self.gemini_client.models.embed_content(
                        model="text-embedding-004",
                        contents=text
                    )
                    embeddings.append(res.embedding.values)
                return embeddings
            except Exception as e:
                logger.error(f"Gemini embedding API call failed: {e}. Falling back to local hash vectorizer...")

        # Try OpenAI API if client is initialized
        if self.openai_client:
            try:
                res = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                return [data.embedding for data in res.data]
            except Exception as e:
                logger.error(f"OpenAI embedding API call failed: {e}. Falling back to local hash vectorizer...")

        # Fallback local hash embedder
        return [_local_hash_embedding(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        results = self.embed_texts([query])
        return results[0] if results else _local_hash_embedding(query)
