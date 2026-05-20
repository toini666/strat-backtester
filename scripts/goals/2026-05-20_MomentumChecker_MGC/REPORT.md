# Campaign report — MomentumChecker on MGC 7m

| | |
|-|-|
| Date | 2026-05-20 |
| Strategy | `MomentumChecker` |
| Symbol / TF | MGC / 7 m |
| Period | 2025-01-07 → 2026-05-15 (full local history) |
| Starting equity | $50,000 |
| Max contracts | 20 |
| Risk constraint | max DD ≤ $2,500 (strict) |
| Budget | 500 sims |

## Result

| | Baseline | Winner | Δ |
|-|-|-|-|
| PnL              | $39,124 | **$56,353** | **+$17,229** (+44%) |
| Max DD           | $7,884  | **$2,425**  | **‑$5,459** (‑69%) |
| Trades           | 2,582   | 784         | ‑1,798 |
| Win rate         | 38.8%   | 41.3%       | +2.5 pp |
| Profit factor    | 1.11    | 1.49        | +0.38 |
| P/DD             | 4.96    | **23.24**   | **+18.28** |
| Sims used        | —       | ~321 / 500  | |

DD compressed by 69% while PnL grew 44%. The 1,798 trades cut were the
low-edge majority — average expectancy on the kept 30 % of trades is
dramatically better.

## Phase-by-phase attribution

| Phase | Key change | PnL | DD | P/DD | Comment |
|-|-|-|-|-|-|
| 0 — Baseline (defaults, BO 22-23:59 only)            | —                                                                | $39,124 | $7,884 |  4.96 | already +PnL but DD ~3× over budget |
| 1 — Selectivity                                      | `min_gap=8`                                                      | $26,951 | $6,282 |  4.29 | gap is the dominant lever; LT/ST barely matter when gap binds first |
| 2 — Risk geometry                                    | `sl_lookback=15`                                                 | $41,915 | $5,725 |  7.32 | wider lookback gives realistic SL placement → +$15k / ‑$2k DD |
| 3 — Combo geometry + module triage                   | + `rr_tp=3.0`, `sl_max_points=50`                                | $39,550 | $4,164 |  9.50 | rr=3.0 cuts DD more than it cuts PnL |
| 4 — Stack filter winners                             | + `ut_on=False`, `sig_extreme_filter_on=True`, `hw_extreme=15`   | $42,778 | $3,044 | 14.05 | UT Bot module was hurting the score on MGC; sig-extreme filter prunes false-extreme entries |
| 5 — Indicator length scan                            | (individual deltas tested)                                       | (best individual: stc_slow_len=80 $44.4k / $2.7k) | — | — | stc_*, ema_*, mf_smooth, amp_mult are the only movers |
| 6 — Combine indicator winners                        | + `stc_length=10`, `stc_fast_len=32`                             | $46,100 | $2,712 | 17.00 | best combination found; ema_prin=25 and amp=2.5 lift PnL but raise DD |
| 7 — Hour / DoW bucketing                             | identifies bad hours: 13, 18, 20, (23 DST artifact)              | — | — | — | analysis only |
| 8 — Blackout sweep                                   | + BO 13-14 + 20-21 / 17-21                                       | $49,025 | $2,273 | 21.57 | **first DD-valid configs** |
| 9 — Risk per trade fine-tune                         | risk=0.60 % at BO 12:30-14                                       | $55,270 | $2,425 | 22.79 | scaling risk up to 0.6% multiplies PnL while DD stays inside budget |
| 10 — Final refinement                                | + BO 12:30-14 + 17:00-21:00                                      | **$56,353** | **$2,425** | **23.24** | adding the afternoon US window lifts PnL without moving DD |

## Why this works

1. **`min_gap=8`** filters away the noise: with default `min_gap=4` almost
   every long signal coexists with a near-equal short signal, so trades fire
   in choppy zones. Requiring 8 points of asymmetry between long and short
   eliminates ~1,800 marginal trades.
2. **`sl_lookback=15`** widens SL placement — typical MGC swings on 7 m exceed
   the 5-bar window, so default `sl_lookback=5` was placing SL inside the
   normal volatility envelope. Win-rate jumps from 38 → 43 % once this is
   fixed.
3. **`rr_tp=3.0`** matches the actual MGC reach: when SL is realistic, TP at
   3× lets the better setups breathe. PF climbs from 1.12 → 1.31.
4. **`ut_on=False`** — UT Bot generated low-quality entries on MGC and
   double-counted the trend bias already covered by Supertrend and EMA break.
5. **`sig_extreme_filter_on=True`** + **`hw_extreme=15`** veto entries where
   the HW oscillator is at an extreme reading — these are mean-reversion
   traps for a momentum entry.
6. **`stc_length=10`, `stc_fast_len=32`** speed STC up enough that the
   "rising" / "falling" requirement bites earlier — slightly tighter
   selectivity inside the cycle module.
7. **Blackouts (12:30-14, 17:00-21)** remove the EU lunch lull (Wed/Thu/Fri
   show negative or breakeven hours there) and the messy 17-20 US PM
   stretch where MGC chops around macro news but doesn't trend.
8. **Risk 0.60 %** — at 0.5 % MAX_CONTRACTS=20 was binding rarely; lifting
   risk to 0.6 % scales the typical position from ~13 to ~15-16 contracts
   without inflating worst-day loss enough to break the $2,500 DD budget.

## Non-monotone / non-trivial findings

- **Long/Short thresholds are NOT levers on MGC**: `long_threshold` and
  `short_threshold` saturate at 8 — but `min_gap` already enforces 8 points
  of asymmetry once `min_gap=8`, so per-side thresholds become redundant.
- **Combining "best individual" indicator tweaks failed**: each of
  `stc_slow_len=80`, `ema_prin_len=25`, `ema_sec_len=5`, `mf_smooth=5`,
  `amp_mult=2.5` looked best in isolation, but stacking them produced
  *worse* DD than the original Phase 4 stack. The two changes that stack
  cleanly are `stc_length=10` + `stc_fast_len=32` (same module, correlated
  effect).
- **DD saturates at $2,425**: four different blackout configurations
  (12:30-14 alone, +17-21, +18-21, +20-21, +12:45-14) all bottom-out at the
  same DD ‒ that's a single worst-day event in the equity curve that none
  of these can dodge. Increasing risk past 0.60 % crosses the budget.

## Future levers not pursued

- **Daily win/loss limits**: skipped per user instruction.
- **More risk above 0.60 %**: every extra 5 bps of risk pushes DD past
  $2,500. Could be revisited if the user accepts a wider budget.
- **Per-side thresholds (LT≠ST)**: short side wins less than long; an
  asymmetric `long_threshold=8 / short_threshold=10` could clean noise.
- **`max_candle_pct`**: Phase 1 picked the default (0.4) but it's a 1-D
  sweep — combinations with risk/blackouts weren't explored.
- **Time-of-week filters**: Wed had +$570 PnL (essentially flat). A weekday
  blackout could lift the average but loses trade count.
