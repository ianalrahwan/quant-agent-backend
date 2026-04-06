# Quant Agent Backend

Quantitative volatility analysis engine built on FastAPI and LangGraph. Orchestrates three sub-graphs to produce institutional-grade vol analysis with trade recommendations.

## LangGraph Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │             ORCHESTRATOR GRAPH              │
                         │                                             │
                         │   ┌─────────────────┐                       │
                         │   │ check_freshness  │                       │
                         │   └────────┬────────┘                       │
                         │            │                                │
                         │    discovery_needed?                        │
                         │      │            │                         │
                         │     yes           no                        │
                         │      │            │                         │
                         │      ▼            │                         │
                         │ ┌──────────────┐  │                         │
                         │ │run_discovery ─┼──┼─── DISCOVERY GRAPH     │
                         │ └──────┬───────┘  │                         │
                         │        │          │                         │
                         │        ▼          ▼                         │
                         │   ┌──────────────────┐                      │
                         │   │   run_trader    ──┼──── TRADER GRAPH    │
                         │   └────────┬─────────┘                      │
                         │            │                                │
                         │           END                               │
                         └─────────────────────────────────────────────┘


  ┌────────────────────────────────┐     ┌─────────────────────────────────────┐
  │        DISCOVERY GRAPH         │     │           TRADER GRAPH              │
  │                                │     │                                     │
  │   ┌──────────┐ ┌──────────┐   │     │   ┌────────────────┐                │
  │   │  crawl   │ │  crawl   │   │     │   │ signal_confirm │                │
  │   │ earnings │ │   news   │   │     │   └───────┬────────┘                │
  │   └────┬─────┘ └────┬─────┘   │     │           │                         │
  │        │             │         │     │      is_valid?                      │
  │   ┌────┴─────┐ ┌────┴─────┐   │     │      │       │                      │
  │   │  crawl   │ │  crawl   │   │     │     yes      no → END               │
  │   │ podcasts │ │   cftc   │   │     │      │                              │
  │   └────┬─────┘ └────┬─────┘   │     │      ▼                              │
  │        │             │         │     │   ┌─────────────┐                   │
  │        └──────┬──────┘         │     │   │ vol_surface  │                  │
  │               │  fan-in        │     │   └──────┬──────┘                   │
  │               ▼                │     │          │                          │
  │        ┌─────────────┐         │     │          ▼                          │
  │        │ chunk_embed  │        │     │   ┌─────────────────┐               │
  │        └──────┬──────┘         │     │   │ narrative_query  │  ⏸ checkpoint│
  │               │                │     │   └───────┬─────────┘               │
  │               ▼                │     │           │                         │
  │        ┌─────────────┐         │     │           ▼                         │
  │        │    index     │        │     │   ┌──────────────┐                  │
  │        └──────┬──────┘         │     │   │  synthesize   │  ⏸ checkpoint  │
  │               │                │     │   └──────┬───────┘                  │
  │              END               │     │          │                          │
  └────────────────────────────────┘     │          ▼                          │
                                         │   ┌──────────────┐                  │
                                         │   │  trade_rec    │  ⏸ checkpoint  │
                                         │   └──────┬───────┘                  │
                                         │          │                          │
                                         │         END                         │
                                         └─────────────────────────────────────┘
```

### Orchestrator

Entry point for all analysis. Checks data freshness, conditionally runs discovery to crawl new data, then hands off to the trader graph for vol analysis and trade recommendations.

### Discovery

Fan-out/fan-in pattern. Four crawlers run in parallel — earnings transcripts (FMP), news (NewsAPI), podcasts (RSS), and CFTC positioning data. Results merge into `chunk_embed` for Voyage AI embedding, then `index` stores vectors in pgvector.

### Trader

Sequential analysis pipeline with human-in-the-loop checkpoints. Validates scanner signals, analyzes the vol surface, queries narrative context from pgvector, synthesizes a narrative via Claude, and generates trade recommendations. Each checkpoint allows the operator to review before proceeding.

## Stack

- **FastAPI** — async API with SSE event streaming
- **LangGraph** — node-based graph orchestration with state management
- **PostgreSQL + pgvector** — document storage and semantic search
- **Claude API** — narrative synthesis and trade recommendation generation
- **Voyage AI** — document embedding (1024-dim)

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/{symbol}` | POST | Start full analysis pipeline |
| `/stream/{jobId}` | GET | SSE event stream for analysis progress |
| `/cached/{symbol}` | GET | Pre-computed analysis results |
| `/scanner` | GET | Pre-computed scanner scores (all tickers) |
| `/health` | GET | Health check |
