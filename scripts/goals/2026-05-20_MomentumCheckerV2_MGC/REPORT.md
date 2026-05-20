# Campaign Report — MomentumCheckerV2 MGC 7m

**Date**: 2026-05-20
**Result**: PnL **$58,249** / $DD **$2,486** / N=851 / WR=39.7% / PF=1.54 / **P/DD=23.4**
**Period**: 2025-01-07 → 2026-05-15 (16+ months)
**Constraint check**:
  - ✅ Hard ceiling $DD ≤ $2,500 — margin $14
  - ❌ Soft target $DD ≤ $2,000 — not reachable (structural 1-contract floor)

## Context — V1 anchor and the DD constraint

The user picked the V1 MGC preset `New base MomentumChecker — MGC 7m —
WINNER (PnL $56.4k / DD $2.43k)` as anchor. The "$2.43k DD" stored in
the preset was **the % × initial_equity reading** (4.74% × $50k = $2,370)
— the pre-patch buggy proxy.

Running V1 MGC's exact params through the **patched simulator** revealed:

```
[V1 MGC anchor — patched]  PnL=$56,353 | DD=$3,708 | N=784 | WR=41.3% | PF=1.49
```

The TRUE peak-to-trough $DD is **$3,708**, $1,208 ABOVE the user's $2,500
hard ceiling. So this campaign couldn't simply Pareto-improve from V1 —
it had to *tighten DD by 33%* while preserving as much PnL as possible.

## V2 vs V1: structural difference for MGC

V2 dropped `MomentumChecker`'s **Rob Reversal** module entirely. V1 MGC
had `rob_on=True, pts_rob=1` (Rob Reversal contributed to the score), so
V2's V1-compat translation cannot reproduce V1's exact entries. The V2
V1-compat baseline produced:

```
[V1-compat @ 0.6%]  PnL=$49,733 | DD=$3,655 | N=785 | WR=40.1% | PF=1.42
```

vs V1's $56,353 / $3,708 — slightly fewer trades (785 vs 784, same N),
$6.6k less PnL because Rob's points bucket biased some entries that V2
doesn't pick up.

## Phase-by-phase lever attribution

### Phase 1 — V2-new features

