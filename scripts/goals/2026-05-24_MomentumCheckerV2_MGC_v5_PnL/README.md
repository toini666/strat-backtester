# Campaign — MomentumCheckerV2 MGC 7m v5 (PnL focus)

**Date**: 2026-05-24
**Seed**: `BESTWR-MGC MomentumCheckerV2 - MGC 7m v4` (v4 WR winner)
**Goal**: Maximise PnL under WR ≥ 50 % and DD ≤ $2,500.
**Budget**: 500 sims (used ~230).
**Period**: 2025-01-02 → 2026-05-22 (full MGC 7m history).

## TL;DR

| Metric | v4 WR WINNER (seed) | **v5 PnL WINNER** | Δ |
|--------|--------------------:|------------------:|---|
| PnL | $28,162 | **$51,984** | **+$23,822 (+84.6 %)** |
| max_dd_$ | $2,438 | **$2,377** | −$61 |
| Win rate | 51.0 % | **53.7 %** | +2.7 pp |
| Profit factor | 1.29 | **1.50** | +0.21 |
| Trades | 1,056 | 1,062 | +6 |

WR margin above 50 % constraint: **3.7 pp** (≈1 σ for N=1062, much safer than v4's 1 pp).
DD margin under $2,500 budget: **$123**.

Preset name in UI: **`BESTPNL-MGC MomentumCheckerV2 - MGC 7m v5`**.

## Run

```bash
cd /Users/awagon/Documents/dev/nebular-apollo
source venv/bin/activate
python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v5_PnL/verify_preset.py
# Must print "✅ MATCH"
```
