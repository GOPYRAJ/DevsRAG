import hashlib
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlmodel import Session, select
from app.config import settings
from app.models import Document, DocumentStatus

def compute_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

class FileService:
    @staticmethod
    def validate_file(file: UploadFile) -> str:
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        return ext

    @staticmethod
    async def save_and_create_document(
        file: UploadFile, session: Session, overwrite: bool = True
    ) -> tuple[Document, bool]:
        ext = FileService.validate_file(file)
        
        # Temp save to compute hash and check size
        temp_filename = f"temp_{file.filename}"
        temp_path = settings.UPLOAD_DIR / temp_filename
        
        try:
            file_size = 0
            with open(temp_path, "wb") as buffer:
                while chunk := await file.read(65536):
                    file_size += len(chunk)
                    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB."
                        )
                    buffer.write(chunk)
            
            if file_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty (0 bytes)."
                )

            file_hash = compute_sha256(temp_path)
            
            # Check duplicate by hash or filename
            existing_doc = session.exec(
                select(Document).where((Document.file_hash == file_hash) | (Document.filename == file.filename))
            ).first()

            doc = existing_doc if existing_doc else Document(
                filename=file.filename,
                file_hash=file_hash,
                file_path="",
                file_size_bytes=file_size,
                mime_type=file.content_type or "application/octet-stream",
                status=DocumentStatus.PENDING
            )

            # Update fields if existing
            doc.filename = file.filename
            doc.file_hash = file_hash
            doc.file_size_bytes = file_size
            doc.mime_type = file.content_type or "application/octet-stream"
            doc.status = DocumentStatus.PENDING
            doc.status_message = "File uploaded successfully. Processing queued."

            final_filename = f"{doc.id}{ext}"
            final_path = settings.UPLOAD_DIR / final_filename
            shutil.move(str(temp_path), str(final_path))
            
            doc.file_path = str(final_path)

            session.add(doc)
            session.commit()
            session.refresh(doc)

            return doc, existing_doc is not None
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
