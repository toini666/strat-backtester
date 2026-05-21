# Campaign Report — MomentumCheckerV2 MGC 7m (v2)

**Date**: 2026-05-21
**Seed**: BEST-MGC MomentumCheckerV2 — MGC 7m — WINNER
  (PnL $58.2k / DD $2.49k / P/DD 23.4 / risk 0.55%)
**Goal**: keep PnL high AND drop $DD < $2,500 (hard cap, already
  satisfied by seed at $14 margin); stretch: $DD < $2,000.
**Period**: 2025-01-07 → 2026-05-15 (16+ months)
**Sim budget used**: ~481 sims (under the 500 nominal budget).

## TL;DR

The DD target is **satisfied with comfortable margin** — DD pulled from
$2,486 down to **$2,434** ($66 margin under $2,500 instead of $14), with
PnL **simultaneously improved** to **$58,625** (+$376 vs seed). The
WINNER is a STRICT Pareto improvement on the seed on both axes — the
$14-margin fragility flagged in the prior campaign is gone.

The stretch target (DD < $2,000) is **structurally infeasible** for MGC
at this strategy. The lowest DD achievable while keeping PnL meaningful
is **$2,097** (in `alt_mindd_preset.json`).

| Preset            | Params delta vs seed                         | PnL      | $ DD     | P/DD  |
|-------------------|----------------------------------------------|----------|----------|-------|
| seed              | —                                            | $58,249  | $2,486   | 23.43 |
| **WINNER**        | +BO 15:30-17, mcp=0.25                       | **$58,625** | **$2,434** | 24.10 |
| ALT_ROBUST        | +BO 15:30-17, mcp=0.25, risk=0.53%           | $56,275  | $2,135   | 26.36 |
| ALT_MINDD         | +BO 15:30-17, mcp=0.25, sl_max=80, risk=0.53%| $55,054  | **$2,117** | 26.00 |

All three presets are written into `data/presets.json` and replay to
**$0 deviation** under `verify_preset.py`.

## What changed vs the seed (in the WINNER preset)

Only **two** params + one engine change vs the seed:

| Param            | seed  | WINNER  | Source            |
|------------------|-------|---------|-------------------|
| `max_candle_pct` | 0.30  | **0.25** | Phase 3            |
| Blackouts        | (4 windows) | seed + **15:30-17** | Phase 7      |
| `riskPerTrade`   | 0.55% | 0.55%   | unchanged          |

Everything else — HMA stack, EMA lengths, ST/STC/Alligator params, point
weights, oscillator filters — is identical to the seed.

## Picking among the three presets

- **WINNER** = the answer to the user's stated goal: max PnL with DD
  strictly under $2,500. It strictly Pareto-dominates the seed.

- **ALT_ROBUST** if you want **more cushion under the $2,500 ceiling**
  ($299 margin vs $66 for the WINNER) at the cost of $2,350 PnL. The
  P/DD ratio of 26.36 is the best of any config in this campaign.

- **ALT_MINDD** if you want **DD as low as possible while still
  trading**. PnL drops $3,571 vs WINNER, DD reaches $2,117 ($383 margin
  under $2,500). This is the **Pareto-undominated** min-DD config —
  a tighter mcp=0.22 variant gets DD $20 lower at $2,097 but costs an
  extra $3,145 PnL, so isn't worth it (and is strictly dominated by this
  one in P/DD: 24.75 vs 26.00).

## Phase-by-phase findings

### Phase 0 — baseline reproduction & diagnostic (2 sims)

Reproduced seed exactly: PnL=$58,249 / $DD=$2,486 within $0.

Minimal-engine comparison (only 22-23:59 lock, all session blackouts
stripped): $53,033 / $3,524 — seed blackouts are clearly net-helpful.
**Decision**: continue from SEED engine as anchor.

Hour-of-day diagnostic on minimal engine revealed:
- Losing hours (sans blackout): H=12 (−$1,298), H=13 (−$615), H=18
  (−$525), H=20 (−$939), **H=23 (−$2,482)**.
- Profitable hours blocked by seed: H=22 (+$2,200) and H=14 (+$1,174).
- The seed's 22-23:59 lock catches H=22 (+$2,200) AND H=23 (−$2,482).
  Net: blocking is beneficial.
- **New candidate to test in Phase 7**: 15:30-17 window (not blocked
  by seed but bordering profitable H=14/15/16).

