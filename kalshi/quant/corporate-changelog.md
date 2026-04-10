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

---

## v5: Parallel Research Desks (2026-03-18)

**Structure:** 3 ephemeral sector-specialist researchers, spawned in parallel on full cycles. Firm head retains all decision-making and execution.

**Agents (spawned per full cycle, killed after):**
- **oil-desk** (claude): WTIMAX contracts, crude/Brent prices, Hormuz/Iran news, energy supply data
- **cpi-desk** (claude): Full CPI curve (all strikes, all months), Cleveland Fed nowcast, gas prices, food prices
- **macro-desk** (codex/o3): GDP, Fed rate path, recession, government spending, unemployment — plus anything the other desks might miss

**Why the change — lessons from baseline comparison (2026-03-18):**

The baseline agent running solo found 12 positions across oil, CPI, and GDP. We ran solo and found 3. Same $200 start, same markets, same information. They're at $242 (+21%), we're at $117 (-41%).

Root cause: **v4's solo operator created tunnel vision.** We found the CPI nowcast thesis on cycle 1, fixated on it for 36+ hours and 20+ cycles, and never explored oil contracts, CPI lottery tickets (T1.0/T1.2/T1.3 at 1c), or CPI April markets. A single brain doing sequential research will lock onto the first thesis it finds and stop looking.

**Key insight:** The advantage of sub-agents isn't managing complexity — it's **parallel idea generation**. Three researchers scanning different sectors simultaneously find 10+ trade ideas in the time one operator spends refining a single thesis. Attention is the bottleneck, not capital.

**False assumption corrected:** v4 assumed "sub-agents only help at 15+ positions / $5K+ accounts." Wrong. The baseline has 12 positions on $138 deployed. Many are tiny: 50 contracts at 1c ($0.50 risk) as lottery tickets. You don't need a large account for many positions. You need ideas across multiple themes.

**Protocol:**
```
FULL CYCLE (catalysts, market open, periodic scans):
1. Firm head gathers portfolio state (30 sec)
2. Spawn 3 researcher agents IN PARALLEL via OMAR API:
   - oil-desk (claude): "Scan WTIMAX/crude markets. Current oil $X.
     Report: top 3 opportunities with ticker, price, thesis, sizing."
   - cpi-desk (claude): "Scan full CPI curve (Mar/Apr/May, all strikes).
     Nowcast=X%. Report: top 3 opportunities + lottery tickets <5c."
   - macro-desk (codex/o3): "Scan GDP, Fed rates, recession, govtcuts,
     unemployment. Report: top 3 opportunities we're not already in."
3. Schedule self-wake in 2 min
4. Collect results via events
5. Firm head synthesizes — look for CONVERGENCE across desks
6. Execute trades directly (no executor agent needed)
7. Log CSVs directly (no bookkeeper needed)
8. Kill all agents
9. Push to omar-data repo

QUIET CYCLE (overnight, no catalysts, all stable):
1. Firm head solo: balance + prices check (~30 sec)
2. If all positions ±2c: log and done
3. No agents needed
```

**Multi-backend deployment:**
- oil-desk + cpi-desk: `claude` backend (fast, good at data analysis)
- macro-desk: `codex` backend with o3 model (independent perspective, catches blind spots)
- Use model disagreement as a signal: if claude and o3 disagree on a trade, size down or skip

**What stays from v4:**
- Firm head makes ALL trading decisions (no delegation of execution)
- Firm head does bookkeeping (trivial CSV appends)
- Agents are ephemeral — spawn, collect, kill
- Quiet cycles stay solo

**What's new vs v4:**
- Sector-specialist researchers instead of generalist solo scanning
- Parallel spawning on EVERY full cycle, not just catalyst days
- codex/o3 as independent second opinion (Lesson 7 finally implemented)
- Explicit goal: 10+ trade ideas per full cycle, not 1-2

**Expected improvement:** Market surface area coverage 3x. Trade idea generation 5-10x. Eliminates tunnel vision that caused us to miss oil trades and CPI lottery tickets worth +400%. Adds model diversity for conviction cross-checks.

---

## v6: Research-Driven Firm (2026-03-31)

**Structure:** 4 parallel research desks + risk manager + executor (all ephemeral per cycle). Firm head coordinates.

