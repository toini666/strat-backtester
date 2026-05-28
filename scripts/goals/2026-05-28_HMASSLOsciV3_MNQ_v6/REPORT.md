# Campaign Report — HMASSLOsciV3 MNQ 7m v6

**Date:** 2026-05-28
**Goal:** Improve PnL (or keep similar) AND reduce max DD vs seed preset
`MNQ-PROD - HMASSLOsciV3 - MNQ 7m`.
**Constraints:** symbol / interval / date range / max_contracts(20) /
daily limits OFF — all locked. Free: strategy params, blackouts, risk_per_trade.
**Budget:** 500 simulations. **Used:** ~332.

## TL;DR

| Metric | Seed | Winner | Δ |
|--------|-----:|-------:|---:|
| PnL    | $63,143 | **$80,709** | **+$17,566 (+27.8%)** |
| Max DD ($) | $3,557 | **$3,236** | **−$321 (−9.0%)** |
| Trades | 1,070 | 1,299 | +21.4% |
| Win rate | 49.3% | 48.7% | −0.6pt |
| Profit factor | 1.75 | 1.64 | −0.11 |
| Risk per trade | 0.50% | 0.60% | +0.10pt |

Strict Pareto improvement: more PnL AND less DD. The PnL bump is mostly from
additional trade volume + risk uplift; the DD cut comes from removing the
bad-hour exposure (H06, H08 morning, H11–H13 European session) and adding the
14:30–15:00 micro-blackout. The strategy parameter stack
(`hma_pol_bars`, `sig_extreme`, `hw_extreme`, `mf_length`) was retuned and is
the source of the higher trade frequency.

## Winner config

**Strategy params** (only deltas vs seed shown):
```
hma_pol_bars:  0 → 5     (was the floor at the bottom of the param_ranges grid)
sig_extreme:  40 → 60    (effectively saturates the filter; ≥60 plateau)
hw_extreme:   20 → 35
mf_length:    37 → 31    (DD valley — see Sweep 03/04)
```
All other strategy params are **kept identical** to the seed, including all
three new v3.1 params at their default off positions
(`min_sl_points=0`, `entry_cross_mode="Baseline"`, `ema_exit_ext_on=False`).

**Blackouts** (reference Brussels time):
```
22:00–23:59  (close)        — unchanged
 6:00–09:00  (morning)      — replaces seed 5–9: tighter, avoids H05 (positive)
11:00–14:00  (Euro session) — replaces seed 11–13: extends to cover H13
14:30–15:00  (US pre-open)  — replaces seed 14–15: tighter, keeps the H14 first half
```

**Risk per trade:** 0.60% (seed: 0.50%).
**Auto-close:** 22:00, **max_contracts:** 20 — both unchanged.

## New v3.1 params — findings

The user specifically asked for an evaluation of the three new v3.1 params.
**Net result: none of them ended up in the winner.** Findings:

### `min_sl_points` (default 0 = off)

Smooth, **monotone trade-off** between PnL and DD: raising the floor cuts both
at roughly the same rate. No sweet spot above seed. Tested 0, 5, 10, 15, 20,
30, 40, 50, 60, 80; the seed setting (0) sits on the Pareto frontier.

| min_sl_points | PnL | DD$ |
|--------------:|----:|----:|
| 0 (seed) | $63,143 | $3,557 |
| 5  | $62,693 | $3,557 |
| 10 | $58,770 | $3,589 |
| 20 | $51,954 | $3,203 |
| 30 | $46,334 | $2,596 |
| 50 | $29,790 | $2,035 |

Combined with a narrower `max_sl_points` (200/150/100) the effect compounds:
trade count drops, DD doesn't fall faster than PnL. Combining with
`ema_exit_ext_on=True` doesn't rescue it — losers still survive long enough to
hit the floor.

**Verdict:** keep `min_sl_points=0`. Useful as a generic risk cap if you want
to manually push DD down at the cost of PnL, but not a Pareto-finding tool on
this MNQ seed.

