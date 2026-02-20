# Production RAG System

A production-grade Retrieval-Augmented Generation (RAG) system using a microservices architecture.

## Stack

| Component | Technology |
|-----------|------------|
| LLM | Ollama (local, runs any GGUF model) |
| Vector DB | FAISS (CPU, thread-safe via Lock) |
| Backend API | FastAPI + SSE streaming |
| Frontend | Streamlit |
| Orchestration | Docker Compose |

## Quick Start

```bash
# 1. Clone / enter project directory
cd Production-RAG-System

# 2. Configure environment
cp .env.example .env

# 3. Build and start all services
make build && make up

# 4. Pull an LLM model (first time — ~2-5 GB download)
make pull-model

# 5. Verify health
make test-health

# 6. Upload a test document and query
make test-upload
make test-query

# 7. Open the web UI
open http://localhost:8501

# 8. Explore the API (Swagger UI)
open http://localhost:8000/docs
```

## Service URLs

| Service | URL |
|---------|-----|
| Frontend (Streamlit) | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

## Supported Document Formats

PDF, DOCX, TXT, MD, HTML, CSV, XLSX, PPTX

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| POST | `/api/documents/upload` | Upload a document |
| GET | `/api/documents` | List all indexed documents |
| DELETE | `/api/documents/{doc_id}` | Delete a document |
| POST | `/api/query` | Ask a question (blocking) |
| POST | `/api/query/stream` | Ask a question (SSE streaming) |

## Architecture

```
User → Streamlit (port 8501)
         ↓ HTTP / SSE
       FastAPI (port 8000)
         ├── FAISS vector store (persistent volume)
         └── Ollama (port 11434)
```

## Makefile Targets

```
make build        # Build Docker images
make up           # Start services
make down         # Stop services
make logs         # Tail logs
make pull-model   # Pull LLM into Ollama
make clean        # Remove containers + volumes + images
make test-health  # Curl health endpoint
make test-upload  # Upload a sample .txt file
make test-query   # Run a sample question
```

## Configuration

All settings are controlled via `.env` (copied from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2` | LLM to use |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `TOP_K` | `5` | Chunks retrieved per query |
| `LLM_TEMPERATURE` | `0.1` | LLM generation temperature |
| `MAX_UPLOAD_MB` | `50` | Max file upload size |

## Key Technical Decisions

- **1 uvicorn worker**: FAISS is not multi-process safe. A single process with `threading.Lock` is used.
- **metadata.json sidecar**: FAISS has no native document metadata; a JSON file tracks doc registry.
- **FAISS delete = rebuild**: `IndexFlatL2` has no selective delete; the index is rebuilt from the docstore.
- **`lru_cache` for embeddings**: Prevents reloading the 90 MB embedding model on every request.
- **Pre-download model in Dockerfile**: The embedding model is baked into the backend image to avoid delays.
- **SSE sources event first**: Streaming returns retrieved sources before tokens, improving UX.
