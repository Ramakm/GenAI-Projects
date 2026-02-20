import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File

from api.models.response import DocumentInfo, DeleteResponse, UploadResponse
from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, UPLOADS_DIR
from core.document_loader import load_from_bytes
from core.text_splitter import split_documents
from core.vectorstore import add_documents, delete_document, get_document_info, list_documents

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """Upload and index a document."""
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    doc_id = str(uuid.uuid4())

    # Persist original file to disk (optional: useful for re-indexing)
    upload_path = UPLOADS_DIR / f"{doc_id}{ext}"
    upload_path.write_bytes(file_bytes)

    # Load, split, and index
    try:
        docs = load_from_bytes(file_bytes, file.filename, doc_id)
        chunks = split_documents(docs)
        chunk_count = add_documents(chunks, doc_id, file.filename, len(file_bytes))
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {exc}")

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        chunk_count=chunk_count,
        message=f"Document '{file.filename}' indexed successfully with {chunk_count} chunks.",
    )


@router.get("", response_model=List[DocumentInfo])
def get_documents() -> List[DocumentInfo]:
    """List all indexed documents."""
    docs = list_documents()
    return [DocumentInfo(**d) for d in docs]


@router.delete("/{doc_id}", response_model=DeleteResponse)
def remove_document(doc_id: str) -> DeleteResponse:
    """Delete a document and all its chunks from the index."""
    info = get_document_info(doc_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    filename = info["filename"]
    file_type = info.get("file_type", "")

    try:
        delete_document(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {exc}")

    # Remove the raw upload from disk (best-effort)
    upload_path = UPLOADS_DIR / f"{doc_id}.{file_type}"
    upload_path.unlink(missing_ok=True)

    return DeleteResponse(
        doc_id=doc_id,
        filename=filename,
        message=f"Document '{filename}' deleted successfully.",
    )
