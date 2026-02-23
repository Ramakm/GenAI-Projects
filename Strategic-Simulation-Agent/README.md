# Strategic Simulation Agent

A 5-node LangGraph agent that takes a plain-text business decision description and generates probabilistic scenario analysis, quantitative outcome projections, risk factor scoring, and a streamed strategic report.

## Architecture

```
Decision Framer → Scenario Generator → Outcome Simulator → Risk Analyzer → Report Generator
```

- **Node 1 — Decision Framer**: Classifies decision type and extracts key parameters
- **Node 2 — Scenario Generator**: Generates Bull / Base / Bear / Tail Risk scenarios with normalized probabilities
- **Node 3 — Outcome Simulator**: Projects quantitative outcomes per scenario, computes expected value
- **Node 4 — Risk Analyzer**: Identifies up to 10 risk factors across 5 categories, computes risk scores
- **Node 5 — Report Generator**: Streams a comprehensive strategic report, applies rule-based recommendation

## Stack

- **Backend**: FastAPI + LangGraph + Ollama (llama3.2)
- **Frontend**: Streamlit (3-tab UI)
- **LLM**: Ollama llama3.2 (local)

## Quick Start

### Prerequisites

```bash
ollama pull llama3.2
```

### Run locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Or use Make:
```bash
make install-backend install-frontend
make run-backend   # terminal 1
make run-frontend  # terminal 2
```

### Docker

```bash
docker compose up --build -d
# Pull model inside ollama container:
docker exec ssa-ollama ollama pull llama3.2
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| POST | `/api/simulate` | Blocking simulation |
| POST | `/api/simulate/stream` | SSE streaming simulation |
| POST | `/api/decisions` | Store a decision |
| GET | `/api/decisions/{id}` | Retrieve stored decision |

## Key Algorithms

| Component | Algorithm |
|-----------|-----------|
| Scenario probabilities | Normalized post-parse: `p_i = p_i / sum(all_p)` |
| Expected value | `EV = Σ(prob_i × revenue_impact_pct_i)` — pure Python |
| Risk score | `risk_score = likelihood × impact` — pure Python |
| Recommendation | Rule-based on EV + overall_risk_score thresholds |
| Confidence | `std(probabilities)` < 0.10 → high, > 0.18 → low |

## Scenarios

| Scenario | Description |
|----------|-------------|
| Bull Case | Optimistic — favorable conditions, strong execution |
| Base Case | Most likely — moderate conditions |
| Bear Case | Pessimistic — challenging conditions |
| Tail Risk | Extreme downside — severe disruption |
