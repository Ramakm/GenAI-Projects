# GenAI-Projects

A collection of production-style Generative AI and AI Agent projects. Each project demonstrates a real-world use case built with modern frameworks — designed to help you understand how to build GenAI products from scratch.

<img width="2000" height="600" alt="image" src="https://github.com/user-attachments/assets/40caa6bf-52cf-4fb1-9e02-771e9cd84a95" />

---

## Projects

| # | Project | Description | Stack |
|---|---------|-------------|-------|
| 1 | [Customer Support Agent](./Customer-Support-Agent) | Multi-step state machine that categorizes queries, analyzes sentiment, and routes to AI response or human escalation | LangGraph · LangChain · OpenAI |
| 2 | [Data Analysis Agent](./Data-Analysis-Agent) | Conversational agent that translates natural language questions into pandas code and executes them against any CSV | PydanticAI · Pandas · OpenAI |
| 3 | [Production RAG System](./Production-RAG-System) | Fully containerized retrieval-augmented generation system with document ingestion, FAISS vector search, and SSE streaming | FastAPI · Streamlit · Ollama · FAISS · Docker Compose |
| 4 | [Multi-Agent Research System](./Multi-Agent-Research-System) | Three-agent pipeline (Source Gatherer → Citation Verifier → Report Writer) that researches URLs and produces a cited Markdown report | LangGraph · FastAPI · Streamlit · Ollama · Docker Compose |
| 5 | [Intrusion Detection System](./Intrusion-Detection-System) | Real-time person detection in user-defined restricted zones with email and desktop alert notifications | YOLOv11 · OpenCV · SMTP · plyer |
| 6 | [Regulatory Impact Analysis Agent](./Regulatory-Impact-Analysis-Agent) | 5-node LangGraph pipeline that ingests regulatory documents (PDF, URL, text, RSS), extracts structured clauses, classifies industry, scores severity, and generates compliance action plans with SSE streaming | LangGraph · FastAPI · Streamlit · Ollama · pdfplumber · feedparser · Docker Compose |

---

## Getting Started

Each project is self-contained with its own `README.md`, `requirements.txt`, and `.env.example`. Refer to the individual project README for setup and usage instructions.

```bash
git clone https://github.com/Ramakm/GenAI-Projects.git
cd GenAI-Projects/<project-name>
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
└── Regulatory-Impact-Analysis-Agent/
```

---

## Tech Stack (across projects)

| Category | Technologies |
|----------|-------------|
| LLM Providers | OpenAI GPT, Ollama (local — llama3.2) |
| Agent Frameworks | LangGraph, LangChain, PydanticAI |
| Backend | FastAPI, uvicorn |
| Frontend | Streamlit |
| Vector Search | FAISS |
| Document Parsing | pdfplumber, BeautifulSoup4, httpx |
| Feed Ingestion | feedparser (RSS/Atom) |
| Computer Vision | YOLOv11, OpenCV |
| Infrastructure | Docker, Docker Compose |
| Data / Validation | Pydantic, Pandas |
| Language | Python 3.10+ |

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
