# Quant Agent — System Architecture

Three repositories collaborate to deliver the Bloomberg-terminal-style volatility analysis app.

| Repo | Role | Stack |
|---|---|---|
| `quant-agent-service` | Frontend | Next.js (App Router), React, SWR, Tailwind |
| `quant-agent-backend` | API + LangGraph agents (this repo) | FastAPI, LangGraph, Anthropic SDK, google-genai SDK, Postgres, Redis |
| `quant-infra` | Cloud infra | Terraform — AWS (ECS, RDS, ElastiCache, Secrets Manager) + Vercel |

---

## High-level data flow

```
                     ┌──────────────────────────────────────────┐
                     │      Visitor's browser (anonymous)        │
                     └───────────────────┬──────────────────────┘
                                         │
                       Disclaimer modal (first visit only)
                       ├─ "Acknowledge" → localStorage flag
                       └─ Optional password → POST /api/auth/login
                                         │
                                         ▼
            ┌─────────────────────────────────────────────────────────┐
            │        Next.js (Vercel) — quant-agent-service           │
            │                                                         │
            │  /                  → SWR(/api/scanner)  [cache-driven] │
            │  /ticker/[symbol]   → SWR(/api/quote, /options, ...)    │
            │                       useAgentAnalysis()                │
            │                          │                              │
            │  /api/auth/login    sets `agent_pro` HMAC cookie        │
            │  /api/agent/analyze/[sym]                               │
            │     ├─ if cookie valid → adds X-Pro-Token header        │
            │     └─ proxies to backend                               │
            └────────────────────────────┬────────────────────────────┘
                                         │   X-Pro-Token? (yes/no)
                                         ▼
            ┌─────────────────────────────────────────────────────────┐
            │     FastAPI (AWS ECS) — quant-agent-backend             │
            │                                                         │
            │  POST /analyze/{symbol}                                 │
            │     │                                                   │
            │     ├─ Depends(get_tier) ── header valid? ──┐           │
            │     │                                       │           │
            │     │   "free"                              │  "pro"    │
            │     ▼                                       ▼           │
            │  ┌──────────────────┐        ┌──────────────────────┐   │
            │  │ RateLimiter      │        │ orchestrator.graph   │   │
            │  │ (per-IP + global)│        │  ├ check_freshness   │   │
            │  │  Redis           │        │  ├ run_discovery     │   │
            │  │                  │        │  │   (FMP earnings/  │   │
            │  │  raises 429      │        │  │    news/podcasts) │   │
            │  └────────┬─────────┘        │  └ run_trader        │   │
            │           ▼                  │     ├ synthesize     │   │
            │  ┌──────────────────┐        │     │  Sonnet 4 ($)  │   │
            │  │ free.graph       │        │     └ trade_rec      │   │
            │  │  ├ load_signals  │        │        Sonnet 4 ($)  │   │
            │  │  └ narrate_      │        └──────────┬───────────┘   │
            │  │    gemini        │                   │               │
            │  │     Gemini Flash │                   │               │
            │  └────────┬─────────┘                   │               │
            │           │                             │               │
            │           ▼                             ▼               │
            │     upsert_cached_analysis (Postgres, 1hr TTL)          │
            │                                                         │
            │  Scheduler loop (every 15 min):                         │
            │     run_scan() → upsert_scanner_results                 │
            │     (NO LLM calls; scanner cache only)                  │
            └─────────────────────────────────────────────────────────┘
                                         │
                                         ▼
            ┌─────────────────────────────────────────────────────────┐
            │      AWS infra (managed by quant-infra terraform)       │
            │  RDS Postgres │ ElastiCache Redis │ Secrets Manager     │
            └─────────────────────────────────────────────────────────┘
```

---

## Tier model

The app serves two tiers from a single `/analyze/{symbol}` endpoint. Tier is determined server-side from the `X-Pro-Token` header (set by the Next.js proxy when a valid `agent_pro` cookie is present).

