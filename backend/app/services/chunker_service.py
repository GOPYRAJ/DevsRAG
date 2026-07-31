from dataclasses import dataclass
from app.services.parser_service import ParseResult

@dataclass
class ChunkItem:
    chunk_index: int
    content: str
    token_count: int
    page_number: int

class ChunkerService:
    def __init__(self, chunk_size_chars: int = 500, overlap_chars: int = 100):
        self.chunk_size_chars = chunk_size_chars
        self.overlap_chars = overlap_chars

    def chunk_document(self, parse_result: ParseResult) -> list[ChunkItem]:
        chunks: list[ChunkItem] = []
        global_chunk_index = 0

        for page in parse_result.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            text_len = len(page_text)

            if text_len <= self.chunk_size_chars:
                chunks.append(
                    ChunkItem(
                        chunk_index=global_chunk_index,
                        content=page_text,
                        token_count=len(page_text.split()),
                        page_number=page.page_number
                    )
                )
                global_chunk_index += 1
            else:
                # Sliding window over character indices (500 chars with 100 char overlap)
                step = self.chunk_size_chars - self.overlap_chars
                if step <= 0:
                    step = self.chunk_size_chars

                start = 0
                while start < text_len:
                    end = min(start + self.chunk_size_chars, text_len)
                    snippet = page_text[start:end].strip()

                    if snippet:
                        chunks.append(
                            ChunkItem(
                                chunk_index=global_chunk_index,
                                content=snippet,
                                token_count=len(snippet.split()),
                                page_number=page.page_number
                            )
                        )
                        global_chunk_index += 1

                    if end >= text_len:
                        break
                    start += step

        return chunks
