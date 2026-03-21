# Event Logging Guide

This guide explains how trader agents should log key events to `events.json`.

## File Locations

- **Baseline trader**: `kalshi/baseline/events.json`
- **Quant trader**: `kalshi/quant/events.json`

## Schema

Each entry is a JSON object in an array:

```json
{
  "timestamp": "2026-03-18T13:22:00Z",
  "type": "macro",
  "title": "Feb PPI hot — 0.7% vs 0.3% consensus",
  "detail": "Headline PPI more than double consensus. Core 0.5% vs 0.3%. Pre-war data showing inflation already accelerating."
}
```

### Fields

| Field | Format | Description |
|-------|--------|-------------|
| `timestamp` | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) | When the event occurred |
| `type` | string | Event category (see below) |
| `title` | string, ~50 chars | Short headline with key numbers |
| `detail` | string, 1-2 sentences | Context, numbers, and impact on positions |

### Event Types

| Type | Use For |
|------|---------|
| `trade` | Trades executed (buys, sells, position changes) |
| `macro` | Economic data releases, geopolitical events, oil moves |
| `win` | Positions that settled in our favor |
| `loss` | Positions that settled against us, stop-losses hit |
| `milestone` | ATH, ATL, profit milestones, portfolio records |
| `crash` | Flash crashes, pricing glitches, sudden drawdowns |
| `org` | System/architecture changes (version upgrades, agent changes) |
| `cycle` | Notable trading cycle summaries (network issues, scan results) |

## Rules

1. **ONLY log events that have ALREADY HAPPENED.** Write in past tense. Never add future predictions, upcoming catalysts, or scheduled events.
2. **Be specific with numbers.** Include prices, percentages, contract names, and position sizes.
3. **Append to the end** of the existing array. Do not reorder or modify past entries.
4. **Log during each trading cycle** if any of the following occurred:
   - A trade was executed (buy or sell)
   - A major market move (>5% in a key asset like WTI, or >10c move in a Kalshi contract)
   - An economic data release that affects positions (CPI, PPI, GDP, PCE, NFP, FOMC)
   - A geopolitical event that moved markets (conflict escalation, sanctions, supply disruptions)
   - A position settled (won or lost)
   - A portfolio milestone was hit (new ATH, ATL, or profit threshold)
5. **Do NOT log** routine HOLD cycles with no significant moves.
6. **Keep the JSON valid.** Ensure proper comma separation and array brackets.

## Example: Logging a Trade

```json
{
  "timestamp": "2026-03-19T12:26:00Z",
  "type": "trade",
  "title": "Lottery ticket profit take — CPI T1.1",
  "detail": "Sold 15 of 30 CPI Mar T1.1 YES @17c (bought @6c). Realized +$1.65. Holding 15."
}
```

## Example: Logging a Macro Event

```json
{
  "timestamp": "2026-03-21T03:00:00Z",
  "type": "macro",
  "title": "Oil re-escalation — Iraq force majeure, Kuwait struck",
  "detail": "WTI $98.32 (+2.3%), Brent $112.19. Iraq force majeure at all foreign oilfields. Kuwait refineries hit by drones. 8M bpd global supply contraction (IEA)."
}
```
