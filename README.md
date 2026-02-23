# GenAI-Projects

A collection of production-style Generative AI and AI Agent projects. Each project demonstrates a real-world use case built with modern frameworks — designed to help you understand how to build GenAI products from scratch.

<img width="2000" height="600" alt="image" src="https://github.com/user-attachments/assets/40caa6bf-52cf-4fb1-9e02-771e9cd84a95" />

---

## At a Glance

| | |
|---|---|
| **Projects** | 9 |
| **LLM Providers** | OpenAI GPT · Ollama (llama3.2, local) |
| **Primary Agent Framework** | LangGraph (5 of 8 projects) |
| **Languages** | Python 3.10+ |
| **Deployment** | Docker Compose (all backend projects) |

---

## Projects

### Agent Pipelines

Multi-node LangGraph pipelines with FastAPI backends, Streamlit frontends, and SSE streaming.

| # | Project | Pipeline | Description |
|---|---------|----------|-------------|
| 4 | [Multi-Agent Research System](./Multi-Agent-Research-System) | Source Gatherer → Citation Verifier → Report Writer | Researches a topic from URLs and produces a fully cited Markdown report |
| 6 | [Regulatory Impact Analysis Agent](./Regulatory-Impact-Analysis-Agent) | Document Parser → Clause Extractor → Industry Classifier → Impact Assessor → Action Plan Generator | Ingests regulatory documents (PDF · URL · text · RSS), extracts clauses, scores severity, and streams compliance action plans |
| 7 | [Strategic Simulation Agent](./Strategic-Simulation-Agent) | Decision Framer → Scenario Generator → Outcome Simulator → Risk Analyzer → Report Generator | Takes any business decision, generates Bull / Base / Bear / Tail Risk scenarios, projects quantitative outcomes, scores risks, and streams a strategic report |
| 8 | [Knowledge Graph Agent](./Knowledge-Graph-Agent) | Document Ingester → Entity Extractor → Relationship Extractor → Graph Builder → Graph Summarizer | Extracts typed entities and relationships from any domain document, builds a queryable NetworkX graph, and enables semantic querying with interactive pyvis visualization |
| 9 | [Narrative Intelligence Agent](./Narrative-Intelligence-Agent) | Source Aggregator → Sentiment Analyzer → Narrative Extractor → Pattern Mapper → Intelligence Reporter | Aggregates RSS feeds, URLs, and social text; detects sentiment shifts; classifies narratives as dominant / emerging / contested / fringe; maps meta-patterns (echo chambers, divergence, amplification); streams a strategic intelligence brief |

### RAG & Retrieval

| # | Project | Description |
|---|---------|-------------|
| 3 | [Production RAG System](./Production-RAG-System) | Fully containerized retrieval-augmented generation system with document ingestion, FAISS vector search, chunking strategies, and SSE streaming |

### Conversational Agents

| # | Project | Description |
|---|---------|-------------|
| 1 | [Customer Support Agent](./Customer-Support-Agent) | Multi-step state machine that categorizes queries, analyzes sentiment, and routes to AI response or human escalation |
| 2 | [Data Analysis Agent](./Data-Analysis-Agent) | Conversational agent that translates natural language questions into pandas code and executes them against any CSV |

### Computer Vision

| # | Project | Description |
|---|---------|-------------|
| 5 | [Intrusion Detection System](./Intrusion-Detection-System) | Real-time person detection in user-defined restricted zones with email and desktop alert notifications |

---

## Full Project Index