**Agents (spawned per full cycle, killed after):**
- **oil-desk (qf-oil)**: WTI spot, Hormuz crisis, Iran war, oil supply/demand, energy markets
- **cpi-desk (qf-cpi)**: Cleveland Fed nowcast, gas prices, PPI pipeline, all CPI curve strikes
- **macro-desk (qf-macro)**: GDP, Fed policy, recession, DOGE/govt cuts, labor markets
- **opportunity-desk (qf-opps)**: Scan ALL Kalshi markets + web for NEW theses we're not tracking. Scout for emerging themes (housing, tariffs, weather, tech, geopolitical).
- **risk-mgr (qf-risk)**: Evaluate proposed trades against risk-limits.json
- **executor (qf-exec)**: Place approved orders

**Why the change — lessons from v5:**

v5 defined parallel research desks but the firm head reverted to solo operation within days. 95%+ of cycles from Mar 18 to Mar 31 were solo "fetch prices → log → HOLD" with zero research. The org chart existed on paper but wasn't followed.

Root causes:
1. Drawdown limit (20%) was too tight — blocked all new trades, making research pointless
2. No mechanism to force research cycles — firm head optimized for speed over alpha
3. 5-position limit killed motivation to find new ideas

**Key changes vs v5:**
- **Position limit raised 5 → 15**: Information edge = more diversified bets
- **Drawdown limit raised 20% → 35%**: Room to trade
- **Exposure limit raised 60% → 75%**: Deploy more capital
- **Opportunity desk added**: Dedicated agent for NEW thesis discovery, not just monitoring existing positions
- **firm-plan.md says READ EVERY CYCLE**: Prevents silent reversion to solo mode
- **Full cycles required 2x/day minimum during market hours**

**Expected improvement:** Active thesis generation instead of passive monitoring. New positions in sectors we haven't explored. Diversified portfolio instead of concentrated in 5 war-correlated bets.

---

## v7: Horizontal Scale (2026-04-01)

**Structure:** 3 core desks + 10 opportunity scouts = 13 parallel researchers per full cycle.

**Core Desks (same as v6):**
- oil-desk, cpi-desk, macro-desk

**Opportunity Scouts (NEW — 10 narrow-scope agents):**
- qf-opps-fed — Fed rate markets
- qf-opps-labor — Jobs, unemployment
- qf-opps-housing — Housing, shelter
- qf-opps-politics — Elections, policy, tariffs
- qf-opps-sp500 — S&P 500, indices
- qf-opps-weather — Weather markets
- qf-opps-crypto — Bitcoin, crypto
- qf-opps-sports — Sports with data edge
- qf-opps-global — Geopolitical, trade
- qf-opps-calendar — This week's econ releases

**Why the change:**

v6's single qf-opps agent failed twice — timed out scanning 9,280 Kalshi series. The scope was right but the execution model was wrong. One agent can't search everything in 3 minutes.

Solution: horizontal scale. 10 scouts with narrow scope each finish fast and return focused findings. 10 agents × 2 ideas = 20 new thesis candidates vs 0 from v6's single agent.

**Key insight:** Agent count is cheap. Information surface area is the bottleneck. More narrow-scope agents > fewer broad-scope agents.

---

## v8: Hybrid — Bots + Agents (2026-04-02)

**Structure:** Automated bots for known-edge strategies + agent desks for judgment calls.

**Bots (persistent code, run independently):**
- `bots/weather_bot.py` — NWS 7-day forecast API → normal distribution model → Kalshi weather brackets. Runs 1-2x/day.
- `bots/econ_bot.py` — Cleveland Fed Nowcast / GDPNow → CPI/GDP brackets (planned).

**Agent Desks (2 Claude agents, spawned per cycle):**
- qf-oil — WTI yearly max, Hormuz, Iran, supply/demand
- qf-macro — GDP, recession, Fed policy, tariffs, govt cuts

**Quant Scouts (2-3 Claude agents, 1-2x/day):**
- Market Scanner — find new Kalshi series with free data sources
- Strategy Developer — backtest/improve bot parameters
- Performance Analyst — audit win rates by sector, recommend sizing

**Why the change:**

v7's 10 Codex scouts consistently failed — they couldn't use web search, timed out, or produced zero actionable output. Meanwhile, weather markets had a clear statistical edge from NWS data that didn't need agent judgment at all.

Key realization: **separate known edges from judgment calls**.
- Weather has a repeatable statistical edge (NWS forecast vs market price). A Python script trades it better than an agent — no emotional sizing, consistent execution, no timeouts.
- Oil/macro positions need synthesis of geopolitical events, economic data, and market sentiment. Agents handle this well.

