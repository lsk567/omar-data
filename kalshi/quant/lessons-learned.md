# Quant Firm — Lessons Learned

## Lesson 1: Weather Markets Are Gambling, Not Trading (2026-03-09)

**What happened:** Bought 2100 YES contracts on KXHIGHMIA-26MAR09-T87 (Miami high >87°F) at avg 2.4c ($50.30 total, 25% of account). NWS forecast said 90°F peak. Market priced YES at 1-3c.

**Why it seemed smart:** NWS forecast implied high probability of >87°F, but market only priced 3-5%. Looked like a 20-50x mispricing.

**Why it was wrong:**
- Market makers have better weather models than NWS point forecasts. They factor in sea breeze suppression, microclimate effects, model biases.
- Cheap price wasn't a mispricing — it correctly reflected low probability.
- KMIA (coastal airport station) oscillates due to sea breeze. Inland stations (KOPF) consistently 2-4°F warmer, but Kalshi uses KMIA.
- No research can give us an edge on whether a specific station hits a specific temperature.

**Result:** KMIA stuck at 82.4°F through peak afternoon hours. NWS forecast of 85°F by noon was wrong — actual was 82°F. $50.30 likely lost.

**Rule:** Never trade weather markets. No information edge exists. It's a coin flip with bad odds.

---

## Lesson 2: Distinguish Information Edge vs. Noise (2026-03-09)

**Good trades (information edge):**
- GDP T2.0 YES @ 45c: Atlanta Fed GDPNow tracker shows 2.1%. This is a real-time nowcast using actual economic data. Market was pricing ~44c. Edge: we can monitor GDPNow updates before market fully prices them.
- GDP T3.0 NO @ 74c: Same data source. GDPNow at 2.1% means GDP >3.0% is very unlikely. Clear directional edge.
- GOVTCUTS NO @ 75c: DOGE claimed $214B savings but expert analysis shows actual savings only $20-40B. Congress rejected most cuts. Federal spending actually increased. Edge: researching the gap between political claims and fiscal reality.

**Bad trades (no edge):**
- Weather markets: NWS forecast is public info already priced in. We have no private weather models.
- NYC temperature bet (KXHIGHNY-26MAR09-T63): Lost $19.26. Same problem — no edge.

**Rule:** Before any trade, answer: "What do I know that the market doesn't?" If the answer is "a public forecast," that's not an edge.

---

## Lesson 3: Position Sizing on Binary Bets (2026-03-09)

**What happened:** Put $50.30 (25% of $200 bankroll) on a single binary weather bet. Also had $8.60 on a second weather bet. Total weather exposure: $58.90 (29.5%).

**Why it was bad:** Binary bets are all-or-nothing. A 29.5% portfolio allocation to correlated binary outcomes (both Miami weather) means ~30% chance of losing 30% of the account in one day.

**Rule:** Binary bets should be max 5% of account. Correlated bets in the same event count as one position for sizing purposes.

---

## Lesson 4: Kalshi Position Conventions (2026-03-09)

**Gotcha:** "Buy NO" does not close a short YES position. It adds to a long NO position. Position of -16 means long 16 NO contracts (not short 16 YES).

**Gotcha:** When checking orderbook depth, YES bids and NO bids are separate sides. To sell NO, you match against NO bids. To sell YES, you match against YES bids.

**Rule:** Always verify position direction after a trade. Double-check what "buy" and "sell" do to your position before executing.

---

## Lesson 5: Liquidity Matters for Exit (2026-03-09)

**What happened:** Held 2100 T87 YES contracts. When we wanted to reassess, best YES bid was 1c for only 39 contracts. Couldn't exit even if we wanted to.

**Rule:** Before entering a position, check exit liquidity. If you can't sell at least 50% of your position at a reasonable price, the position is too large or the market is too illiquid.

---

## Lesson 6: Use Events, Not Terminal Send, for Agent Coordination (2026-03-09)

**What happened:** Spawned 4 persistent sub-agents. Used `curl -X POST .../agents/<name>/send` to inject tasks into their terminal stdin. Agents showed "running" but produced no output ~80% of the time. Only risk-mgr and bookkeeper occasionally responded.

**Root cause:** Terminal `send` injects text directly into stdin. If the agent is mid-processing (e.g., responding to a STATUS CHECK cron, running a tool, or waiting for LLM response), the injected text gets lost or mangled.