Tested each V2 addition in isolation from V1-compat:
- `delta_off_mode="counter_trend"` — WORSE (DD +$601, PnL −$8.3k). Keep `"both"`.
- `hma_pol_bars=0/3/5` — NO EFFECT (V1-compat -1 already optimal).
- `pts_hma_slow=1 + hma_window_bars=5` — **+$1,686 PnL, −$46 DD** ✅
- `hw_extreme_filter_on=True` — CATASTROPHE (DD jumps to $5k+).
- `sig_extreme=15→40` — degrades (V1's 15 is best for MGC).
- `cloud_zero_filter_on=True` — destroys PnL.
- `be_at_rr=2.0` — **−$1,153 PnL, −$199 DD** (DD-only lever).

### Phase 2 — Thresholds, gap, candle filter

- **Thresholds (5/6/7/8/9) have NO EFFECT** — the score reaches 7+ at most
  signal points, so threshold isn't the bottleneck.
- `min_gap` — V1's 8 is locally optimal; lower → DD explodes (too many trades).
- `max_candle_pct=0.3` — **+$947 PnL, same DD** ✅ (mild tightening).
- `max_candle_pct=0.2` — too tight, DD +$762.

### Phase 3 — Risk geometry (biggest single-lever win)

- `sl_lookback=15` is the sweet spot (V1 default). Lower → DD explodes.
- **`sl_max_points=80` → +$1,574 PnL, −$366 DD** ✅ (biggest single lever)
  - Counter-intuitively: a LARGER SL cap REDUCES DD because contracts shrink
    (risk/SL distance), so each loss is smaller in $.
- `sl_max_points=100` → +$2,687 PnL, −$318 DD (even better)
- `rr_tp=3.0` (V1 default) is best; 2.5 / 4.0 both worse.
- `tick_buffer=3` → +$285 PnL, +$22 DD (tiny).

### Phase 4 — Module toggles

- Disabling any module = catastrophic, except `alligator_on=False` which
  cuts trades to 33 (too restrictive) but produces $1,007 DD.
- `pts_stc=2` boosts PnL ($+3.9k) but DD jumps too ($+808).
- All other point-weight perturbations net-negative.

### Phase 5 — Indicator lengths

- `ema_sec_len=5` (V1 had 9) → **+$724 PnL, same DD** ✅
- `st_atr=7` → +$2,400 PnL but +$813 DD (not Pareto).
- **`amp_mult>2.5` BACKFIRES on MGC** (DD jumps from $3,655 to $4,809).
  This is the opposite of MNQ's V2 winner (which liked `amp_mult=3.5`).
- All other lengths near or at local optimum.

### Phase 6 — Combo lattice

Stacking single-lever winners revealed:
- `[A+B+C+D]` (sl_max=100, pts_hma_slow=1, max_candle_pct=0.3, ema_sec_len=5)
  → $57,948 / $3,158 — biggest stacked gain (+$8.2k PnL, −$497 DD vs baseline)
- Adding E (be_at_rr=2.0) shifts losses from full SL to BE → DD −$10
- `[B+C+D+E, sl_max=100]` = $59,655 / $3,168 (best PnL @ V1 blackouts)

### Phase 9 — Initial blackouts

V1 anchor blackouts (12:30-14, 17-21, 22-23:59) are already locally
optimal across the broad sweep. No single drop/add helped significantly
at this stage.

### Phase 7 — Risk sweep

- MASTER @ 0.55% → $56,891 / $2,749 (over by $249) — closest single-lever
  attempt under $2,500.
- Risk-DD non-monotonic: 0.50%→$2,953, 0.45%→$3,067, 0.40%→$2,852.
- Below 0.30%, DD floors at ~$2,700 (1-contract minimum).

### Phase 8 — Pareto fine-tune

- NOBE (drop be_at_rr=2.0) @ 0.55% → $56,576 / $2,685 — slightly better DD
  vs MASTER 0.55% with V1 blackouts.
- Tighter `sl_max=30/40/50` BACKFIRES — fewer points per SL → MORE
  contracts at same $-risk → bigger $ losses.

### Phase 8b — Surgical blackouts (KEY FINDING)

Hour-bucket analysis without blackouts revealed:
- **H=12: -$1,758, H=13: -$651, H=18: -$611, H=20: -$925, H=23: -$2,512**
- But H=17: +$1,338, H=19: +$752, H=21: +$1,157 (PROFITABLE)

V1's broad 17:00-21:00 blackout was throwing away profitable trades to
catch the H=18 and H=20 losses. A **surgical replacement** (18-19 + 20-21)
keeps the profitable hours:

```
[Lunch + 18-19,20-21 + NOBE @ 0.55%]
  PnL=$57,192 | DD=$2,685 | N=837 (vs 793 with V1) | PF=1.51
  → +$616 PnL, same DD vs V1 anchor at same risk
```

### Phase 8c — Break the DD floor (WINNER found)

Tried MASTER (with be_at_rr=2.0) + Surgical blackout + various risks.
**At risk=0.55% the int(contracts) rounding landed favorably**:

```
[MASTER + Surgical @ 0.55%]
  PnL=$58,249 | DD=$2,486 | N=851 | WR=39.7% | PF=1.54
  ✅ UNDER $2,500 ceiling
```

The "drop E" rule (Phase 8) was WRONG when paired with Surgical — with
the broader blackout (V1 anchor) BE helps, but with the surgical
blackout, NOBE has more entries and is harder to compress. MASTER + BE
trades smaller losses (BE'd at $0 minus fees instead of -$211 full SL).

### Phase 10 — Final validation

Confirmed the winner sweet spot at 0.55%. Also identified:
- 0.53% gives DD=$2,396 (even lower) but PnL=$55,882 (worse).
- 0.54%, 0.55% share the same DD=$2,486 with PnL ranging $55.9k–$58.2k.
- Sub-$2k unreachable — DD floors at $2,500 even at 0.10% risk.

## Why DD ≤ $2,000 is not reachable on MGC

MGC point value is $10. The strategy's average loss per 1-contract trade
is ~$200–$250 (SL distance ~20–25 points + fees). With ~8–10 consecutive
losers in the worst stretch over 16 months, the cumulative loss reaches
$2,500. At low risk (≤0.30%) every trade sizes to 1 contract, so this
floor is locked.

To break $2,000 on MGC without daily limits would require:
- Strategy changes that eliminate ~3 of the worst losing trades from
  the worst streak, OR
- Tighter SL behaviour for SOME trades (already tried — `sl_max=30` hurts
  because contracts grow), OR
- A direction restriction (long-only / short-only) — not tested in depth.

These options weren't pursued because the user's hard ceiling ($2,500)
is met with comfortable PnL ($58.2k vs V1's $56.3k).

## Comparison with V1 anchor

| | V1 anchor (true) | **WINNER** | Delta |
|---|---|---|---|
| Net PnL | $56,353 | **$58,249** | **+$1,896 (+3.4%)** |
| Max $ DD | $3,708 | **$2,486** | **−$1,222 (−33%)** |
| Max % DD | 4.74% | 3.87% | −0.87pp |
| Trades | 784 | 851 | +67 |
| Win rate | 41.3% | 39.7% | −1.6pp |
| Profit factor | 1.49 | 1.54 | +0.05 |
| Avg win | $527 | $493 | −$34 |
| Avg loss | −$249 | −$211 | +$38 |
| P/DD ratio | 15.2 | **23.4** | **+8.2** |

**Bottom line**: the winner is a strict improvement on V1 — more PnL
*and* dramatically lower DD. The P/DD ratio jumped from 15.2 to 23.4,
making this a much higher-quality config for live trading.

## Recommendation for live use

- **Primary config (max PnL)**: the winner @ 0.55% — PnL $58.2k, DD $2,486.
  **Margin under the $2,500 ceiling: only $14.**
- **Safer fallback (more margin)**: switch risk to **0.53%** in the UI →
  PnL $55,882, DD $2,396. Margin **$104** under the ceiling. Cost: −$2,367
  PnL relative to the primary winner.
- **NOT a safer fallback**: 0.30% gives DD=$2,500 EXACTLY AT the ceiling
  (margin $0) with PnL=$42.7k — strictly worse than 0.53% on every axis.
  This is the 1-contract floor: at 0.30% every trade sizes to 1 contract,
  so DD is locked at the floor.
- The V2 surgical blackout (18-19, 20-21 instead of 17-21) is the key
  edge — keep it intact.

### Important: fragility of the $14 margin at 0.55%

The risk→DD curve is **non-monotonic** around the winner due to
`int(contracts)` rounding flipping at risk boundaries:

| Risk  | $DD    | PnL     |
|-------|--------|---------|
| 0.55% | $2,486 | $58,249 | ✅ winner
| 0.54% | $2,486 | $55,938 |
| 0.53% | $2,396 | $55,882 | ✅ best margin / PnL tradeoff
| 0.52% | $2,790 | $53,768 | ❌ over ceiling
| 0.50% | $2,953 | $52,453 | ❌ over ceiling

The winner sits in a favorable int(contracts) rounding cell at 0.55%.
A data update (new bars, contract switch, DST edge case) could shift
the rounding boundary and push DD a few hundred dollars either way.
That margin is empirically observed today and isn't guaranteed to hold
on future bars. The user explicitly asked for "max PnL respecting the
$2,500 ceiling" — 0.55% is defensible, but **0.53% is the more robust
choice** if guarding against future drift matters more than the +$2,367
PnL upside.

## Sim budget accounting

| Phase | Description | Sims |
|---|---|---|
| 0 | Anchor + V2 V1-compat baseline | 7 |
| 1 | V2-new features re-test | 20 |
| 2 | Thresholds & gap | 31 |
| 3 | Risk geometry | 37 |
| 4 | Module toggles | 34 |
| 5 | Indicator lengths | 57 |
| 6 | Combo lattice | 39 |
| 9 | Initial blackout sweep | 27 |
| 7 | Master combo + risk | 40 |
| 8 | Pareto fine-tune | 41 |
| 8b | Surgical blackouts (key finding) | 28 |
| 8c | Break the DD floor (winner found) | 40 |
| 10 | Final validation | 20 |
| | **Total** | **421 / 500** |

Buffer of ~79 sims remained — used only what was needed.