| Concern | Free tier | Pro tier |
|---|---|---|
| Trigger | Disclaimer acknowledged, no password | Disclaimer acknowledged + correct password |
| Auth surface | None (cookie absent) | Signed httpOnly cookie, 30-day expiry |
| Backend graph | `graphs/free` (3 nodes, 1 LLM call) | `graphs/orchestrator` (discovery + trader, 2 LLM calls) |
| LLM | `gemini-2.0-flash` (Google AI Studio free tier) | `claude-sonnet-4-20250514` (Anthropic) |
| External data fetched | Options chain only (for deterministic vol surface compute) | Options chain + FMP earnings/news + podcast transcripts + positioning |
| Output: narrative | ✅ | ✅ (richer, more context-aware) |
| Output: trade recommendations | ❌ Replaced by upgrade tile | ✅ |
| Rate limit | 5/hr per IP, 300/day global (Redis) | None |
| DB cache | Same `cached_analyses` table, 1hr TTL | Same |
| Response shape | Same envelope; `tier: "free"`, `trade_recs: []` | Same envelope; `tier: "pro"`, `trade_recs: [...]` |

### Frontend display difference

The `/ticker/[symbol]` page renders 7 panels. Only the LLM-driven content inside the `AgentPanel` differs between tiers:

| Panel | Source | Free | Pro |
|---|---|---|---|
| Signal Analysis (sidebar) | scanner DB | ✅ same | ✅ same |
| Term Structure | options chain | ✅ same | ✅ same |
| IV Skew | options chain | ✅ same | ✅ same |
| Return Distribution / Kurtosis | historical bars | ✅ same | ✅ same |
| Vol Surface | options chain | ✅ same | ✅ same |
| Macro Overlay & IV Percentile | macro + history | ✅ same | ✅ same |
| Agent Analysis: phase pipeline + logs + bear mascot | UI state | ✅ shown | ✅ shown |
| Agent Analysis: NARRATIVE | LLM | ✅ Gemini Flash | ✅ Sonnet 4 |
| Agent Analysis: TRADE RECOMMENDATIONS | LLM JSON | ❌ Upsell tile | ✅ Cards |

---

## Component map

### `quant-agent-backend` (this repo)

```
app/
  main.py            FastAPI app, lifespan starts scheduler
  config.py          Settings (env vars, including new GEMINI_API_KEY, PRO_TIER_TOKEN, rate-limit knobs)
  dependencies.py    DI: get_session_factory, get_tier, get_rate_limiter
  scheduler.py       15-min loop: scanner only, no LLM (post-cleanup)
  scanner/
    engine.py        run_scan() — pulls market data, computes signals
    rate_limiter.py  Redis-backed per-IP + global daily cap (NEW)
  routes/
    analysis.py      POST /analyze/{symbol} — tier-aware routing
    cached.py        GET /agent/cached/{symbol}
    health.py        GET /health

graphs/
  orchestrator/      Pro tier graph (discovery + trader)
  discovery/         Earnings/news/podcast/positioning crawlers
  trader/
    nodes/synthesize.py    Sonnet 4 narrative
    nodes/trade_rec.py     Sonnet 4 trade structures (JSON)
  free/              Free tier graph (NEW)
    graph.py           load_signals → compute_vol (shared) → narrate_gemini
    state.py
    nodes/narrate_gemini.py    Gemini Flash narrative
  shared/            Deterministic vol-surface computation (extracted
                     from current trader graph so both tiers can reuse)

data/
  scanner_repo.py    upsert_scanner_result, delete_stale_scanner_results
  cache_repo.py      upsert_cached_analysis, delete_stale_analyses
```

### `quant-agent-service` (frontend)

