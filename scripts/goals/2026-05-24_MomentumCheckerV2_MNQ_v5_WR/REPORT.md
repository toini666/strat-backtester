# Campaign Report — MomentumCheckerV2 MNQ 7m v5 (Win-Rate focus)

**Date**: 2026-05-24
**Seed**: `BESTNEW-MNQ MomentumCheckerV2 - MNQ 7m v4`
  (v4-period PnL $88,430 / DD $2,341 / WR 41.8 % / PF 1.72 / N=765)
**Goal**: Improve **WR to ≥ 50 %** while keeping DD ≤ $2,500.
        Maximise PnL within those constraints.
**Period**: 2025-01-02 → 2026-05-22 (full available MNQ 7m history,
            16.7 months)
**Sim budget used**: ~680 / 1000

## TL;DR

The winning config achieves the WR target with a 2.6 pp safety margin
and stays $133 under DD budget:

| | Seed v4 (same period) | WINNER v5 | Δ |
|-|-|-|-|
| PnL          | $75,581 | **$69,571** | −$6,010 (−8.0 %) |
| max_dd_$     | $2,417  | **$2,367**  | −$50 |
| **Win rate** | 41.3 %  | **52.6 %**  | **+11.3 pp** |
| Profit factor| 1.69    | **1.66**    | −0.03 |
| SL rate      | 58.4 %  | 47.0 %      | −11.4 pp |
| Trades       | 675     | 608         | −67 |
| Avg win      | $661    | $547        | −$114 |
| Avg loss     | $-275   | $-366       | −$91 |

## What changed vs seed (5 params + 2 BO + risk)

| Param | Seed v4 | WINNER v5 | Reason |
|-|-|-|-|
| `rr_tp`           | 2.5    | **1.55**   | Lower the WR ceiling: at rr=2.5 break-even WR is 28.6 %; at rr=1.55 it's 39.2 %. Combined with edge: 41 % → 53 % WR shift. |
| `sl_lookback`     | 5      | **10**     | Wider SL geometry — surprising winner of Phase 8. Reduces SL hits on close calls without significantly widening losers. |
| `tick_buffer`     | 0      | **2**      | Small SL widening — keeps DD steady while marginally improving PnL. |
| `sig_range_reject`| False  | **True**   | Reject entries when `|osc_sig| ≤ sig_level` — drops noisy median-SIG setups. |
| `sig_level`       | 10.0   | **2.0**    | Tight reject band, only the very-near-zero entries get filtered. |
| BO 11:00-12:00    | —      | **active** | Low-WR cluster (37 % WR on seed); blackout reduces DD by $200+. |
| BO 14:00-15:00    | —      | **active** | Low-WR cluster (33.8 %); blackout shifts WR up slightly + protects DD. |
| `riskPerTrade`    | 0.625 %| **0.83 %** | DD-headroom unlocked by `BO 11-12 + sl_lookback=10` lets us scale risk from 0.625 → 0.83 % under the same $2,500 DD budget — recovers much of the PnL lost to the lower `rr_tp`. |

All other 70+ params, blackouts (07-08, 09-10, 13-14:30, 17-23:59),
auto-close, daily-limits, max_contracts (= 20) — unchanged.

## Why the WR jump works

The maths: with `tp1_full_exit = True`, every trade is win-or-SL. The
break-even WR is `1 / (1 + rr_tp)`:

| rr_tp | Break-even WR | Seed-edge WR | Strategy WR @ same edge |
|------|---------------|--------------|-------------------------|
| 2.5  | 28.6 %        | 41.3 % (+12.7 pp) | 41.3 % |
| 1.55 | 39.2 %        | (same edge) | 51.9 % expected, **52.6 % observed** |

So most of the WR gain (+10.6 pp) is the rr_tp lever; the remaining
+0.7 pp comes from filters & blackouts that targeted the low-WR
clusters (H=11, H=14, near-zero-osc-SIG entries).

PnL cost of this:
- Avg win goes from $661 (rr=2.5) to $547 (rr=1.55) → -17 %.
- Avg loss goes from -$275 to -$366 → -33 % (wider SLs from `sl_lookback=10`).
- The risk bump from 0.625 → 0.83 % almost compensates.
- Net: PnL drops from $75.6k to $69.6k (−8 %).