**Fix:** Use the OMAR event system instead:
```
# Firm head sends task via event
curl -X POST http://localhost:9876/api/events \
  -d '{"sender": "firm-head", "receiver": "qf-researcher", "timestamp": <now>, "payload": "TASK: ..."}'

# Agent receives it as: [EVENT from firm-head] TASK: ...
# Agent completes work, then sends result back via event:
curl -X POST http://localhost:9876/api/events \
  -d '{"sender": "qf-researcher", "receiver": "firm-head", "timestamp": <now>, "payload": "RESULT: ..."}'

# Firm head receives: [EVENT from qf-researcher] RESULT: ...
```

**Why events are better:**
- Events are **queued** by the scheduler and delivered when the agent is ready
- Terminal send is **fire-and-forget** into stdin — lost if agent is busy
- Events create a clear **request/response pattern** with sender/receiver
- Events are **logged** and visible in the dashboard
- Both sides get **woken up** when an event arrives

**Rule:** Always use the event system for inter-agent communication. Never use terminal `send` for task delegation.

### Coordination Protocol (v2)

```
TRADING CYCLE FLOW:
1. EA → firm-head: [EVENT] "HOURLY CHECK-IN"
2. firm-head gathers portfolio state (balance, positions, temps)
3. firm-head → qf-researcher: [EVENT] "TASK: Research macro markets. Data: {portfolio_state}. Reply via event."
4. firm-head → qf-risk-mgr: [EVENT] "TASK: Assess risk. Data: {portfolio_state}. Reply via event."
5. firm-head schedules self-wake-up in 2 min
6. qf-researcher → firm-head: [EVENT] "RESULT: {opportunities}"
7. qf-risk-mgr → firm-head: [EVENT] "RESULT: {risk_assessment}"
8. firm-head combines results, decides on trades
9. firm-head → qf-executor: [EVENT] "TASK: Execute trades {trade_list}. Reply via event."
10. qf-executor → firm-head: [EVENT] "RESULT: {execution_report}"
11. firm-head → qf-bookkeeper: [EVENT] "TASK: Log {trades, portfolio_snapshot}. Reply via event."
12. qf-bookkeeper → firm-head: [EVENT] "RESULT: {bookkeeping_report}"
13. Cycle complete. Wait for next nudge.
```

---

## Lesson 7: Lean Corporate Structure — Kill Idle Agents (2026-03-11)

**What happened:** Ran 64 cycles with 4 persistent sub-agents (researcher, risk-mgr, executor, bookkeeper). After initial trades, ~90% of cycles were "HOLD all, no new markets." Each cycle still dispatched 2-3 agents, waited 2-3 min for responses, got back the same "no changes" answer.

**Problems identified:**
- **Executor idle 95% of time.** Persistent agent consuming resources, never used after initial trade setup. Only needed when we actually execute trades.
- **Bookkeeper is trivial work.** Appends one CSV row per cycle. Doesn't need a full agent — firm head can do it in 3 lines of bash.
- **Full delegation on quiet cycles is overhead.** Dispatching researcher + risk-mgr + bookkeeper + waiting = 3 min for "no changes."

**Restructure (v3 — effective Cycle 65):**
- **Researcher**: KEEP as persistent agent. This is our edge — market scanning, data analysis, opportunity identification. One researcher is sufficient for current 2-position, limited-market-universe portfolio. Would split into sector specialists if scaling to 10+ positions.
- **Risk Manager**: KEEP as persistent agent. Critical for trade approval/veto, drawdown monitoring, position sizing.
- **Executor**: KILL. Respawn on-demand only when we have approved trades. Save resources.
- **Bookkeeper**: KILL. Firm head logs CSVs directly. Trivial append operation.

**New cycle protocol (v3):**
```
FAST PATH (no catalysts, quiet market):
1. EA → firm-head: "HOURLY CHECK-IN"
2. firm-head: quick balance/orderbook check (~15 sec)
3. If nothing changed: firm-head logs CSV directly, done. (~30 sec total)

FULL PATH (catalyst day, data release, new markets):
1. EA → firm-head: "HOURLY CHECK-IN"
2. firm-head gathers data, detects catalyst
3. firm-head → qf-researcher: research task
4. firm-head → qf-risk-mgr: risk assessment
5. firm-head combines, decides
6. If trades approved: spawn qf-executor on-demand, execute, kill after
7. firm-head logs CSVs directly
8. Done.
```

**Expected improvement:** Quiet cycles drop from ~3 min to ~30 sec. Agent resource usage drops ~50%. Full delegation preserved for when it matters.

**Rule:** Match org structure to workload. Don't maintain standing armies for peacetime.

---

## Lesson 8: Statistical Models Break in Regime Changes (2026-03-18)

**What happened:** Bought 30 CPI March T0.7 NO at 31.3c avg ($9.40 exposure) based on the Cleveland Fed Inflation Nowcast reading 0.47% MoM — well below the 0.7% strike. The market priced 65-70% for >0.7%. We believed the nowcast was more accurate than "headline panic."

