# Kalshi Quant Firm — Public Dashboard

Live portfolio data for the agentic quant trading firm on Kalshi. Hybrid architecture: weather bots + agent research desks (oil/macro).

## Files

- `portfolio-history.csv` — Per-cycle snapshots: portfolio value, positions, unrealized P&L, and notes with trade rationale (updated every cycle)
- `events.json` — Key events: org changes, trades, crashes, milestones, macro developments (updated on notable events)
- `org-versions.json` — Org structure version history (v1-v8) with agent counts and architecture summaries (used by public website)
- `corporate-changelog.md` — Detailed prose changelog: rationale, problems, solutions, and insights for each org version
- `lessons-learned.md` — Post-mortem analysis of key mistakes and what changed
