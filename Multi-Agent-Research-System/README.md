# Multi-Agent Research System

A production-grade research pipeline powered by three specialized AI agents:

```
Source Gatherer → Citation Verifier → Report Writer
```

**Stack**: Ollama · LangGraph · FastAPI · Streamlit · Docker Compose · BeautifulSoup4

---

## Architecture

| Layer | Technology | Role |
|-------|-----------|------|
| Orchestration | LangGraph `StateGraph` | Linear agent pipeline |
| LLM | Ollama (`llama3.2`) | Claim extraction, relevance scoring, report writing |
| Backend | FastAPI + uvicorn | REST + SSE streaming endpoints |
| Frontend | Streamlit | Interactive UI with live progress |
| Scraping | requests + BeautifulSoup4 | URL fetching and text extraction |
| Infrastructure | Docker Compose | Three services: ollama, backend, frontend |

### Agent Pipeline

1. **Source Gatherer** — Fetches each URL (10s timeout, browser User-Agent), strips HTML noise, extracts 3–8 factual claims via LLM.
2. **Citation Verifier** — Scores each source: domain trust (.edu/.gov=0.7, .org=0.6, else=0.4) × 0.3 + LLM relevance × 0.7. Marks sources as usable if `confidence ≥ 0.3`.
3. **Report Writer** — Compiles a structured Markdown report with inline citations, executive summary, key findings, detailed analysis, source table, and references.

---

## Quick Start

```bash
# 1. Clone and configure
cd Multi-Agent-Research-System
cp .env.example .env

# 2. Build and start all services
make build && make up

# 3. Pull the LLM (first time only — ~2 GB)
make pull-model

# 4. Verify
make test-health         # {"status": "healthy", "ollama_connected": true, ...}

# 5. Open UI
open http://localhost:8501       # Streamlit UI
open http://localhost:8000/docs  # Swagger / OpenAPI
```

---

## API Endpoints

### `GET /health`
Returns system status including Ollama connectivity and model availability.

```json
{
  "status": "healthy",
  "ollama_connected": true,
  "model_available": true,
  "available_models": ["llama3.2:latest"],
  "version": "1.0.0"
}
```

### `POST /api/research` (blocking)
Run the full pipeline and return the final report.

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Benefits of renewable energy",
    "urls": [
      "https://en.wikipedia.org/wiki/Renewable_energy",
      "https://www.energy.gov/eere/renewable-energy"
    ]
  }'
```

### `POST /api/research/stream` (SSE)
Same request body as above. Returns a stream of SSE events:

| Event | Description |
|-------|-------------|
| `agent_start` | Agent begins processing |
| `agent_update` | Per-URL/per-source progress |
| `agent_complete` | Agent finishes |
| `token` | Report Writer text tokens (streamed) |
| `done` | Final `ResearchResponse` payload |
| `error` | Fatal error in an agent |

---

## Configuration

All settings via `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Model to use |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature |
| `MAX_URLS` | `10` | Max URLs per request |
| `FETCH_TIMEOUT` | `10` | HTTP fetch timeout (seconds) |
| `MAX_TEXT_CHARS` | `4000` | Max chars extracted per page |
| `BACKEND_URL` | `http://localhost:8000` | Frontend → backend URL |

---

## Development

### Run backend locally

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # edit OLLAMA_BASE_URL if needed
uvicorn main:app --reload --port 8000
```

### Run frontend locally

```bash
cd frontend
pip install -r requirements.txt
cp ../.env.example .env
streamlit run app.py
```

---

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make build` | Build Docker images |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | Tail logs (add `service=backend` to filter) |
| `make pull-model` | Pull Ollama model into running container |
| `make clean` | Remove containers, images, volumes |
| `make test-health` | Quick health check |
| `make test-research` | Sample research request |

---

## Project Structure

```
Multi-Agent-Research-System/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── main.py              # FastAPI app + lifespan warmup
│   ├── config.py            # Env-var config
│   ├── requirements.txt
│   ├── api/
│   │   ├── models/
│   │   │   ├── request.py   # ResearchRequest
│   │   │   └── response.py  # ResearchResponse, CitationResponse, HealthResponse
│   │   └── routes/
│   │       ├── health.py    # GET /health
│   │       └── research.py  # POST /api/research + /api/research/stream
│   └── agents/
│       ├── state.py         # ResearchState TypedDict
│       ├── source_gatherer.py
│       ├── citation_verifier.py
│       ├── report_writer.py
│       └── graph.py         # LangGraph pipeline
└── frontend/
    ├── Dockerfile
    ├── app.py               # Streamlit UI
    ├── config.py
    └── requirements.txt
```
