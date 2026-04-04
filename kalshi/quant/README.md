# Kalshi Quant Firm — Dashboard

Live portfolio data for the agentic quant trading firm on Kalshi. Hybrid architecture: weather bots + agent research desks (oil/macro).

**Strategy repo:** [money-making-quant](https://github.com/lsk567/money-making-quant) — full philosophy, trade cycle process, bot code, and agent prompts.

## Files

- `portfolio-history.csv` — Time-series snapshots of portfolio value, positions, and unrealized P&L (updated every cycle by `update_portfolio.sh`)
- `trade-log.csv` — Every trade executed with rationale/thesis (synced from strategy repo each cycle)
- `org-versions.json` — Org structure version history (v1-v8)
- `risk-limits.json` — Current risk parameters
- `corporate-changelog.md` — Qualitative org evolution notes
- `lessons-learned.md` — Post-mortem analysis of key events
- `events.json` — OMAR event log
- `portfolio_snapshot.csv` — Point-in-time position-level detail