**Bot limits (strict, auto-approved):**
- Max 20 contracts/trade, $15/day, $5/market
- Min 15% edge (model_prob - market_price - fees)
- Half-Kelly sizing
- Trades both YES and NO sides

**Results (first 2 days):**
- Bot settled 5 weather trades: 3 wins, 2 losses = 60% win rate, 6.9x profit factor, +$27.73 net
- Bot recalibrated after scout analysis: city-specific stdev (CHI 5.0°F, MIA 2.0°F, NYC 2.5°F, DEN 3.0°F) + 95% model prob cap
- Agent desks discovered Muscat Protocol, tracked GDP T2.5 movement, executed CPI rotation

**Key insight:** The March 9 catastrophe ($1,600 loss on 1508 weather contracts) happened because agents had no position sizing discipline. Bots with hard limits solve this structurally — the code physically cannot buy more than 20 contracts.

---

## v9: Pipeline-Driven Firm (2026-04-05)

**Structure:** Same 2 agent desks + 2 bots + quant scouts. **What changed is the process, not the headcount.**

**Strategy Pipeline (4 stages):**
- **Stage 1 Discover** — Market Scanner scout writes hypothesis docs in `strategies/discovery/`. No code, just documented edge.
- **Stage 2 Backtest** — Strategy Developer scout builds backtest in `strategies/backtests/`. Requires 60+ days historical data, 70/30 train/test split, realistic fee simulation, calibration check.
- **Stage 3 Deploy** — Gated by acceptance criteria: profit factor ≥1.3, win rate ≥50%, projected annual return ≥20%, max drawdown ≤25%, ≥30 OOS trades. Deployed strategies start in probationary mode at half size for first 30 live trades.
- **Stage 4 Monitor** — Performance Analyst scout runs daily, compares live metrics to backtest baseline. Decay triggers (30-day negative P&L, win rate drop >15pp, 5 consecutive losses, profit factor <0.8 for 14d) → investigation → fix or archive.

**Scout roles formalized:**
- Market Scanner → Stage 1 owner
- Strategy Developer → Stage 2 owner + Stage 4 investigator
- Performance Analyst → Stage 4 owner (daily runs)

**Why the change:**

The weather bot exposed the problem. It was deployed on Apr 2 with zero backtesting, got lucky day 1 (+$28), then lost on days 2 and 3 (−$15 and −$25). On Apr 3 evening, we "recalibrated" the stdev parameters based on N=1 day of live data — classic overfitting to noise. Net result: 30% win rate, −$12 cumulative P&L, and no way to know if the strategy is fundamentally broken or just running bad.

Lesson: **every parameter change, every new bot, every strategy tweak is a gamble unless backtested first.** The firm was playing live-data roulette dressed up as quant research.

**v9 fixes this structurally:**
- No parameter changes without backtest evidence
- No new bots deployed without passing acceptance gates
- No continuing to run a decaying strategy without formal investigation
- Failed strategies get archived with post-mortems, not quietly forgotten

**Immediate consequence:** Weather bot is flagged as **non-compliant** — it must pass a retroactive Stage 2 backtest or be archived.

**Key insight:** Process discipline beats improvisation. A well-defined pipeline with acceptance gates is cheap to implement and catches exactly the errors we've been making (overfitting, premature deployment, strategy decay blindness).

### 2026-04-10 — Technical Halt: tornado-composite + tsa-composite

**Action**: HALTED both bots per Technical Issue Halt Protocol.

**Root cause**: Both bots have broken scaffolds — missing `place_order` function. The bot files load without error but cannot execute trades. This is a technical failure, not a performance issue.

**Steps taken**:
1. Disabled cron entries for both bots (commented out with HALTED prefix and date)
2. TSA metadata moved from `deployed` → `backtest`, `active: false`
3. Tornado was already at `backtest`, `active: false` — confirmed correct

**Path to redeployment**: Fix `place_order` in both bot scripts → re-run `gate_checker.py` → dual audit (Opus 4.6 + GPT 5.2) → Shaokai approval.

**gas-prices-weekly**: CONDITIONAL_PASS (WR 97%, PF 46.8, p=0.0001, all 7 gates). Queued for dual audit. Synthetic fills caveat requires extended probation if deployed.
