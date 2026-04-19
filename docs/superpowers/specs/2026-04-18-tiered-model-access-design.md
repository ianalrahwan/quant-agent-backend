# Tiered Model Access — Design Spec

**Date:** 2026-04-18
**Branches:** `feature/tiered-model-access` in `quant-agent-backend`, `quant-agent-service`, `quant-infra`
**Companion doc:** [`system_architecture.md`](../../../system_architecture.md) (full system view)

---

## Problem

Anthropic billing credits are draining faster than expected. Audit (see Findings section) confirmed two issues:

1. **The scheduler bleed.** `app/scheduler.py` runs the full orchestrator graph (2 × `claude-sonnet-4-20250514` calls) on the top 10 tickers every 15 minutes — even when no user is on the site. That's ~80 Sonnet 4 calls/hr × 24h = ~1,920 calls/day of idle spend.
2. **No cost ceiling on the public ticker page.** `/ticker/[symbol]` invokes the same expensive orchestrator on every visit, with no auth and no rate limit. A bot, a Hacker News spike, or even casual browsing can run up the bill.

The user originally intended only the scanner on the homepage to be cached; per-ticker LLM analysis was meant to be on-demand and gated.

## Goals

- Idle app spends $0 on Anthropic.
- Anonymous internet visitors get a useful, agentic-feeling experience using a free model with bounded cost.
- The expensive Sonnet 4 path is gated behind a shared password that the user can hand out selectively.
- Frontend visual experience is identical between tiers wherever possible (deterministic charts, signal sidebar, narrative panel) — the only visible gap is trade-rec generation.

## Non-goals (YAGNI)

Per-user accounts, multi-tier billing, audit logs, streaming free-tier output, caching Gemini outputs, multiple passwords, role-based access.

---

## Findings (audit)

Verified file:line evidence for the cost bleed:

- **`app/scheduler.py:16`** — `REFRESH_INTERVAL = 900` (15 min)
- **`app/scheduler.py:84-85`** — `for symbol, signals in tickers[:10]: await _run_for_ticker(...)` runs the full orchestrator per ticker
- **`app/scheduler.py:38`** — `build_orchestrator_graph()` invoked inside `_run_for_ticker`
- **`graphs/trader/nodes/synthesize.py:13`** — `model="claude-sonnet-4-20250514"` (narrative)
- **`graphs/trader/nodes/trade_rec.py:16`** — `model="claude-sonnet-4-20250514"` (trade recs)
- **No auth anywhere:** `app/main.py:64-70` has only CORS; no API key, no middleware, no `AGENT_ACCESS_PASSWORD` env var.

The earnings crawler (`graphs/discovery/nodes/crawl_earnings.py`) does not use Claude — pure FMP API.

---

## Decisions made during brainstorm

| # | Question | Decision |
|---|---|---|
| Q1 | What should the scheduler do? | **A** — Scanner only. No per-ticker LLM pre-warm. |
| Q2 | What "free" model? | **A** — Free-tier hosted model (Gemini Flash). |
| Q3 | Auth shape? | **A** — Single shared password via signed httpOnly cookie. |
| Q4 | Modal: required or optional password? | **A** — Optional. Disclaimer ack required, password optional. |
| Q5 | What does the free graph compute? | **C** — Stripped: skip discovery (no FMP), narrative only via Gemini, no trade recs. |
| Q6 | Rate limit shape? | **C** — Per-IP (5/hr) + global daily cap (300/day) via Redis. |
| Q7 | Routing topology? | **A** — Single endpoint, backend decides tier from header. |
| (cross-domain) | Cookie strategy across Vercel + ECS domains? | **A** — Next.js sets/reads cookie; forwards `X-Pro-Token` to backend. |

---

## Design

### Section 1 — Scheduler bleed fix (`quant-agent-backend`)

Delete `app/scheduler.py` lines 84-87 (the per-ticker pre-warm loop and its cleanup) and the now-dead `_run_for_ticker` function plus its imports. Keep the scanner refresh + `upsert_scanner_result`. Move the periodic `delete_stale_analyses` call into the scanner loop iteration so cache cleanup still runs without dragging an LLM call along.

**Test:** new `tests/test_scheduler.py` asserts one iteration of `analysis_refresh_loop` invokes zero orchestrator graphs.

### Section 2 — Disclaimer modal, password, cross-domain auth