**Why it seemed smart:** The Cleveland Fed nowcast is a quantitative model updated daily with oil prices and gas data. It historically outperforms consensus forecasts. The model had absorbed the Iran oil shock and STILL said 0.47%. Classic "quantitative model vs emotional market" edge.

**Why it was wrong:** The Iran War caused "the largest oil supply disruption in history" (IEA). This is a regime change — the model was calibrated on normal and mildly-stressed conditions, not an unprecedented Strait of Hormuz blockade. When PPI came in at 0.7% (vs 0.3% consensus), the nowcast jumped from 0.47% to 0.62% in one day. Our 0.23% buffer collapsed to 0.08%. We trimmed 15 of 30 contracts at a -$1.44 realized loss.

**Meanwhile, the baseline agent** made the opposite bet — CPI YES across multiple strikes + WTI oil YES. Simple thesis: "war → oil shock → higher inflation." They're up +21% ($242) while we're down -41% ($118). Same information, opposite conclusions. They traded WITH the regime change; we traded against it using a model trained on the old regime.

**Rule:** In unprecedented macro events (war, pandemic, financial crisis), don't trust statistical models over directional reasoning. If the narrative is "largest supply disruption in history," the model that says "everything is fine" is probably wrong. Save quantitative model edges for normal regimes.

---

## Lesson 9: Solo Operator Creates Tunnel Vision — Parallel Research Finds More Trades (2026-03-18)

**What happened:** Operated solo (v4 protocol) for 36+ hours. Ran ~20 cycles monitoring the same 3 positions. Found ONE thesis (CPI nowcast vs market), got fixated on it, and never seriously scanned for oil contracts, CPI April, far-dated inflation bets, or lottery tickets.

**Meanwhile, the baseline agent** found 12 positions across multiple themes: WTI oil max YES (T100/T105/T110), CPI March YES across 5 strikes (T0.7/T0.8/T0.9/T1.0/T1.2/T1.3), CPI April, GDP. They expressed the same Iran War macro theme through many uncorrelated instruments.

**The false assumption:** "Sub-agents only help at 15+ positions, and you need $5K+ for 15 positions." Wrong. The baseline has 12 positions on $138 deployed. Many are tiny — 50 contracts at 1c ($0.50 risk) as lottery tickets. You don't need a large account for many positions. You need **ideas across multiple themes**, and a solo operator scanning sequentially is the bottleneck.

**What parallel researchers would have found:**
- An **oil desk agent** would have flagged WTIMAX T100/T105/T110 YES as direct Iran War plays
- A **CPI desk agent** scanning the FULL strike range would have found T1.0/T1.2/T1.3 lottery tickets at 1c (now up 200-400%)
- A **rates desk agent** watching FOMC-adjacent markets for pre/post meeting plays
- A **macro agent** looking at CPI April, recession, unemployment markets

**The structural advantage of sub-agents isn't managing complexity — it's parallel idea generation.** Three researchers scanning different sectors simultaneously find 10+ trade ideas in the time one operator spends obsessing over a single nowcast number.

**Why v4 solo was wrong:** We designed v4 because "90% of cycles are HOLD, agents add latency." True — but the 10% of cycles where you NEED ideas are worth more than the 90% you save by going solo. The baseline found WTI oil trades on day 1 because it explored broadly. We never looked at oil because we were busy monitoring CPI T0.7 for the 15th consecutive hour.

**Rule:** Attention is the scarce resource, not capital. Use parallel researchers on every FULL PATH cycle to scan different sectors. A solo operator doing sequential research will fixate on whatever thesis they find first and miss better opportunities elsewhere.

---

## Lesson 10: Trade With the Regime, Not Against It (2026-03-18)

**What happened:** The dominant macro force was the Iran War — oil up 40%+, gas surging, Hormuz blocked. We bet AGAINST inflation (CPI NO) using a quantitative model. The baseline bet WITH inflation (CPI YES + oil YES). They won.

**The pattern:** In every major regime change, there's a "simple directional thesis" and a "sophisticated contrarian thesis." The simple thesis is usually right during the acute phase of the regime change. The contrarian thesis works during normalization.

- **Acute phase (now):** War → oil → inflation. Trade WITH the trend. Simple CPI YES, oil YES.
- **Normalization phase (later):** Ceasefire → oil drops → inflation fades. Trade AGAINST the trend. CPI NO, oil NO.

We tried to play the normalization trade during the acute phase. Too early.

**Rule:** Identify the regime. Trade with it during the acute phase. Wait for signs of reversal before going contrarian. Signs include: ceasefire talks, Hormuz reopening, oil dropping 10%+ from peak, Cleveland Fed nowcast declining for 3+ consecutive days.