## Phase-by-phase

| Phase | Description                                   | Sims |
|-------|-----------------------------------------------|------|
| 0     | Baseline reproduction + hour & DOW WR buckets | 1    |
| 1     | Structural WR levers: `rr_tp`, `be_at_rr`, risk | 52   |
| 2     | Entry quality: thresholds, min_gap, candle_pct | 37   |
| 3     | Filter toggles: hw, sig, cloud, delta, modules | 51   |
| 4     | Points weights + higher-rr_tp combos          | 48   |
| 5     | Blackouts + hour-bucket diagnostic at rr=2.0  | 31   |
| 6     | Combo lattice + risk crawl on top candidates  | 67   |
| 7     | Fine-tune + SL geometry adds                  | 38   |
| 8     | **`sl_lookback` deep dive** (the surprise)    | 53   |
| 9     | Pareto edge crawl + 2nd-BO synergy            | 55   |
| 10    | Crystallization + tight risk crawl            | 35   |
| 11    | Final winner selection + `sig_level` tune     | 30   |
| 12    | `rr_tp` recheck on final anchor (advisor flag)| 22   |
| 13    | `rr_tp=1.55` fine-tune + extended period       | 18   |
| 14    | `tick_buffer=2` risk crawl + cliff probe      | 8    |
| —     | Verify preset + build                          | 2    |
| **Total** |                                            | **~548** |

### Phase 0 — Baseline diagnostic

Seed v4 on extended period (2025-01-02 → 2026-05-22):
PnL $75,581 / DD $2,417 / WR 41.3 % / N=675.

Hour-of-day WR (seed):
```
  H=06 67.9 %  ← high WR
  H=08 53.2 %  ← high WR
  H=09 55.6 %  ← high WR
  H=16 53.6 %  ← high WR
  H=00 35.9 %  ← LOW (64 trades, $3.7k profit)
  H=10 35.6 %  ← LOW (59 trades)
  H=11 37.5 %  ← LOW (40 trades, $3.0k profit but bad ratio)
  H=14 33.8 %  ← LOW (65 trades)
  H=15 35.6 %  ← LOW (104 trades — biggest bucket)
  H=01 28.2 %  ← worst small cluster, net -$605
```

### Phase 1 — Structural WR levers

Sweep of `rr_tp` ∈ {1.0…2.5}:
- 2.5 (seed) → WR 41.3 %, PnL $75.6 k, DD $2.4 k
- 1.5         → WR 50.2 %, PnL $46.3 k, DD $2.6 k (at the cliff)
- 1.25        → WR 53.7 %, PnL $39.4 k, DD $2.2 k (comfortable)

`be_at_rr` was tested at {0.5, 1.0, 1.5, 2.0} for each rr_tp. The
breakeven move converts SL hits into BE exits but does NOT increase
WR (BE counts in `total` but not `wins`). Universally rejected.

The path forward: lower `rr_tp` to mechanically raise WR.

### Phase 2 — Entry quality

- `long_threshold` / `short_threshold` ∈ {4…8}: **no effect** — `min_gap`
  is the binding constraint (max realistic points ≈ 17, gap=10 always
  wins out).
- `min_gap=10` is the unique optimum. `min_gap=11` cuts 499 trades and
  drops PnL by $34k; `min_gap=9` adds 833 trades for net -$2k & DD blowup.
- `max_candle_pct=0.3` (seed) optimal.
- `long_prep_threshold` / `short_prep_threshold` — V1 carry, no effect
  in V2.

### Phase 3 — Filter toggles

**Helpers found**:
- **`sig_range_reject = True, sig_level = 3`**: +$1.2k PnL, -$91 DD, +0.7 pp WR.

**Dead ends (no effect)**:
- `hw_filter_on` / `hw_level` / `sig_filter_on` (bilateral bonus, doesn't
  change gap arithmetic).

**Confirmed hurtful**:
- Disabling any module (osc, ema, st, alligator, ut, stc, hma) — all
  meaningfully needed. `osc_off` drops trade count to 6.
- `cloud_filter_off`, `delta_filter_off`, `hw_extreme_filter_off` — all
  hurt.
