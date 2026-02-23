# Regulatory Impact Analysis Agent

A 5-node LangGraph agent that accepts regulatory documents (PDF, URL, plain text, or RSS feed), extracts structured clauses, classifies industry relevance, scores impact severity, and generates industry-specific compliance action plans.

## Architecture

```
Document Parser → Clause Extractor → Industry Classifier → Impact Assessor → Action Plan Generator
```

- **Node 1 — Document Parser:** Ingests PDF/URL/text/RSS and extracts structured metadata
- **Node 2 — Clause Extractor:** LLM-based extraction of regulatory clauses (32-type vocabulary)
- **Node 3 — Industry Classifier:** Rule-based + LLM classification (Financial Services / Healthcare)
- **Node 4 — Impact Assessor:** Severity scoring per clause with affected business functions
- **Node 5 — Action Plan Generator:** Industry-specific compliance action plan with streaming

## Tech Stack

- **LLM:** Ollama (llama3.2) — runs locally
- **Agent Framework:** LangGraph + LangChain
- **API:** FastAPI with SSE streaming
- **Frontend:** Streamlit 4-tab UI
- **PDF:** pdfplumber
- **Web:** httpx + BeautifulSoup
- **RSS:** feedparser

## Quick Start

### Prerequisites
- [Ollama](https://ollama.ai) installed and running
- Python 3.11+

### Local Setup

```bash
# Pull the model
ollama pull llama3.2

# Install and run backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# In another terminal — install and run frontend
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Or use the Makefile:

```bash
make install      # install both backend + frontend deps
make run          # run both services
make pull-model   # pull llama3.2 via ollama
```

### Docker

```bash
docker compose up --build
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:8501
- Ollama: http://localhost:11434

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | System health + Ollama status |
| POST | /api/ingest/pdf | Upload PDF file |
| POST | /api/ingest/url | Ingest from URL |
| POST | /api/ingest/text | Ingest plain text |
| POST | /api/ingest/rss | Poll RSS feed |
| POST | /api/analyze | Blocking analysis |
| POST | /api/analyze/stream | SSE streaming analysis |
| GET | /api/feeds/list | List known regulatory feeds |
| GET | /api/feeds/poll | Poll a specific RSS feed |

## Supported Industries

- **Financial Services:** Banking capital, payments, consumer protection, AML/KYC, data privacy/fintech
- **Healthcare:** Pharma/clinical trials, medical devices, HIPAA data privacy, pharmacovigilance, billing/coding

## Known Regulatory Feeds

Financial: Federal Reserve, OCC, CFPB, SEC, EBA
Healthcare: FDA News, FDA Guidance, CMS, EMA