### `entry_cross_mode` ("Baseline" / "Borne proche" / "Borne opposée")

`Baseline` (= legacy v3 behavior, slow-HMA crosses `BBMC_ssl`) strictly
dominates. The other two reference lines fire earlier or later than the
baseline and trade quality drops on both PnL and DD:

| Mode | PnL | DD$ |
|------|----:|----:|
| Baseline (seed) | $63,143 | $3,557 |
| Borne proche    | $45,974 | $5,426 |
| Borne opposée   | $38,482 | $3,279 |

**Verdict:** `Baseline` is the winner — only kept the seed value.

### `ema_exit_ext_on` + `ema_exit_len`

**Always hurts DD on this MNQ seed.** Activating the EMA extension keeps
loser trades alive longer (SL rate jumps from ~50% to 53–60%). PnL stays
roughly similar, DD blows out:

| ema_exit_len | PnL | DD$ |
|-------------:|----:|----:|
| OFF (seed)   | $63,143 | $3,557 |
| 5            | $51,960 | $5,828 |
| 9            | $48,908 | $6,805 |
| 15           | $50,294 | $8,069 |
| 30           | $43,315 | $6,788 |

Even combined with `min_sl_points` (which one might think caps the surviving
losers) the DD remains far above the seed. Tested ema_exit_len ∈ {5,7,9,11,
15,20,30,50} both alone and combined with `min_sl_points ∈ {15,25,40}`.

**Verdict:** leave `ema_exit_ext_on=False` for this strategy on MNQ 7m. The
HMA→HW exit is already well-timed; deferring it via EMA just keeps drawdowns
in the trade.

## Core param re-sweep (Sweep 03)

Found three **strict Pareto** singletons:

| Change | PnL | DD$ | Δ PnL | Δ DD$ |
|--------|----:|----:|------:|------:|
| `hma_pol_bars=5` | $64,952 | $3,474 | +$1,808 | −$83 |
| `hma_pol_bars=3` | $64,006 | $3,468 | +$863 | −$89 |
| `hw_extreme=35`  | $63,192 | $3,485 | +$49 | −$72 |

And a **DD valley** at `mf_length=31`: PnL=$59,075 / DD=$2,494 (−$1,063 DD
for −$4,068 PnL). Memory confirmed — `mf_length` is non-monotone (the dip
sits between 25 and 33; rises again past 35).

## Champion stack (Sweep 04/05)

Combining `hma_pol_bars=5 + sig_extreme=60 + hw_extreme=35` produced a major
jump: **PnL=$68,107 / DD=$3,376** (+$4,964 / −$181). At this point
`sig_extreme` and `hw_extreme` have effectively saturated their filters —
testing values from 50 up to 90 only plateaus (all converge around
$66k–$68k). Disabling them entirely (`sig_extreme_on=False`,
`hw_extreme_on=False`) reproduces nearly the same result, confirming the
filters are no longer binding at these thresholds.

Three candidate variants emerged:

| Tag | Params | PnL | DD$ |
|-----|--------|----:|----:|
| A (top PnL)   | hma=5, sig=60, hw=35              | $68,107 | $3,376 |
| B (balanced)  | hma=5, sig=50, hw=30              | $67,943 | $3,165 |
| C (DD-cut)    | hma=5, sig=60, hw=35, mf=31       | $63,923 | $2,681 |

## Blackouts (Sweep 06/07)

Hour-of-day on candidate A (no extra blackouts) revealed only H06, H08, H11,
H12 as net-negative — the seed already covered the morning broadly (5–9) but
included H05 (which is positive!) and missed H13 (mostly neutral, but inside
a noisier block). Best blackout stack:

```
22:00–23:59   (close — unchanged)
 6:00–09:00   (morning — replaces 5–9)
11:00–14:00   (Euro session — extends 11–13)
14:30–15:00   (US pre-open — tightens 14–15)
```

Applied on the three candidates:

