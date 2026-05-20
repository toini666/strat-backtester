# Campaign Report — MomentumCheckerV2 MNQ 7m (v2, corrected)

**Date**: 2026-05-20 (v2 follow-up after the v1 campaign discovered a metric bug)
**Result**: PnL **$80,565** / $DD **$3,023** / N=797 / WR=40.4% / PF=1.58 / **P/DD=26.65**
**vs V1 anchor**: **+$19,252 PnL (+31.4%) AND −$51 $DD** — clean Pareto improvement
**Period**: 2025-01-07 → 2026-05-15 (16+ months)

## Context — the v1 campaign and the bug

The first campaign (`scripts/goals/2026-05-20_MomentumCheckerV2_MNQ/`) optimised
against a buggy metric. `src/engine/simulator.py:max_drawdown_dollars` returned
the `$` peak-to-trough at the moment of `%` max drawdown — not the worst-ever
`$` peak-to-trough.

For a low-PnL strategy these align (peak ≈ initial equity). For a high-PnL one
they diverge significantly: a $3.3k drop on a $115k peak (2.87%) is worse in $
than a $1.8k drop on a $54k peak (3.33%) — the buggy code reported the latter.

The v1 winner ($69,819 / "$DD=$1,866") had a TRUE $DD of $3,326 — over V1's
true $DD ceiling of $3,074 by $252. The v1 optimisation pushed risk up
aggressively to maximise the apparent PnL/DD ratio, but only because the
high-equity-peak $DD wasn't being measured.

### The fix

```python
# simulator.py:1840
for v in eq_values:
    if v > peak:
        peak = v
    dollar_dd = peak - v
    pct_dd = dollar_dd / peak if peak > 0 else 0
    if pct_dd > max_dd:
        max_dd = pct_dd           # tracked independently
    if dollar_dd > max_dd_dollars:
        max_dd_dollars = dollar_dd  # NOT tied to %_max
```

## Goal

- Reproduce the V1 preset *New base - MomentumChecker - MNQ 7m* with V2 (V1-compat). ✓ (done in v1 campaign)
- Optimize PnL with:
  - **Hard ceiling**: TRUE $DD ≤ V1's TRUE $DD = $3,074
  - **Soft target**: $DD < $2,000
- Fixed: symbol MNQ, TF 7m, period, max contracts=20, no daily limits.

## New baseline — "B combo"

The v1 campaign's Phase 11 re-rank (with the patched simulator) identified the
strongest starting point as:

```python
amp_mult         = 3.0
max_candle_pct   = 0.3
sig_extreme      = 40 (filter ON)
sl_max_points    = 60
# all other params: V1-compat anchor
```

At risk=0.55%: PnL=$71,371 / $DD=$2,900 / P/DD=24.61 — already beating V1
by +$10k PnL with $174 lower DD.

## Lever-by-lever attribution (v2 → winner)

Going from B baseline ($71,371 / $2,900) → winner ($80,565 / $3,023):

### 1. `amp_mult: 3.0 → 3.5`  (P5 finding)

Wider HMA-canal envelope. Better filtering of weak breakouts. +$792 PnL with
same $DD at the B baseline.

### 2. `pts_hma_slow=1 + ssl_len=60 + hma_window_bars=5`  (P1 finding)

Enables V2's "HMA-slow / SSL cross" bucket. Adds quality signals that the
strategy was missing. Slight Pareto improvement: +$168 PnL, −$176 $DD at the
baseline risk.

### 3. `st_atr: 14 → 10`  (P5 finding)

Tighter Supertrend ATR. Improves bucket scoring. −$129 $DD with similar PnL.

### 4. `tick_buffer: 0 → 2`  (P3 finding)

Adds 2 ticks of buffer to the SL (essentially: SL is set 2 ticks further from
entry). Reduces stop-out frequency on noise. −$74 $DD with small PnL trade-off.

### 5. Blackout extension `13-14 → 13-14:30`  (P9 finding)

The single best engine-level lever. Extends the European midday blackout by
30 minutes, blocking the start of the US session's "lunch reversal" period.

| | risk 0.62% / 09-10,13-14,17-24 | risk 0.62% / 09-10,**13-14:30**,17-24 |
|---|---|---|
| PnL | $76,060 | **$76,174** (+$114) |
| $DD | $3,036 | **$2,846** (−$190) |
| P/DD | 25.05 | **26.77** |

### 6. `risk_per_trade: 0.55% → 0.66%`  (P10 final risk sweep)

Once all the above were locked, scaling risk up brought PnL to $80,565 with
$DD still at $3,023 (just under V1 ceiling).

**Note**: there's expected non-monotonicity at sizing boundaries — at 0.58%
the DD jumped to $2,852 while at 0.66% it's $3,023. These are deterministic
but reflect the int(contracts) rounding flipping at specific risk levels.
The risk band 0.60-0.66% is uniformly safe — DD stays $2,793-$3,036.

## Final stats — winner vs V1 anchor

| | V1 anchor (true DD) | **v2 winner** | Delta |
|---|---|---|---|
| Net PnL | $61,313 | **$80,565** | **+$19,252 (+31.4%)** |
| Max $ DD | $3,074 | **$3,023** | **−$51 (−1.7%)** |
| Max % DD | 4.12% | 3.61% | −0.51pp |
| Trades | 785 | 797 | +12 |
| Win rate | 39.6% | 40.4% | +0.8pp |
| Profit factor | 1.5 | 1.58 | +0.08 |
| Avg win | $589 | $679 | +$90 |
| Avg loss | −$257 | −$291 | −$34 |
| P/DD ratio | 19.95 | **26.65** | **+6.70** |

## Sub-$2,000 alternative

If the user prefers DD < $2,000 (the soft target), the strongest config is the
same strategy stack at **risk=0.44%**:
- PnL = $47,623 / $DD = $1,971 / P/DD = 24.16

This sacrifices ~$33k PnL vs the main winner but stays comfortably under $2k.
The user can change risk to 0.44% on the saved preset in the UI to switch
between the two.

## Comparison with v1 campaign

| Campaign | "Apparent" $DD | True $DD | True PnL |
|---|---|---|---|
| V1 baseline | $2,143 | $3,074 | $61,313 |
| v1 winner | $1,866 | **$3,326 ❌ (over budget)** | $69,819 |
| **v2 winner** | $3,023 (same) | **$3,023 ✓** | **$80,565** |

The v1 winner was over V1's actual DD budget once the bug was patched.
The v2 winner is a genuine Pareto improvement — measurable, deterministic,
and reproducible in the UI.

## Sim budget accounting

| Phase | Description | Sims |
|---|---|---|
| 0 | Baselines | 1 |
| 1 | V2-new features re-test | 30 |
| 2 | Thresholds & gap | 28 |
| 3 | Risk geometry | 35 |
| 4 | Module toggles | 30 |
| 5 | Indicator lengths | 75 |
| 6 | Stack-the-wins combo | 52 |
| 7 | Master combo + risk sweep | 50 |
| 8 | Pareto fine-tune | 76 |
| 9 | Blackout sensitivity | 18 |
| 10 | Final risk-band validation | 16 |
| | **Total** | **411 / 500** |

Within budget. Phase 11 (re-rank from v1) added another ~90 sims of
re-evaluation that informed the B-baseline starting point.
