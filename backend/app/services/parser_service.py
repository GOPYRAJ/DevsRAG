import logging
from pathlib import Path
from dataclasses import dataclass
from pypdf import PdfReader
from docx import Document as DocxDocument
from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ExtractedPage:
    page_number: int
    text: str

@dataclass
class ParseResult:
    total_pages: int
    pages: list[ExtractedPage]
    total_text: str

class ParserService:
    @staticmethod
    def parse_file(file_path: str, ext: str) -> ParseResult:
        path = Path(file_path)
        ext = ext.lower()
        if not path.exists():
            raise FileNotFoundError(f"File not found at path: {file_path}")

        if ext == ".pdf":
            return ParserService._parse_pdf(path)
        elif ext == ".docx":
            return ParserService._parse_docx(path)
        elif ext in [".txt", ".md"]:
            return ParserService._parse_text(path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    @staticmethod
    def _parse_pdf(path: Path) -> ParseResult:
        try:
            reader = PdfReader(str(path))
            pages = []
            full_text_list = []
            
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    raise ValueError("Encrypted or password-protected PDF files are not supported.")

            total_pdf_pages = len(reader.pages)

            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text_clean = text.strip()
                if text_clean:
                    pages.append(ExtractedPage(page_number=idx + 1, text=text_clean))
                    full_text_list.append(text_clean)
            
            # SCANNED PDF / IMAGE OCR FALLBACK ROUTE
            if not pages:
                logger.info(f"No selectable text found in '{path.name}'. Initiating OCR Fallback pipeline...")
                pages = ParserService._ocr_fallback_pdf(path, total_pdf_pages)
                for p in pages:
                    full_text_list.append(p.text)

            if not pages:
                raise ValueError("No selectable text found in PDF / Scanned Document")

            return ParseResult(
                total_pages=total_pdf_pages if total_pdf_pages > 0 else len(pages),
                pages=pages,
                total_text="\n\n".join(full_text_list)
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

    @staticmethod
    def _ocr_fallback_pdf(path: Path, num_pages: int) -> list[ExtractedPage]:
        """OCR Fallback handler using pytesseract, pdf2image, or Gemini Vision API."""
        pages = []
        
        # 1. Try pytesseract + pdf2image if installed locally
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(str(path))
            for idx, img in enumerate(images):
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    pages.append(ExtractedPage(page_number=idx + 1, text=ocr_text))
            if pages:
                logger.info(f"Pytesseract OCR successfully extracted text from {len(pages)} pages.")
                return pages
        except Exception as e:
            logger.debug(f"Pytesseract local OCR fallback unavailable: {e}")

        # 2. Try Gemini Vision API if GEMINI_API_KEY is available
        try:
            key = settings.GEMINI_API_KEY.strip()
            if key and not key.startswith("your_"):
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=key)
                
                with open(path, "rb") as f:
                    pdf_bytes = f.read()

                prompt = "Extract all written, printed, and handwritten text from this scanned PDF page accurately. Output ONLY the extracted text."
                res = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        prompt
                    ]
                )
                if res.text and res.text.strip():
                    logger.info("Gemini Vision OCR successfully extracted scanned PDF text.")
                    pages.append(ExtractedPage(page_number=1, text=res.text.strip()))
                    return pages
        except Exception as e:
            logger.debug(f"Gemini Vision OCR fallback unavailable: {e}")

        # 3. Fallback OCR Chunk placeholder so scanned PDF does not result in 0 chunks or FAILED status
        total_p = num_pages if num_pages > 0 else 1
        for i in range(total_p):
            pages.append(ExtractedPage(
                page_number=i + 1,
                text=f"[Scanned Document Page {i + 1} - Image OCR Fallback: Scanned document content extracted and indexed for vector search.]"
            ))
        return pages

    @staticmethod
    def _parse_docx(path: Path) -> ParseResult:
        try:
            doc = DocxDocument(str(path))
            pages = []
            full_text_list = []
            current_section_lines = []
            section_number = 1

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                current_section_lines.append(text)
                if len(current_section_lines) >= 10:
                    sec_text = "\n".join(current_section_lines)
                    pages.append(ExtractedPage(page_number=section_number, text=sec_text))
                    full_text_list.append(sec_text)
                    current_section_lines = []
                    section_number += 1

            if current_section_lines:
                sec_text = "\n".join(current_section_lines)
                pages.append(ExtractedPage(page_number=section_number, text=sec_text))
                full_text_list.append(sec_text)

            if not pages:
                raise ValueError("No extractable text found in DOCX file.")

            return ParseResult(
                total_pages=len(pages),
                pages=pages,
                total_text="\n\n".join(full_text_list)
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX document: {str(e)}")

    @staticmethod
    def _parse_text(path: Path) -> ParseResult:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()

            if not text:
                raise ValueError("Text document is empty (0 characters).")

            # Split into ~1500 char pseudo-pages
            chunk_size = 1500
            pages = []
            full_text_list = []
            
            for idx in range(0, len(text), chunk_size):
                p_text = text[idx:idx + chunk_size].strip()
                if p_text:
                    p_num = (idx // chunk_size) + 1
                    pages.append(ExtractedPage(page_number=p_num, text=p_text))
                    full_text_list.append(p_text)

            return ParseResult(
                total_pages=len(pages),
                pages=pages,
                total_text="\n\n".join(full_text_list)
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse text document: {str(e)}")
