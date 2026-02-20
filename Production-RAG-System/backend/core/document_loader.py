import os
import tempfile
from pathlib import Path
from typing import List

from langchain.schema import Document


def load_from_bytes(file_bytes: bytes, filename: str, doc_id: str) -> List[Document]:
    """Load documents from raw bytes, dispatching by file extension.

    Injects doc_id and filename into every document's metadata.
    """
    ext = Path(filename).suffix.lower()
    docs: List[Document] = []

    if ext in (".txt", ".md"):
        text = file_bytes.decode("utf-8", errors="replace")
        docs = [Document(page_content=text)]

    elif ext == ".html":
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(file_bytes, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        docs = [Document(page_content=text)]

    elif ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        docs = _load_via_tempfile(file_bytes, ".pdf", PyPDFLoader)

    elif ext == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        docs = _load_via_tempfile(file_bytes, ".docx", Docx2txtLoader)

    elif ext == ".xlsx":
        from langchain_community.document_loaders import UnstructuredExcelLoader
        docs = _load_via_tempfile(file_bytes, ".xlsx", UnstructuredExcelLoader)

    elif ext == ".csv":
        from langchain_community.document_loaders.csv_loader import CSVLoader
        docs = _load_via_tempfile(file_bytes, ".csv", CSVLoader)

    elif ext == ".pptx":
        from langchain_community.document_loaders import UnstructuredPowerPointLoader
        docs = _load_via_tempfile(file_bytes, ".pptx", UnstructuredPowerPointLoader)

    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    # Inject metadata into every page / chunk
    for doc in docs:
        doc.metadata["doc_id"] = doc_id
        doc.metadata["filename"] = filename
        doc.metadata["source"] = filename

    return docs


def _load_via_tempfile(file_bytes: bytes, suffix: str, loader_cls) -> List[Document]:
    """Write bytes to a temp file, load with loader_cls, then clean up."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        loader = loader_cls(tmp_path)
        return loader.load()
    finally:
        os.unlink(tmp_path)