| # | Project | Stack |
|---|---------|-------|
| 1 | [Customer Support Agent](./Customer-Support-Agent) | LangGraph · LangChain · OpenAI |
| 2 | [Data Analysis Agent](./Data-Analysis-Agent) | PydanticAI · Pandas · OpenAI |
| 3 | [Production RAG System](./Production-RAG-System) | FastAPI · Streamlit · Ollama · FAISS · Docker Compose |
| 4 | [Multi-Agent Research System](./Multi-Agent-Research-System) | LangGraph · FastAPI · Streamlit · Ollama · Docker Compose |
| 5 | [Intrusion Detection System](./Intrusion-Detection-System) | YOLOv11 · OpenCV · SMTP · plyer |
| 6 | [Regulatory Impact Analysis Agent](./Regulatory-Impact-Analysis-Agent) | LangGraph · FastAPI · Streamlit · Ollama · pdfplumber · feedparser · Docker Compose |
| 7 | [Strategic Simulation Agent](./Strategic-Simulation-Agent) | LangGraph · FastAPI · Streamlit · Ollama · Docker Compose |
| 8 | [Knowledge Graph Agent](./Knowledge-Graph-Agent) | LangGraph · FastAPI · Streamlit · NetworkX · pyvis · Ollama · Docker Compose |
| 9 | [Narrative Intelligence Agent](./Narrative-Intelligence-Agent) | LangGraph · FastAPI · Streamlit · Plotly · feedparser · BeautifulSoup4 · Ollama · Docker Compose |

---

## Getting Started

Each project is self-contained with its own `README.md`, `requirements.txt`, and `.env.example`.

```bash
git clone https://github.com/Ramakm/GenAI-Projects.git
cd GenAI-Projects/<project-name>
```

### Prerequisites for LangGraph projects (4, 6, 7, 8)

```bash
# Install Ollama and pull the model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# Install backend dependencies
cd <project>/backend && pip install -r requirements.txt
uvicorn main:app --reload

# Install frontend dependencies (new terminal)
cd <project>/frontend && pip install -r requirements.txt
streamlit run app.py
```

### Docker (all LangGraph projects)

```bash
docker compose up --build -d
docker exec <container>-ollama ollama pull llama3.2
```

---

## Repository Structure

```
GenAI-Projects/
├── README.md
├── LICENSE
├── Customer-Support-Agent/
├── Data-Analysis-Agent/
├── Production-RAG-System/
├── Multi-Agent-Research-System/
├── Intrusion-Detection-System/
├── Regulatory-Impact-Analysis-Agent/
├── Strategic-Simulation-Agent/
├── Knowledge-Graph-Agent/
└── Narrative-Intelligence-Agent/
```

---

## Tech Stack (across projects)

| Category | Technologies |
|----------|-------------|
| LLM Providers | OpenAI GPT, Ollama (local — llama3.2) |
| Agent Frameworks | LangGraph, LangChain, PydanticAI |
| Backend | FastAPI, uvicorn |
| Frontend | Streamlit |
| Graph Analysis | NetworkX, pyvis |
| Data Visualization | Plotly |
| Media Ingestion | feedparser (RSS/Atom), httpx, BeautifulSoup4 |
| Vector Search | FAISS |
| Document Parsing | pdfplumber, BeautifulSoup4, httpx |
| Feed Ingestion | feedparser (RSS/Atom) |
| Computer Vision | YOLOv11, OpenCV |
| Infrastructure | Docker, Docker Compose |
| Data / Validation | Pydantic, Pandas |
| Language | Python 3.10+ |

---

## LangGraph Architecture Pattern

Projects 4, 6, 7, and 8 share a consistent architecture:

```
FastAPI (lifespan + CORS)
  └── LangGraph StateGraph (linear pipeline)
        ├── Node 1..N  (sync, LLM JSON calls)
        └── Node N     (streamed token-by-token via Ollama /api/chat)
              ↕ SSE
Streamlit frontend
  ├── 5-column agent progress strip
  ├── Streaming report / summary placeholder
  └── Results tabs + downloads
```

SSE event sequence: `agent_start` → `agent_update` (×N) → `agent_complete` → `token` (streamed) → `done`

---

## Contributing

Contributions are welcome. To add a new project:

1. Fork the repository
2. Create a new folder with a descriptive name
3. Include a `README.md`, `requirements.txt`, and `.env.example`
4. Submit a pull request

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Built by Ramakrushna Mohapatra

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://instagram.com/techwith.ram)
[![](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://twitter.com/techwith_ram)
[![Substack](https://img.shields.io/badge/-Substack-FF6719?style=flat&logo=substack&logoColor=white)](https://growtechie.substack.com)