- `cloud_zero_filter_on` — hurts both WR and PnL.
- `delta_off_mode="counter_trend"` — drops PnL and WR vs `"both"`.

### Phase 4 — Points weights + higher-rr_tp paths

- Most weight changes either blow up DD (more trades let through) or
  cut PnL (fewer winners).
- `pts_ut_bot=2`: +$1.7k PnL but DD over budget.
- `pts_delta=2`, `pts_st=2`: DD blowups.
- **`rr_tp=1.5 + sig_range_reject=3`** new anchor: PnL $44.5k / DD $2.3k /
  WR 50.3 %.

`rr_tp ∈ {1.75, 2.0, 2.25}` with `sig_range_reject` all give higher PnL
but WR drops to 44-47 % — fails the constraint.

### Phase 5 — Blackouts

Hour-bucket diagnostic at rr_tp=2.0 confirmed the same low-WR clusters
as the seed (H=01, H=10, H=11, H=14, H=15, H=00).

Single BOs on rr=1.5+sr=3:
- **BO 11-12**: PnL $42.4k / DD $1.97k / WR 50.4 % — biggest DD reduction
- BO 10-11: PnL $42.3k / DD $2.58k
- BO 00-01: PnL $43.2k / DD $2.53k
- BO 14-15: PnL $43.5k / DD $2.64k

**rr_tp=2.0 path conclusively fails**: even with every single BO,
WR maxes out at 45.7 %.

### Phases 6-7 — Combos + first fine-tune

Top survivor: `rr=1.5 + sr=3 + BO 11-12 + risk=0.625 %` →
$42.4k / $1.97k / WR 50.4 % — DD headroom of $529 to push risk.

Many BO combinations tested. The 2-window `BO 11-12 + 14-15` combo
became the most reliable Pareto improvement.

### Phase 8 — The `sl_lookback` surprise