| Stack \ Candidate | A | A2 (with 11-14) | B | C |
|-------------------|----:|----:|----:|----:|
| Seed blackouts | $68,107 / $3,376 | — | $67,943 / $3,165 | $63,923 / $2,681 |
| **New stack**  | $74,911 / $3,508 | **$72,870 / $2,946** | **$71,335 / $2,761** | **$69,411 / $2,792** |

All combinations are strict Pareto improvements vs seed.

## Risk × candidate (Sweep 08/09)

Trade count is identical across risk levels — the 20-contract cap is rarely
binding, so PnL and DD scale roughly linearly with risk. The candidate that
best preserves the DD margin while ramping PnL is **TOP_C (mf_length=31 +
11–14 mid-blackout)**, which has more total trades and a steeper DD floor.

| Risk | TOP_A2 | TOP_B | **TOP_C** |
|-----:|-------:|------:|----------:|
| 0.50% | $72,870 / $2,946 | $71,335 / $2,761 | $69,411 / $2,792 |
| 0.55% | $79,522 / $3,406 | $78,090 / $3,414 | $76,262 / $3,075 |
| **0.60%** | $85,123 / $3,922 | $83,580 / $3,917 | **$80,709 / $3,236** |
| 0.625% | $89,696 / $4,067 | $88,064 / $4,086 | $84,804 / $3,391 |
| 0.65% | $93,694 / $4,097 | $92,069 / $4,116 | $89,804 / $3,574 |

DD-budget cutoff: at 0.625%, TOP_A2 and TOP_B both exceed seed DD ($3,557) on
the wrong side. TOP_C stays under up to 0.65%. **0.60% is the comfort-margin
sweet spot** — high PnL, comfortable DD cushion.

## Decision rationale (winner pick)

Three viable Pareto-strict picks at the end of the sweep:

| Candidate | PnL | DD$ | Comment |
|-----------|----:|----:|---------|
| **TOP_C @ 0.60%** | $80,709 | $3,236 | ⭐ Best balance: +28% PnL, −9% DD |
| TOP_C @ 0.625%    | $84,804 | $3,391 | Max PnL, tighter DD margin |
| TOP_C @ 0.55%     | $76,262 | $3,075 | Max DD reduction, less PnL bump |

We picked **TOP_C @ 0.60%**: it leaves a comfortable cushion on both axes
(DD margin of $321 vs the seed budget) and represents the strongest Pareto
move that doesn't push the DD to the limit. If the user wants to push for
maximum PnL, swap risk to 0.625% (still Pareto-strict, just less margin).

## Re-validation
`verify_preset.py` replays the saved preset and confirms:
```
PRESET REPLAY: PnL=$80,709 | DD=$3,236 | N=1299 | WR=48.7% | SL=50.3% | BE=1.0% | PF=1.64 | AW=$326 | AL=$-188
Expected:      PnL=$80,709 DD=$3,236 N=1299 WR=48.7% PF=1.64
✅ MATCH
```

## Memory items to update / add

1. **`feedback_v31_params_mnq`** (new): on HMASSLOsciV3 MNQ 7m, the three new
   v3.1 params (`min_sl_points`, `entry_cross_mode`, `ema_exit_ext_on`) all
   ended up disabled in the winner. `entry_cross_mode=Baseline` strictly
   dominates the two alternatives; `ema_exit_ext_on=True` worsens DD at every
   tested EMA length (5–50) by keeping losers alive longer; `min_sl_points`
   trades PnL for DD smoothly (no sweet spot).

2. **`project_hmav3_mnq_v6_winner`** (new): MNQ 7m winner config is
   hma_pol_bars=5, sig_extreme=60, hw_extreme=35, mf_length=31, risk=0.60%,
   blackouts {close, 6-9, 11-14, 14h30-15} → $80,709 / $3,236.

3. **`feedback_parameter_sweeps`** (update): also confirms `hma_pol_bars` is
   a big Pareto unlock on HMASSLOsciV3 MNQ (moving 0 → 5 alone is +$1,808
   PnL / −$83 DD).