**Frontend (`quant-agent-service`):**
- `src/components/DisclaimerModal.tsx` — first-visit gate, blocks page until acknowledged. Detects via `localStorage["disclaimer-ack-v1"]`. Includes "Built by [Ian Rahwan](https://github.com/ianalrahwan/)" attribution. Optional password field. Modal supports a second mode ("upgrade prompt") that hides the disclaimer paragraph and just shows the password input — opened from `TradeRecUpsell` clicks.
- `src/app/api/auth/login/route.ts` — `POST {password}`. Validates against `AGENT_ACCESS_PASSWORD` env var with `crypto.timingSafeEqual`. On match, sets `agent_pro=<HMAC-SHA256(random, SESSION_COOKIE_SECRET)>` cookie: `httpOnly`, `Secure`, `SameSite=Lax`, 30-day expiry. Returns `{ ok: true }`. Wrong password → 401 after a small delay.
- `src/app/api/auth/logout/route.ts` — clears cookie.
- `src/app/api/agent/analyze/[symbol]/route.ts` — reads cookie, validates HMAC, adds `X-Pro-Token: <PRO_TIER_TOKEN>` header when forwarding to backend.

**Backend (`quant-agent-backend`):**
- `app/dependencies.py` — new `get_tier(request)` returns `"pro"` when header matches `settings.PRO_TIER_TOKEN` via `secrets.compare_digest`, else `"free"`. Never raises.
- `app/config.py` — adds `PRO_TIER_TOKEN: str`.

### Section 3 — Backend tier routing & free graph

**`app/routes/analysis.py`** — single endpoint, single branch:
```python
if tier == "free":
    await rate_limiter.check(get_client_ip(request))
    graph = build_free_graph()
else:
    graph = build_orchestrator_graph()
```
Same job-id, SSE bus, and `upsert_cached_analysis` flow for both tiers. Response envelope adds `tier: "free" | "pro"`.

**`graphs/free/`** (new):
- `state.py` — minimal Pydantic state: `symbol`, `scanner_signals`, `vol_analysis`, `narrative`, `logs`. No discovery context.
- `graph.py` — START → `load_signals_node` → `compute_vol_node` → `narrate_gemini_node` → END. Three nodes; only the last is an LLM call.
- `nodes/narrate_gemini.py` — single `gemini-2.0-flash` call via `google-genai`, `max_output_tokens=256`. Prompt is the trader synthesize prompt minus earnings/news/podcast context. On any Gemini error, returns a graceful fallback narrative — never 500s.

**Shared vol computation:** the deterministic vol-surface node currently inside the trader graph is extracted to `graphs/shared/compute_vol.py` so both `free.graph` and `orchestrator.graph` can reuse it. This is the only refactor outside the immediate scope of the feature, justified because the free graph genuinely needs the same numbers and duplicating the code would invite drift.

### Section 4 — Rate limiting (free tier only)

**`app/scanner/rate_limiter.py`** (new) — `RateLimiter.check(ip)`:
- Per-IP: `INCR rl:ip:{ip}` with 1hr `EXPIRE`. Limit = 5 (`RATE_LIMIT_PER_IP`).
- Global daily: `INCR rl:global:{YYYYMMDD}` with 86460s `EXPIRE`. Limit = 300 (`RATE_LIMIT_GLOBAL_DAILY`).
- Either limit exceeded → `HTTPException(429, message)` with tier-specific user-facing copy.

**IP source:** new helper `get_client_ip(request)` reads `X-Forwarded-For[0]` (trusted because upstream ALB/Vercel is controlled) and falls back to `request.client.host`.

Frontend handles 429 in `useAgentAnalysis` as `error.kind = "rate_limit"`, rendered as a friendly amber banner inside `AgentPanel`.

### Section 5 — Frontend display integration

**`src/lib/agent-types.ts`** — adds `Tier = "free" | "pro"`, propagated through `AgentAnalysisState` and `CachedAnalysis`.

**`src/hooks/useAgentAnalysis.ts`** — propagates `tier` from response into state; routes 429s into a structured error.

**`src/components/detail/AgentPanel.tsx`** — single conditional in the trade-rec section:
```tsx
state.tier === "pro"
  ? <TradeRecCards .../>
  : <TradeRecUpsell />
```

**`src/components/detail/TradeRecUpsell.tsx`** (new, ~20 lines) — Bloomberg-styled lock tile with a button that re-opens `DisclaimerModal` in upgrade-prompt mode (skips the disclaimer paragraph, focuses the password input).

All deterministic chart panels (signal sidebar, term structure, skew, kurtosis, vol surface, macro overlay) and all phase-pipeline / log / mascot UI inside `AgentPanel` are unchanged and identical between tiers.

### Section 6 — Infra (`quant-infra`)

**`terraform/data/main.tf`** — append four new `aws_secretsmanager_secret` + `_version` pairs (placeholder `"REPLACE_ME"` like existing pattern):
- `gemini_api_key`
- `agent_access_password`
- `session_cookie_secret`
- `pro_tier_token`

**`terraform/data/outputs.tf`** — export 4 new ARNs.

**`terraform/compute/main.tf`** —
- Pull new ARNs into `locals` near lines 47-51.
- Add `gemini_arn` and `pro_tier_token_arn` to `ecs_execution_secrets` policy `Resource` list (around line 144).
- Add `GEMINI_API_KEY` and `PRO_TIER_TOKEN` entries to ECS task `secrets` block (around line 201).

