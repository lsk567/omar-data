# Kalshi Quant Firm — Dashboard

Live portfolio data for the agentic quant trading firm on Kalshi. Hybrid architecture: weather bots + agent research desks (oil/macro).

**Strategy repo:** [money-making-quant](https://github.com/lsk567/money-making-quant) — full philosophy, trade cycle process, bot code, agent prompts, and detailed trade log.

## Files

- `portfolio-history.csv` — Time-series snapshots: portfolio value, positions, unrealized P&L, and cycle notes with trade rationale (updated every cycle by `update_portfolio.sh`)
- `events.json` — Key events: org changes, trades, crashes, milestones, macro developments (updated when notable events occur)
- `org-versions.json` — Org structure version history (v1-v8) with agent counts and architecture summaries
- `risk-limits.json` — Current risk parameters (position limits, bot limits, drawdown thresholds)
- `corporate-changelog.md` — Qualitative org evolution notes
- `lessons-learned.md` — Post-mortem analysis of key events
- `portfolio_snapshot.csv` — Point-in-time position-level detail