```
src/
  components/
    DisclaimerModal.tsx            (NEW) First-visit + upgrade-prompt modes
    detail/
      AgentPanel.tsx               (MODIFIED) Conditional render on `tier`
      TradeRecCards.tsx            (existing) Pro tier
      TradeRecUpsell.tsx           (NEW) Free tier replacement tile
      ...all chart components      (unchanged)
  hooks/
    useAgentAnalysis.ts            (MODIFIED) Propagates `tier`, handles 429
  app/
    api/
      auth/login/route.ts          (NEW) Validates password, sets cookie
      auth/logout/route.ts         (NEW) Clears cookie
      agent/analyze/[symbol]/route.ts  (MODIFIED) Forwards X-Pro-Token
    ticker/[symbol]/page.tsx       (unchanged)
    page.tsx                       (unchanged — scanner page)
  lib/
    agent-types.ts                 (MODIFIED) Adds Tier type
```

### `quant-infra` (terraform)

```
terraform/
  data/main.tf       (MODIFIED) Add 4 new aws_secretsmanager_secret resources:
                       gemini_api_key, agent_access_password,
                       session_cookie_secret, pro_tier_token
  data/outputs.tf    (MODIFIED) Export 4 new ARNs
  compute/main.tf    (MODIFIED)
                       - Add ARNs to ecs_execution_secrets policy
                       - Add GEMINI_API_KEY + PRO_TIER_TOKEN to ECS task secrets
  vercel/main.tf     (MODIFIED) Sync 3 env vars to Vercel project from
                       Secrets Manager:
                       AGENT_ACCESS_PASSWORD, SESSION_COOKIE_SECRET,
                       PRO_TIER_TOKEN
```

---

## Env vars (production)

| Var | Frontend (Vercel) | Backend (ECS) | Source of truth |
|---|---|---|---|
| `AGENT_ACCESS_PASSWORD` | ✅ | ❌ | AWS Secrets Manager |
| `SESSION_COOKIE_SECRET` | ✅ | ❌ | AWS Secrets Manager |
| `PRO_TIER_TOKEN` | ✅ | ✅ | AWS Secrets Manager (single value, mirrored) |
| `GEMINI_API_KEY` | ❌ | ✅ | AWS Secrets Manager |
| `ANTHROPIC_API_KEY` | ❌ | ✅ | AWS Secrets Manager (existing) |

---

## Cost model

**Idle app (no users):** $0 Anthropic, $0 Google. The scheduler only computes scanner signals.

**Free user activity:** Bounded by rate limits at 300 calls/day globally → fits within Gemini Flash's free tier (1,500 RPD). Worst-case overflow into paid Flash is pennies/day.

**Pro user activity:** Each ticker analysis = 2 Sonnet 4 calls (synthesize + trade_rec). Cost scales linearly with authenticated user clicks. Cached for 1 hour per ticker, so refreshes within the window are free.

**Pre-tier-system baseline (the bleed):** Scheduler ran the full orchestrator on 10 tickers every 15 min = ~80 Sonnet 4 calls/hr regardless of user activity = ~1,920 calls/day idle. Removed in `app/scheduler.py` lines 84-87.

---

## Security boundaries

- Backend never sees the user's password. Only the Next.js layer compares it; on success, Next.js sets a signed cookie and adds a shared `X-Pro-Token` header to backend calls.
- Cookie is `httpOnly`, `Secure`, `SameSite=Lax`, signed with HMAC-SHA256.
- Rate limiter trusts `X-Forwarded-For[0]` because the upstream (ALB or Vercel) is controlled. Direct `request.client.host` would always be the load balancer.
- Password validation uses `crypto.timingSafeEqual`; token validation uses `secrets.compare_digest`.
- No PII stored. No accounts. localStorage holds only the disclaimer-ack boolean.

---

## Out of scope (intentional YAGNI)

- Per-user accounts, audit logs, billing
- Multiple passwords / role tiers
- Streaming Gemini responses (free narratives are short, buffered)
- Caching Gemini outputs (rate limiter already bounds cost)
