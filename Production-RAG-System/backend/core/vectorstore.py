import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from langchain.schema import Document
from langchain_community.vectorstores import FAISS

from config import FAISS_INDEX_PATH, FAISS_METADATA_PATH
from core.embeddings import get_embeddings

# ── Global state ───────────────────────────────────────────────────────────────
_lock = threading.Lock()
_faiss_instance: Optional[FAISS] = None


# ── Metadata helpers ───────────────────────────────────────────────────────────

def _load_metadata() -> Dict:
    path = Path(FAISS_METADATA_PATH)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"documents": {}}


def _save_metadata(meta: Dict) -> None:
    with open(FAISS_METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def load_vectorstore() -> None:
    """Load the FAISS index from disk on startup (no-op if it doesn't exist yet)."""
    global _faiss_instance
    index_path = Path(FAISS_INDEX_PATH)
    if index_path.exists():
        with _lock:
            _faiss_instance = FAISS.load_local(
                FAISS_INDEX_PATH,
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )


def is_loaded() -> bool:
    return _faiss_instance is not None


def add_documents(
    chunks: List[Document],
    doc_id: str,
    filename: str,
    file_size_bytes: int,
) -> int:
    """Add document chunks to the FAISS index and update metadata.json."""
    global _faiss_instance
    embeddings = get_embeddings()

    with _lock:
        if _faiss_instance is None:
            _faiss_instance = FAISS.from_documents(chunks, embeddings)
        else:
            _faiss_instance.add_documents(chunks)

        _faiss_instance.save_local(FAISS_INDEX_PATH)

        meta = _load_metadata()
        meta["documents"][doc_id] = {
            "filename": filename,
            "file_type": Path(filename).suffix.lower().lstrip("."),
            "chunk_count": len(chunks),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_size_bytes": file_size_bytes,
        }
        _save_metadata(meta)

    return len(chunks)


def delete_document(doc_id: str) -> None:
    """Remove all chunks for doc_id from FAISS by rebuilding the index."""
    global _faiss_instance
    embeddings = get_embeddings()

    with _lock:
        if _faiss_instance is None:
            raise ValueError("Vector store is not loaded.")

        # Filter docstore to exclude the target doc_id
        surviving = [
            doc
            for doc in _faiss_instance.docstore._dict.values()
            if doc.metadata.get("doc_id") != doc_id
        ]

        if surviving:
            _faiss_instance = FAISS.from_documents(surviving, embeddings)
            _faiss_instance.save_local(FAISS_INDEX_PATH)
        else:
            # No documents left — wipe the index files
            import shutil
            index_path = Path(FAISS_INDEX_PATH)
            if index_path.exists():
                shutil.rmtree(index_path, ignore_errors=True)
            _faiss_instance = None

        meta = _load_metadata()
        meta["documents"].pop(doc_id, None)
        _save_metadata(meta)


def list_documents() -> List[Dict]:
    """Return all document records from metadata.json."""
    meta = _load_metadata()
    result = []
    for doc_id, info in meta["documents"].items():
        result.append({"doc_id": doc_id, **info})
    return result


def get_document_info(doc_id: str) -> Optional[Dict]:
    """Return metadata for a single document, or None if not found."""
    meta = _load_metadata()
    info = meta["documents"].get(doc_id)
    if info is None:
        return None
    return {"doc_id": doc_id, **info}


def get_chunk_count() -> int:
    """Return the total number of chunks across all documents."""
    if _faiss_instance is None:
        return 0
    return len(_faiss_instance.docstore._dict)


def get_faiss_instance() -> Optional[FAISS]:
    return _faiss_instance