**`terraform/vercel/main.tf`** — three new `vercel_project_environment_variable` resources. Source values from AWS Secrets Manager via `data "aws_secretsmanager_secret_version"` blocks so secrets live in one place: `AGENT_ACCESS_PASSWORD`, `SESSION_COOKIE_SECRET`, `PRO_TIER_TOKEN`.

### Section 7 — Backend dependencies

`pyproject.toml` adds `google-genai`. Verify `redis>=5` is already present (the rate limiter uses it); if not, add it.

---

## Testing strategy

**Unit:**
- `tests/test_scheduler.py` — one iteration runs zero LLM-bearing graphs.
- `tests/graphs/free/test_narrate_gemini.py` — prompt structure + error fallback path.
- `tests/test_rate_limiter.py` — per-IP exceeds → 429; global exceeds → 429; pro tier bypasses entirely.
- `tests/test_get_tier.py` — header missing → free; valid → pro; tampered → free; no exceptions.

**Integration:**
- `tests/routes/test_analyze_tier.py` — POST without header runs free graph (mocked Gemini); POST with valid token runs orchestrator (mocked Anthropic). Asserts via `build_*_graph` spies.
- Frontend (Vitest or Playwright) — wrong password → 401; right password → cookie set with correct flags.

**Manual smoke (per CLAUDE.md):**
- Fresh ticker as unauthed user → narrative renders, upsell shows, no Anthropic line in logs.
- Same ticker after entering password → trade rec cards render, Sonnet 4 call appears in logs.
- One scheduler cycle → only `run_scan` + scanner upsert lines; zero `synthesize.calling_claude` or `trade_rec.calling_claude`.

---

## Cost model

| Scenario | Before | After |
|---|---|---|
| Idle (no users) | ~80 Sonnet 4 calls/hr (scheduler bleed) | $0 |
| Anonymous visitor on `/ticker/X` | 2 Sonnet 4 calls per visit, unbounded | 1 Gemini Flash call (free tier) capped at 5/hr/IP and 300/day global |
| Authenticated visitor | 2 Sonnet 4 calls per visit (cached 1hr) | Same — but only when password is held |

Worst-case bot abuse on free tier: bounded at 300 Gemini Flash calls/day. Within Google's free tier (1,500 RPD); even paid overflow is pennies.

---

## Threat model

- **Brute-force the password:** rate-limited at the `/api/auth/login` route (Vercel-level rate limits or a small in-route counter — implement during plan phase).
- **Tamper with the cookie:** HMAC validation rejects any modification.
- **Bypass the rate limiter via IP rotation:** global daily cap catches it.
- **Spoof `X-Forwarded-For`:** acceptable risk because only trusted upstream (Vercel/ALB) prepends this header in production; document this and only trust it when behind the load balancer.
- **Read frontend env vars:** an attacker who has these already owns the deployment.
- **Backend never receives the user's password** — only the shared token from trusted Next.js code.

---

## Files to create or modify (summary)

**`quant-agent-backend`:**
- NEW: `graphs/free/{graph,state}.py`, `graphs/free/nodes/narrate_gemini.py`, `graphs/free/nodes/load_signals.py`
- NEW: `graphs/shared/compute_vol.py` (extracted from trader graph)
- MODIFY: `graphs/trader/graph.py` (use shared compute_vol)
- NEW: `app/scanner/rate_limiter.py`
- NEW: `tests/test_scheduler.py`, `tests/test_rate_limiter.py`, `tests/test_get_tier.py`, `tests/graphs/free/test_narrate_gemini.py`, `tests/routes/test_analyze_tier.py`
- MODIFY: `app/scheduler.py` (delete bleed loop)
- MODIFY: `app/dependencies.py` (add `get_tier`, `get_rate_limiter`)
- MODIFY: `app/config.py` (add new env settings)
- MODIFY: `app/routes/analysis.py` (tier-aware graph selection)
- MODIFY: `pyproject.toml` (add `google-genai`)

**`quant-agent-service`:**
- NEW: `src/components/DisclaimerModal.tsx`, `src/components/detail/TradeRecUpsell.tsx`
- NEW: `src/app/api/auth/login/route.ts`, `src/app/api/auth/logout/route.ts`
- MODIFY: `src/app/api/agent/analyze/[symbol]/route.ts`
- MODIFY: `src/components/detail/AgentPanel.tsx`
- MODIFY: `src/hooks/useAgentAnalysis.ts`
- MODIFY: `src/lib/agent-types.ts`
- MODIFY: `src/app/layout.tsx` (mount `<DisclaimerModal />`)

**`quant-infra`:**
- MODIFY: `terraform/data/main.tf`, `terraform/data/outputs.tf`
- MODIFY: `terraform/compute/main.tf`
- MODIFY: `terraform/vercel/main.tf`
