# Narrative Intelligence Agent

A 5-node LangGraph agent that aggregates media coverage and social discussions, detects sentiment shifts, and maps evolving narrative patterns — delivering a streamed intelligence brief.

## Architecture

```
Source Aggregator → Sentiment Analyzer → Narrative Extractor → Pattern Mapper → Intelligence Reporter
```

| Node | Responsibility |
|------|---------------|
| **Source Aggregator** | Ingest RSS feeds (feedparser), URLs (httpx + BeautifulSoup), or pasted text; normalize to Article TypedDict |
| **Sentiment Analyzer** | Batch LLM sentiment scoring (−1.0 to +1.0); compute overall score, distribution, per-source averages, and shift signal |
| **Narrative Extractor** | Identify up to 8 distinct narratives with type, framing, key claims, key actors, and momentum score |
| **Pattern Mapper** | Detect meta-patterns (convergence, divergence, echo chamber, amplification, suppression, reversal); extract global key actors and claims |
| **Intelligence Reporter** | Extract 3–5 key insights + stream a full intelligence brief with strategic implications |

## Narrative Types

| Type | Meaning |
|------|---------|
| `dominant` | Widely repeated across most sources |
| `emerging` | Gaining traction, limited coverage |
| `fading` | Present but declining |
| `contested` | Actively disputed between sources |
| `fringe` | Minority view, limited reach |

## Pattern Types

`convergence` · `divergence` · `amplification` · `suppression` · `reversal` · `echo_chamber`

## Stack

- **Backend**: FastAPI + LangGraph + Ollama (llama3.2) + feedparser + BeautifulSoup4
- **Frontend**: Streamlit + Plotly (sentiment gauge, source bars, type distribution)
- **Sources**: RSS feeds · web URLs · pasted text

## Preset Topics

| Preset | Topic | Feed Category |
|--------|-------|---------------|
| `ai_tech` | Artificial Intelligence & Technology | technology |
| `climate_change` | Climate Change & Environment | climate |
| `global_markets` | Global Financial Markets | finance |
| `geopolitics` | Geopolitics & International Relations | general_news |

## Quick Start

```bash
ollama pull llama3.2

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend && pip install -r requirements.txt
streamlit run app.py
```

Or via Make:
```bash
make install-backend install-frontend
make run-backend    # terminal 1
make run-frontend   # terminal 2
```

### Docker

```bash
docker compose up --build -d
docker exec nia-ollama ollama pull llama3.2
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| POST | `/api/analyze` | Blocking full analysis |
| POST | `/api/analyze/stream` | SSE streaming analysis |
| POST | `/api/topics` | Store topic configuration |
| GET | `/api/topics/{id}` | Retrieve stored topic |
| GET | `/api/feeds/presets` | Available RSS feed presets |
| GET | `/api/topics/presets` | Available topic presets |

## SSE Event Sequence

```
agent_start    source_aggregator     "Aggregating media sources..."
agent_update   source_aggregator     article_id, title, source  (×N)
agent_complete source_aggregator     article_count, sources_found
agent_start    sentiment_analyzer    "Analyzing sentiment..."
agent_update   sentiment_analyzer    article_id, sentiment, score  (×N)
agent_complete sentiment_analyzer    overall_sentiment, shift_signal
agent_start    narrative_extractor   "Extracting narratives..."
agent_update   narrative_extractor   narrative_id, title, type, momentum  (×N)
agent_complete narrative_extractor   narrative_count, dominant_count
agent_start    pattern_mapper        "Mapping narrative patterns..."
agent_complete pattern_mapper        pattern_count, key_actors
agent_start    intelligence_reporter "Generating intelligence brief..."
token                                (streamed LLM tokens)
done                                 full AnalysisResponse
```

## Frontend Tabs

- **Monitor** — Topic/source config with preset quick-starts + live 5-agent progress strip + post-analysis summary metrics
- **Narrative Map** — Sentiment gauge + shift signal + distribution bars + per-source sentiment chart + narrative cards (with momentum bars) + pattern cards + key actors/claims
- **Intelligence Brief** — Key insights bullets + full streamed markdown report + CSV/JSON/MD downloads

## Config

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ARTICLES` | 20 | Total article cap across all sources |
| `MAX_ARTICLES_PER_FEED` | 5 | Max entries per RSS feed |
| `SENTIMENT_BATCH_SIZE` | 4 | Articles per LLM sentiment batch |
| `MAX_NARRATIVES` | 8 | Max narratives to extract |
| `MAX_PATTERNS` | 5 | Max meta-patterns to identify |
| `CONTENT_CHAR_LIMIT` | 600 | Content character limit per article |