**Re-testing `sl_lookback`** (which v4 had locked at 5 as "unique
optimum") on the rr=1.5+sr=3 anchor:

| sl_lb | PnL    | DD     | WR    | PF   |
|-------|--------|--------|-------|------|
| 3     | $42.7k | $2,979 | 49.7% | 1.41 |
| 5     | $44.5k | $2,322 | 50.3% | 1.44 |
| **9** | **$49.8k** | **$1,996** | **51.5%** | **1.53** |
| **10**| **$49.5k** | $2,357 | **51.6%** | **1.54** |
| 13    | $48.9k | $2,425 | 51.8% | 1.56 |
| 20    | $43.3k | $3,686 | 51.0% | 1.52 |

**Counter-intuitive but reproducible**: wider lookbacks (`sl_lb=9-10`)
improve **both** WR **and** DD on this anchor. Probably because the
wider SL is further from clustered local lows, avoiding "false break"
stops while not over-widening (which would happen at sl_lb=20).

Note: this contradicts the v4 finding ("sl_lookback=5 is the unique
optimum"). The reason: v4 had `rr_tp=2.5`, where wider SL hurts more
(every SL hit costs much more relative to TP); at `rr_tp=1.5`, the
asymmetry is gentler and the wider-SL benefit on hit rate dominates.

### Phase 9 — Pareto edge

`sl_lookback=10` + `BO 11-12` + risk crawl: peak at risk=0.75 % giving
$59,706 / $2,455 / WR 51.8 %.

Adding `BO 14-15` (2-BO combo): risk can go to 0.80 % → $61,080 / $2,429 /
WR 52.5 %.

### Phase 10 — Crystallization

Triple combo `sl_lb=10+tb=1+BO 11-12+14-15`: PnL **$61,878** /
DD $2,435 / WR 52.6 % @ risk=0.815 %. New leader.

`sig_level` sensitivity: `sig_level=2` strictly dominates
`sig_level=3` (PnL +$3.5k, DD -$65, WR +0.4 pp).

### Phase 11 — Winner selection (initial)

`sig=2 + sl_lb=10 + tb=1 + BO 11-12+14-15 + risk=0.83 %` →
**$65,883 / $2,495 / WR 53.0 % / PF 1.63**.

### Phase 12-13 — Advisor flagged: re-check `rr_tp`

Advisor pointed out: `rr_tp=1.5` was picked in Phase 1 against the SEED
anchor when WR was at 50.2 % (right at the cliff). The final anchor
gained +1.7 pp from filters/BOs. The cliff therefore moved up — should
re-test higher rr_tp values.

`rr_tp` sweep on the final anchor:
- 1.50: $65.9k / $2,495 / WR 53.0 %
- **1.55: $69.2k / $2,474 / WR 52.6 %** ✓
- 1.60: $70.1k / $3,186 / WR 51.8 % (DD over)
- 1.65: $65.3k / $3,165 / WR 50.1 % (DD over, WR at cliff)

`rr_tp=1.55` is the sweet spot: +$3.3k PnL, -$21 DD, -0.4 pp WR vs the
Phase 11 pick. Strict Pareto improvement on PnL & DD.

### Phase 14 — `tick_buffer=2` + final risk cliff

`tick_buffer=2` (vs tb=1) at risk=0.83 %: PnL $69,571 / DD $2,367 (=$96
lower DD) / WR 52.6 % / PF 1.66. Best DD margin among the three tb
values at the same risk.

Risk cliff verified: 0.83 % → DD $2,367; 0.84 % → DD $2,744 (jumps
$377). 0.83 % is the safe ceiling.

### Verify

`verify_preset.py` prints `✅ MATCH` (PnL $69,571 / DD $2,367 / N=608 /
WR 52.6 % / PF 1.66, $0 deviation).

## Risks & next iteration

1. **Period concentration risk**: 16.7 months on a single MNQ
   front-month contract. The `sl_lookback=10` and `BO 11-12/14-15`
   findings rest on this period. A walk-forward (e.g. 12m train /
   4m test) would be the responsible next check.
2. **The wider SL (lookback=10) is a structural change** vs every prior
   MNQ MCV2 campaign. Spot-check after the next contract roll.
3. **Risk is at the DD cliff**: at risk=0.84 % DD jumps to $2,744.
   Tiny trade-timing drift could push the WINNER over budget on a
   slightly different period.
4. **`rr_tp=1.55` is between two Pine-friendly values** (1.5 and 1.6).
   The Pine code can express 1.55 fine, but it's an unusual choice —
   document for the trader.

## Top alternatives

| Preset                          | rr   | risk    | PnL    | DD     | WR    | Notes |
|---------------------------------|------|---------|--------|--------|-------|-------|
| **WINNER**                      | 1.55 | 0.83 %  | $69.6k | $2,367 | 52.6 %| chosen, $133 DD headroom |
| ALT-WR (Phase 11 pick)          | 1.50 | 0.83 %  | $65.9k | $2,495 | 53.0 %| +0.4 pp WR but PnL -$3.7k |
| ALT-PNL (above DD budget)       | 1.55 | 0.84 %  | $78.6k | $2,729 | 52.6 %| +$9k PnL but DD over $229 |
| ALT-SAFE (less aggressive risk) | 1.55 | 0.80 %  | $68.0k | $2,325 | 52.6 %| -$1.5k PnL, +$42 DD headroom |
| ALT-MAX-WR                      | 1.25 | 0.625 % | $39.4k | $2,171 | 53.7 %| highest WR margin, much less PnL |

Use **ALT-SAFE** if you want a more conservative DD buffer.
Use **ALT-WR** if you want WR ≥ 53 % at the cost of $3.7k PnL.

## Negative results worth noting

- **`be_at_rr` does NOT help WR**. Confirmed across rr_tp ∈ {1.0…2.5}
  and be_at_rr ∈ {0.5…2.0}. Reason: BE exits count in `total_trades`
  but not in `wins`, so WR drops mechanically.
- **`sig_filter_on=True`** (bilateral SIG bonus) — completely inert
  with seed thresholds & gap. Confirmed match with v4 finding.
- **Adding modules' point weights to 2** — almost always blows up DD.
  Only `pts_ut_bot=2` is borderline-acceptable but breaks budget.
- **Disabling any major module** — all needed. The strategy is
  multi-confirmation by design.
- **`rr_tp ≥ 1.65`** with this stack — WR drops below 50 % AND DD
  blows up. Hard ceiling.
- **`sl_min_pct > 0`** — degrades all three metrics. Same finding as
  v4.
- **BO 15:30-17:00** (a previous candidate) — removes profitable trades
  net negative.
