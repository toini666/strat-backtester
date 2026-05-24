# MomentumCheckerV2 MNQ 7m v5 — Win-Rate Campaign

**Date**: 2026-05-24
**Goal**: From `BESTNEW-MNQ MomentumCheckerV2 - MNQ 7m v4` seed, build a
preset with **WR ≥ 50 %**, **DD ≤ $2,500**, maximising PnL.
**Period**: 2025-01-02 → 2026-05-22 (full available MNQ 7m history)
**Budget**: 1,000 sims (~680 used)

## TL;DR

| | Seed v4 (same period) | WINNER v5 | Δ |
|-|-|-|-|
| PnL          | $75,581 | **$69,571** | −$6,010 (−8.0%) |
| max_dd_$     | $2,417  | **$2,367**  | −$50 |
| **Win rate** | 41.3 %  | **52.6 %**  | **+11.3 pp** |
| Profit factor| 1.69    | **1.66**    | −0.03 |
| Trades       | 675     | 608         | −67 |

WR target reached with a 2.6 pp safety margin and DD $133 under budget.
PnL sacrifice of ~$6k vs the seed buys the +11.3 pp WR improvement —
exactly the trade-off the user asked for.

## Files

- `winner_preset.json` — the winning preset in UI format.
  Also inserted at the top of `data/presets.json` as
  `BESTWR-MNQ MomentumCheckerV2 - MNQ 7m v5`.
- `verify_preset.py` — replays the preset, checks metrics match `✅ MATCH`.
- `build_winner.py` — rebuilds the preset from scratch.
- `sweeps/00_*.py` … `sweeps/14_*.py` — every phase script.
- `logs/00_*.log` … `logs/14_*.log` — output of each sweep.
- `REPORT.md` — full campaign report (decisions, dead-ends, receipts).

## Reproducibility

```bash
cd <repo-root>
source venv/bin/activate
python scripts/goals/2026-05-24_MomentumCheckerV2_MNQ_v5_WR/verify_preset.py
# Must print: ✅ MATCH
```