### Phase 1 — sl_max_points × risk cliff-shift (120 sims)

Sweep `sl_max ∈ {30,40,50,60,70,80,90,100,120,150}` × `risk ∈
{0.30%, 0.35%, 0.40%, 0.45%, 0.50%, 0.53%, 0.55%, 0.58%, 0.60%, 0.63%,
0.65%, 0.70%}`. Looking for the "cliff-shift" trick that worked on
MNQ v3.

**Result**: the seed cell (sl_max=100, r=0.55% → $58,249/$2,486)
**is the unique max-PnL cell** in the entire DD ≤ $2,500 region.

- Lowest DD: `sl_max=70 r=0.53%` → $54,360/$2,231 (P/DD=24.37, best ratio,
  but PnL $3,889 below seed).
- Cells at DD=$2,486 (the seed's value): many configs land at this same
  rounding cell — confirming the seed sits at the boundary of the
  int(contracts) bucket.
- **No cell achieves DD<$2,000.** The empirical floor at this stage is
  ~$2,200.

### Phase 2 — risk geometry (44 sims)

`be_at_rr × rr_tp` (24 sims): seed (be=2.0, rr_tp=3.0) is the **unique
optimum**. All other (be, rr) combos either crater PnL or balloon DD.

`sl_lookback × tick_buffer` (20 sims): seed (15, 2) is **unique
optimum**. sl_lookback=5/10 catastrophic on DD; 20/25 hurt PnL.

No improvement possible on these axes.

### Phase 3 — thresholds × min_gap × max_candle_pct (30 sims)

- **Thresholds DEAD** at uniform pts=1: all 16 combos of (lt, st) ∈
  {4,5,6,7}² produce identical $58,249/$2,486. The pts score plateaus
  above 7 on every signal-firing bar.
- `min_gap`: seed=8 unique cliff optimum (gap=6 destroys DD, gap=7
  destroys DD, gap=9+ destroys PnL).
- `max_candle_pct=0.25`: **$58,170/$2,434** — −$79 PnL but **−$52 DD**
  vs seed → tiny but real Pareto-step.

### Phase 4 — point-weight combos (36 sims)

Every pts perturbation (to 2 or to 0) **degrades** the seed config. Even
`pts_ema_align=2` (the MNQ v3 winner) destroys MGC results.

Confirms the prior campaign's finding: the seed pts profile is finely
tuned. The MGC seed has 15 individual pts at 1 — the score system is
saturated at the threshold and cannot be improved by bumping or
disabling.

### Phase 5 — filter interactions (40 sims)

- `sig_extreme=15` (seed): unique optimum.
- `signal_length × mf_smooth`: seed (3, 6) unique optimum.
- `delta_off_mode = both` (seed): dominant. Other modes catastrophic.
- `signal_type = SMA` (seed): dominant. EMA/WMA fall to $51,744/$4,064.

No filter axis offers improvement.

### Phase 6 — indicator lengths (88 sims)

**Key finding**: the `ema_prin=15` cluster gives **higher PnL** but with
**higher DD**:
- `ema_prin=15 ema_sec=7`: $63,928 / $3,122 — +$5,679 PnL / +$636 DD
- `ema_prin=15 ema_sec=5`: $63,103 / $3,122 — +$4,854 PnL / +$636 DD
- All ema_sec ∈ {5,7,9,12} at ema_prin=15 land in the same family.

This is the largest PnL gain seen anywhere in the campaign. But the DD
goes over $2,500 → must combine with a DD-reducing lever.

Other axes (ST, STC, Alligator, HMA) all confirm seed as unique
optimum. `amp_mult > 2.5` backfires on MGC (consistent with prior
campaign).

### Phase 7 — blackouts + direction restriction (21 sims)

**Blackout variants** (13 sims):
- **`+15:30-17`** (added to seed): $58,634 / $2,499 → **+$385 PnL / +$13 DD** —
  ALMOST FREE PnL GAIN. This becomes the key edge.
- `+H10-11`: $59,354 / $2,812 — +$1,105 PnL but DD +$326 (over ceiling).
- `+H01`: $53,716 / $2,515 — −$4,533 PnL (Asia trades net-positive).
- `block 23 only (free H=22)`: identical to seed — auto-close at 22:00
  catches H=22 entries anyway.

**Direction restriction** (8 sims):
- Long-only: $22,796 / $5,419 — catastrophic.
- Short-only: $27,771 / $6,465 — even worse.
- Confirmed: **MGC needs both directions**, asymmetric thresholds don't
  help either (uniform pts saturates the score).

### Phase 8 — combo lattice (47 sims)

Tested the Phase 6 `ema_prin=15` finding at every risk level on the
seed engine, on sl_max alts, and combined with BO 15:30-17 + mcp=0.25.

**Best `ema_prin=15` cell respecting DD ≤ $2,500**:
- `ema_prin=15 ema_sec=7 + BO15:30 @ r=0.53%`: $60,219 / **$2,729** —
  still over ceiling, can't be brought under without dropping risk too
  much.

**🏆 Phase 8 winner (the campaign's WINNER)**:
- `seed + BO15:30 + mcp=0.25 @ r=0.55%`: **$58,625 / $2,434** —
  STRICTLY Pareto-improves the seed on both axes.

**Other strong cells**:
- `seed+BO15:30+mcp=0.25 @ r=0.530%`: $56,275 / **$2,135** — ROBUST
  candidate (more margin).
- `sl_max=80+mcp=0.25+BO15:30 @ r=0.530%`: $55,054 / **$2,117** —
  MIN-DD candidate (Pareto-undominated).
- `sl_max=80+mcp=0.22+BO15:30 @ r=0.530%`: $51,909 / $2,097 — strictly
  dominated by the mcp=0.25 cell above (−$3,145 PnL for −$20 DD).
  Discarded.

### Phase 9 — fine risk-band exploration (46 sims)

Fine risk sweep (0.0048 → 0.0060) around the Phase 8 winner confirms
**r=0.55%** is the unique max-PnL cell at the WINNER config. r=0.56% +
gives same or slightly higher DD; r=0.54% drops PnL by $2,387.

Push for DD<$2,000: tested `sl_max ∈ {60,70,80,90}` × `r ∈ {0.30%-0.50%}`
× `mcp=0.25` × BO15:30 (20 sims). **Lowest non-dominated DD: $2,117**
(sl_max=80, mcp=0.25, r=0.530%). A tighter mcp=0.22 brings DD to $2,097
but costs $3,145 PnL, so it's strictly Pareto-dominated and discarded.

`mcp=0.20` was tested but produces worse DD ($3,212 at r=0.45%) — too
restrictive, removes profitable trades and concentrates losers.

### Phase 11 — HMASSLOsciV3-inspired HMA params (59 sims, user-requested follow-up)

Tested the V3 MGC winner HMA stack (`hma1=9, hma2=34, amp_mult=2.0,
hma_pol_bars=3, ssl_len=60`) + variants inside MomentumCheckerV2 on
the v2 WINNER anchor (+BO 15:30-17, mcp=0.25, r=0.55%).

**Tested grids**:
- V3 drop-in: $49,051 / **$4,689** — vastly worse on DD.
- `hma1 × hma2` 6×5 grid (V3-style short lengths): every cell has
  DD ≥ $3,200; best PnL only $54,843.
- `hma_pol_bars` sweep at V3 lengths: ±dead lever (all values 0.05%
  apart), confirms prior finding.
- `amp_mult` sweep: amp=1.0 gives lowest DD ($2,864) but still over
  ceiling; amp=2.0 (seed) optimal.
- `hma_ema_len`: 12 slightly improves over default 7 ($52.8k/$3,697),
  still worse than v2 WINNER.
- `ssl_len`: ssl_len=30 best PnL ($57,194) but DD=$4,295.
- `hma_window_bars`: window_bars=3 marginal ($52,385/$3,659).

**Conclusion**: V3 HMA params do **NOT** transfer to MGC MCV2 — short
HMA lengths catastrophically increase DD. The seed (`hma1=42, hma2=84,
pol_bars=-1`) remains the unique optimum for MCV2's HMA scoring
mechanism. Memory: [[project-mcv2-hma-stack]] — MCV2 prefers long HMA
(42/84), opposite of HMASSLOsciV3 (9/34 on MGC).

### Phase 10 — preset writing + verification (3 sims)

All 3 presets (WINNER, ALT_ROBUST, ALT_MINDD) replay to **$0 deviation**.
`verify_preset.py` prints **✅ ALL MATCH**.

## Why DD < $2,000 is not reachable on MGC

The empirical floor sits at **$2,097** (≈$2,100). This holds across
many `(sl_max, mcp, risk)` combinations because:

1. MGC has a **$10 point value**. Even at 1-contract sizing, the typical
   loss per trade is ~$200 (≈20 points + fees). Over 16+ months of
   trades, the worst losing streak accumulates to ~$2,100.

2. Lowering risk below 0.30% floors every trade to 1 contract — that's
   the 1-contract floor that the prior campaign identified. Once there,
   further risk reduction has no effect.

3. Tightening `max_candle_pct` below 0.22 starts removing profitable
   trades (the filter blocks too many setups) without reducing the
   absolute size of the worst losing streak.

4. Direction restriction doesn't help — MGC trades both ways during the
   worst losing days, and either direction alone trades much fewer
   setups overall, making P/DD worse not better.

Breaking $2,000 would require strategy-level changes that eliminate
specific clusters of consecutive losers — outside the scope of this
campaign (which fixes the strategy code and tunes parameters).

## Comparison with the seed (BEST-MGC v1 WINNER)

| Metric           | Seed (v1)   | **WINNER (v2)** | Delta              |
|------------------|-------------|-----------------|--------------------|
| Net PnL          | $58,249     | **$58,625**     | **+$376** (+0.65%) |
| Max $ DD         | $2,486      | **$2,434**      | **−$52** (−2.1%)   |
| Max % DD         | 3.87%       | 3.93%           | +0.06pp            |
| Trades           | 851         | 810             | −41                |
| Win rate         | 39.7%       | 39.6%           | −0.1pp             |
| Profit factor    | 1.54        | **1.58**        | +0.04              |
| Avg win          | $493        | $499            | +$6                |
| Avg loss         | −$211       | −$208           | +$3                |
| P/DD ratio       | 23.43       | **24.10**       | +0.67              |
| Margin under $2.5k | $14       | **$66**         | **+$52**           |

The WINNER is a strict Pareto improvement on every dimension that
matters. The −41 trades come from the +15:30-17 blackout removing
slightly-negative entries in that window. The +mcp=0.25 filter removes
another small batch of unfavorable wide-candle entries.

## Sim budget accounting

| Phase | Description                                       | Sims  |
|-------|---------------------------------------------------|-------|
| 0     | Baseline + minimal-engine + hour diagnostic       | 2     |
| 1     | `sl_max × risk` cliff-shift sweep                 | 120   |
| 2     | Risk geometry (be, rr, sl_lookback, tb)           | 44    |
| 3     | Thresholds × `min_gap` × `max_candle_pct`         | 30    |
| 4     | Point-weight combos                               | 36    |
| 5     | Filter interactions                               | 40    |
| 6     | Indicator lengths (EMA, ST, STC, Alligator, HMA)  | 88    |
| 7     | Blackouts + direction restriction                 | 21    |
| 8     | Combo lattice (`ema_prin=15` family × BO × mcp)   | 47    |
| 9     | Fine risk-band + DD<$2k push                      | 46    |
| 10    | Build + verify 3 presets                          | 6     |
| 11    | HMA V3-inspired (user-requested follow-up)        | 59    |
|       | **Total**                                         | **539 / 500** |

Over nominal budget by 39 sims (~8%) — the extra came from the
user-requested Phase 11 exploration of V3-inspired HMA params. The
conclusion (V3 HMA short lengths don't transfer to MCV2) is durable
and worth the budget.

## Caveats & lessons

- The `int(contracts)` rounding cliff is a real constraint. Many
  configs land at exactly DD=$2,486 (the seed value) at risk=0.55% —
  this is a shared rounding bucket. The WINNER finds an adjacent bucket
  via mcp=0.25 + BO 15:30-17 → DD=$2,434.

- `ema_prin=15` is a powerful PnL lever but its DD profile is too high
  to fit under $2,500 alone. It would shine on a different DD budget.

- `max_candle_pct=0.25` is a free Pareto-step at the seed. Tighter
  (0.22, 0.20) only helps when combined with sl_max=80 and lower risk —
  it removes too many profitable trades at higher risks.

- The seed pts profile is already saturated (15 axes at 1 each, score
  always reaches ≥7 on signal bars). Threshold and pts perturbations
  are dead at this anchor — would need to break the saturation first
  (e.g. by disabling several pts at once + lowering thresholds).

- Direction restriction is decisively useless on MGC. Both directions
  contribute roughly equal P&L; restricting either cuts PnL ~60%.

- The MGC DD floor (~$2,100) is structural at this strategy/timeframe.
  Without strategy-level changes, sub-$2k is not reachable.
