# Quant Firm — Corporate Changelog

## v1: Full Team (2026-03-09, Cycle 1)

**Structure:** 4 persistent sub-agents
- qf-researcher: Market scanning, data analysis, opportunity identification
- qf-risk-mgr: Risk assessment, trade approval/veto, drawdown monitoring
- qf-executor: Trade execution on Kalshi API
- qf-bookkeeper: CSV logging, P&L tracking, baseline comparison

**Coordination:** Terminal `send` (stdin injection)

**Problems:** Terminal send unreliable — agents missed ~80% of injected tasks. See lessons-learned.md Lesson 6.

---

## v2: Event-Based Coordination (2026-03-09, ~Cycle 10)

**Structure:** Same 4 agents

**Change:** Switched from terminal `send` to OMAR event system for all inter-agent communication.

**Result:** Reliability went from ~20% to ~100%. Clear request/response pattern. Events queued and delivered when agent is ready.

**Protocol:**
1. Firm head gathers data
2. Dispatches researcher + risk-mgr via events (parallel)
3. Self-wake in 2 min
4. Collects responses, makes decision
5. Dispatches executor if trades approved
6. Dispatches bookkeeper to log
7. Cycle complete

---

## v3: Lean Team (2026-03-11, Cycle 65)

**Structure:** 2 persistent sub-agents (down from 4)
- qf-researcher: KEPT — core edge, market scanning + data analysis
- qf-risk-mgr: KEPT — risk discipline, drawdown enforcement
- qf-executor: KILLED — idle 95% of cycles. Respawn on-demand when trades approved.
- qf-bookkeeper: KILLED — trivial CSV append. Firm head does it directly.

**Rationale:**
- 90%+ of cycles were "HOLD all, no new markets"
- Full 4-agent delegation took ~3 min per cycle for no alpha
- Executor never used after initial trade setup
- Bookkeeper work is 3 lines of bash

**New protocol:**
```
FAST PATH (quiet market, no catalysts):
1. Firm head: quick balance + orderbook check (~15s)
2. Nothing changed → log CSV directly, done (~30s total)

FULL PATH (catalyst day: data release, new markets):
1. Firm head gathers data, detects catalyst
2. Dispatch researcher + risk-mgr via events
3. Combine results, decide
4. If trades: spawn executor on-demand, execute, kill after
5. Log CSVs directly
6. Done
```

**Catalyst triggers for FULL PATH:**
- GDPNow update days (typically Mon/Wed/Fri)
- Economic data releases (CPI, PPI, jobs, retail sales)
- FOMC meeting days
- New macro markets appearing on Kalshi
- Significant orderbook moves (>10c) on our positions

**Scaling plan:** One researcher sufficient for 2 positions + limited Kalshi macro universe. Split into sector specialists if scaling to 10+ positions or multiple asset classes.

**Expected improvement:** Quiet cycles 30s (was 3min). Agent resource usage -50%.

**File location change:** All firm documents (CSVs, lessons-learned, changelog) now written to `/home/shaokai/Documents/projects/money-making-quant/` using absolute paths. Previously wrote to `omar/money-making-quant/` (repo-relative). Agent prompts and `kalshi_auth.py` still referenced from omar repo.

---

## v4: Solo Operator + On-Demand Task Forces (2026-03-14)

**Structure:** Zero persistent sub-agents. Firm head operates solo by default.

**Rationale:**
- Ran 75+ cycles. ~95% were "HOLD all, no changes."
- Even v3's lean 2-agent structure added 2-3 min latency dispatching researcher + risk-mgr for the same "nothing to do" answer.
- Firm head can scan the entire Kalshi macro universe (GDP, CPI, Fed, GOVTCUTS, oil — ~30 tickers), check GDPNow, pull orderbooks, and do risk math in under 2 minutes solo.
- Research depth matters more than org breadth. When a catalyst hits, we need *deep analysis*, not standing committees.

**Protocol:**
```
SOLO PATH (95% of cycles — quiet market, no catalysts):
1. Firm head: balance + positions + orderbook check
2. Quick web search for macro data if needed (GDPNow, FOMC, CPI)
3. Risk check against risk-limits.json
4. Log portfolio-history.csv
5. Done. ~2 min total.

TASK FORCE PATH (catalyst day — data release, FOMC, big move):
1. Firm head detects catalyst, gathers initial data
2. Spawn 2-3 purpose-built agents IN PARALLEL:
   - qf-researcher (claude or opencode/o3): deep analysis of the specific catalyst
   - qf-risk-mgr (claude): stress test proposed trades against limits
   - qf-executor (claude): execute approved trades via API
3. Collect results, make trading decision
4. Kill all agents after use
5. Log everything
```

**Multi-backend capability (new in OMAR v0.1.1):**
- Available: `claude` (Anthropic), `opencode` (multi-provider — OpenAI o3, etc.)
- Not yet installed: `codex` (OpenAI native), `cursor`
- Use case: spawn a second researcher on `opencode` with `openai/o3` for an independent macro view when conviction is borderline. Two models, two perspectives, better decisions.

**Catalyst triggers (same as v3):**
- GDPNow update days
- Economic data releases (CPI, PPI, jobs, retail sales)
- FOMC meeting days (next: March 18)
- New macro markets on Kalshi
- Orderbook moves >10c on our positions

**vs. v3:** Eliminated 2 persistent agents. Quiet cycles drop from ~3 min to ~2 min. Zero idle resource usage between cycles. Full analysis capacity preserved for when it matters — just deployed on-demand instead of standing by.
