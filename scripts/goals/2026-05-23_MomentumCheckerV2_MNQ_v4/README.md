# Campaign — MomentumCheckerV2 MNQ 7m v4 (2026-05-23)

Goal: from the user-provided seed `BEST-MNQ MomentumCheckerV2 - MNQ 7m`
(PnL $75.1k / DD $2,420 / WR 39.6%), find a config that (a) improves PnL,
(b) keeps `max_dd_$` ≤ seed, (c) increases the win rate. Two new params
were available since the previous campaign: `sl_min_pct` (SL floor in %
of entry) and the SIG range filter (`sig_filter_on`/`sig_level`/
`pts_sig_value`). A simulator-side change exposes `sl_rate` / `be_rate`
in the metrics dict and on the dashboard.

User-frozen constraints (NOT changed in this campaign):
  - Symbol = MNQ, Timeframe = 7m
  - Date range = 2025-01-07 → 2026-05-15
  - max_contracts = 20
  - Daily limits OFF

Sim budget: 500 (used ~430).

## Result

| | Seed | WINNER | Δ |
|-|-|-|-|
| PnL          | $75,132 | **$88,430** | **+$13,298 (+17.7 %)** |
| max_dd_$     | $2,420  | **$2,341**  | **−$79 (−3.3 %)** |
| Win rate     | 39.6 %  | **41.8 %**  | **+2.2 pp** |
| SL rate      | 60.3 %  | 57.9 %      | −2.4 pp |
| Profit factor| 1.56    | **1.72**    | +0.16 |
| Trades       | 828     | 765         | −63 |

All three goals achieved simultaneously. See REPORT.md for the full
phase-by-phase narrative.

## What changed vs seed

| Param | Seed | WINNER |
|-|-|-|
| `ema_prin_len`     | 30   | **34** |
| `ema_sec_len`      | 20   | **18** |
| `st_atr`           | 10   | **14** |
| `tick_buffer`      | 2    | **0**  |
| `sl_max_points`    | 41   | **42** |
| `riskPerTrade`     | 0.6 %| **0.625 %** |
| Blackout 07-08     | —    | **active (NEW)** |

Everything else (HMA stack, oscillator filters, alligator, UT, STC,
points weights, thresholds, sl_lookback…) is identical to seed.

## Reproduce

```bash
python scripts/goals/2026-05-23_MomentumCheckerV2_MNQ_v4/verify_preset.py
```

Must print `✅ MATCH`. Or load the preset
`BEST-MNQ MomentumCheckerV2 - MNQ 7m v4` from the UI favorites list.