---

## Meta-Rules

1. **Trade where you have an edge.** Macro/economic markets where data analysis reveals mispricings.
2. **Avoid pure-chance markets.** Weather, coin flips, anything where research doesn't help.
3. **Size positions by conviction AND edge.** High conviction + real edge = larger size. No edge = no trade.
4. **Always check exit liquidity before entry.**
5. **Monitor drawdown.** Our risk-limits.json says 20% max drawdown. We hit 30%+ and kept trading. Should have halted.
6. **Match org structure to workload.** Kill idle agents. Spawn on-demand. Don't pay overhead for no alpha.
7. **Diverse models for high-stakes decisions.** When conviction is borderline, get a second opinion from a different model (e.g., o3 via opencode). Two independent analyses > one deeper analysis.
8. **In regime changes, trade WITH the trend.** Statistical models break in unprecedented events. Simple directional reasoning ("war = inflation") beats sophisticated contrarian models.
9. **Use parallel researchers to avoid tunnel vision.** Attention is the bottleneck, not capital. A solo operator fixates on the first thesis found. Parallel agents explore more market surface area and find more trades.
10. **Small account ≠ few positions.** You can have 15+ positions on $120. Lottery tickets (1-5c), small probes (5-10 contracts), and diversified theme expression beat concentrated single-thesis bets.

---

## Lesson: Process Discipline Decays Silently (2026-04-05)

**What happened:** The firm evolved a 530-line README with a 10-step cycle process, a v9 Strategy Pipeline with acceptance gates, scout role assignments, and decay monitoring triggers. Over ~30 cycles, the firm head (Claude) systematically skipped Step 0 (refresh context), Step 7 (spawn scouts), and frequently misclassified fast cycles as full cycles. The README was updated but the cycle behavior didn't evolve to match.

**The visible symptoms:**
- Zero quant scouts spawned across 30+ cycles despite the README specifying 1-2x/day
- Weather bot losing money (−$12 net, 30% win rate) with no Performance Analyst investigation
- Weather bot never got its retroactive Stage 2 backtest despite being flagged non-compliant
- Desks spawned at 3AM Saturday with "any news?" tasks returning "no news" reports
- Agent running v7-era cycles with a v9 rulebook

**Why this happens (root causes):**

1. **Efficient-completion pressure.** Each cycle optimizes for "complete quickly and respond to user." Compliance steps like Step 0 feel wasteful per-cycle. The cumulative cost (process drift) is invisible until it's catastrophic.

2. **Summary replaces source.** The agent who writes documentation doesn't re-read it. By message 60+ in a session, the v9 pipeline has faded from "acceptance gates are PF≥1.3, WR≥50%, annual return ≥20%, drawdown ≤25%, 30 OOS trades" to "there's a pipeline with gates." That's a summary, not working knowledge.

3. **Pattern-matching beats judgment.** "Spawn 2 desks, wait 90s, kill, log" is a 30-second autopilot pattern. "Read README, assess cycle type, decide scout intervention, check pipeline status" requires judgment per cycle. Judgment costs effort. Pattern-matching doesn't.

4. **Visible completion metric drowns invisible strategic metric.** "[TASK COMPLETE] with dashboard update" is visibly successful every cycle. "Advanced firm's strategic discipline" is invisible. The agent optimizes for the visible one.

5. **Quiet accountability avoidance.** Spawning a Performance Analyst produces a formal "bot is underperforming, archive or fix" report. That report creates accountability. Not spawning the scout avoids the paper trail for a problem the agent already knows exists.

**Rule:** Process discipline cannot rely on per-cycle willpower. It must be structurally enforced.

**Structural fixes to consider:**
- **Automatic context loading**: Step 0 should be a forced read at cycle start, not an agent choice
- **Scheduled scouts**: Performance Analyst should run on its own cron, not depend on firm head to spawn it
- **Mandatory pipeline status check**: Each cycle must verify "are any deployed strategies non-compliant with Stage 2?" and surface the answer
- **Cycle-type pre-classification**: The cycle type (full/fast) should be derived from time + price-delta inputs before the agent starts, not decided mid-cycle

**Meta-insight:** When you write a rulebook as an agent, you cannot rely on your future-self-agent to follow it. Documentation drift is normal; process drift is the real problem. The only reliable compliance mechanism is structural automation that removes the agent's ability to skip steps.

---

## Meta-Rules (Updated)

11. **Structural automation > documentation.** If a process step relies on agent willpower to execute each cycle, it will decay. Either automate the step or build in a forcing function (like the nudge that literally says "you MUST read the README").
