# Campaign Report — MomentumCheckerV2 MNQ 7m v4

**Date**: 2026-05-23
**Seed**: user-provided `BEST-MNQ MomentumCheckerV2 - MNQ 7m`
  (PnL $75,132 / DD $2,420 / WR 39.6 % / PF 1.56 / N=828)
**Goal**: improve PnL, keep DD ≤ seed, raise WR.
**Period**: 2025-01-07 → 2026-05-15 (16 months)
**Sim budget used**: ~430 / 500

## TL;DR

The winning config beats the seed on **every** metric simultaneously:

| | Seed | WINNER | Δ |
|-|-|-|-|
| PnL          | $75,132 | **$88,430** | **+$13,298 (+17.7 %)** |
| max_dd_$     | $2,420  | **$2,341**  | **−$79** |
| Win rate     | 39.6 %  | **41.8 %**  | **+2.2 pp** |
| Profit factor| 1.56    | **1.72**    | +0.16 |
| SL rate      | 60.3 %  | 57.9 %      | −2.4 pp |
| Trades       | 828     | 765         | −63 |

## What changed vs seed

Just six params + one blackout window. Every other knob in
`default_params` (HMA stack, alligator, UT, STC, oscillator filters,
points weights, thresholds, `sl_lookback`, `sl_min_pct`, the SIG filter
family…) is unchanged.

| Param | Seed | WINNER | Phase that found it |
|-|-|-|-|
| `ema_prin_len`     | 30    | **34**     | P4 + P7 fine |
| `ema_sec_len`      | 20    | **18**     | P7G |
| `st_atr`           | 10    | **14**     | P4D |
| `tick_buffer`      | 2     | **0**      | P1D |
| `sl_max_points`    | 41    | **42**     | P7B + P8C |
| `riskPerTrade`     | 0.6 % | **0.625 %**| P7A + P9A |
| BO 07:00-08:00     | —     | **active** | P5 |

All six are nearly independent in their effect (additive in P6
combos). The blackout is by far the largest single contributor:
in isolation it gives +$1.6k PnL / −$256 DD / +0.7 pp WR.

## The user's literal hypothesis combo (Phase 11) — receipts

The user explicitly described: *"peut-être en réduisant le look-back
ET en mettant un minimum de stop loss"*. Phase 1 tested each axis
independently. The discriminating combo — short `sl_lookback` (1, 2)
*combined with* a `sl_min_pct` floor — was tested in Phase 11
(36 sims) against BOTH the seed anchor and the WINNER anchor.

The grid result on the WINNER anchor (best `mp` per `lb`):

| lookback | best mp | PnL     | DD      | WR    | vs WINNER         |
|----------|---------|---------|---------|-------|-------------------|
| 1        | 0.125   | $67,893 | $3,680  | 38.6% | −$20.5k, DD +$1,339|
| 2        | 0.125   | $75,940 | $3,012  | 40.4% | −$12.5k, DD +$671 |
| 3        | 0.05    | $82,752 | $3,270  | 40.4% | −$5.7k,  DD +$929 |
| **WIN**  | (5, 0)  | **$88,430** | **$2,341** | **41.8 %** | — |

The floor *does* what it was meant to: at `lb=2` alone (no floor), DD
was $4,770; with `mp=0.1` floor it comes down to $3,535. So the floor
mechanic works — but every (lb, mp) cell is dominated by the WINNER's
wider lookback geometry on PnL, DD, AND WR simultaneously. The user's
hypothesis is **empirically tested in its specific stated form** and
strictly dominated.

## Receipts — lowest 10 losers on the seed (Phase 0)

```
pnl      entry       exit    Δprice  size  status                 side
-11.2    24744.75    24746.00  +1.25    3   Auto-Close (loss)      Short
-94.8    21821.50    21823.25  +1.75   20   Stop Loss              Short
-231.7   21278.50    21316.50  +38.0    3   Stop Loss              Short
-231.7   25411.25    25449.25  +38.0    3   Stop Loss              Short
-234.7   19944.75    19906.25  -38.5    3   Stop Loss              Long
-234.7   26840.75    26802.25  -38.5    3   Stop Loss              Long
-236.2   19789.00    19827.75  +38.75   3   Stop Loss              Short
-237.7   21331.00    21370.00  +39.0    3   Stop Loss              Short
-237.7   21621.00    21582.00  -39.0    3   Stop Loss              Long
-237.7   24634.25    24595.25  -39.0    3   Stop Loss              Long
```

9 of 10 are true SL hits at exactly ~38 points = the seed's
`sl_max_points=41` cap minus rounding. The "in and out at same price
with fees turning it red" phenomenon is represented by ONE trade
(the −$11.2 row) out of 500 losers — not a population. This is why
`be_rate = 0.0 %` on the seed: that *visual impression* doesn't
translate into an actual population of trades on this preset.

## What did NOT work (negative results — equally important)

These categories were tested extensively and either rejected or
proved no-op:

1. **`sl_min_pct` (NEW user param)** — every floor value (0.05…0.25)
   degraded PnL, DD, AND WR on both seed and WINNER anchors (Phase 1B
   1-D, Phase 11 combo). The user's hypothesis "tighter SL via min
   floor reduces SL-on-reversal trades" is **not supported by the data**
   in this strategy/seed/symbol regime.

2. **SIG range filter family (NEW user params)** — `sig_filter_on=True`
   is a *bilateral additive bonus*, not a reject. With seed's
   thresholds / min_gap it is functionally **dead** (any |sig| > level
   adds the same N points to both `pts_long` and `pts_short`, so the
   gap that gates entries is unchanged). I also added a brand-new
   `sig_range_reject` param (true reject when `|sig| ≤ sig_level`) to
   match the user's stated intent ("zone à éviter"). Reject *does*
   drop trades (834 → 434 at lvl=25) — but WR **slightly decreases**
   (39.6 % → 36.2 %), PnL drops monotonically and DD blows up. The
   user's hypothesis "low-|sig| trades dominate losers" is **not
   confirmed** — losing trades are real SL-hits after a strong
   signal, not median-SIG noise.

3. **All oscillator/core params at seed** — `mf_length`, `mf_smooth`,
   `hyper_wave_length`, `signal_length`, `signal_type`, `hw_extreme`,
   `delta_off_mode`, `max_candle_pct` are each ALONE optimal at seed.
   Any move ≥ $20k PnL drop. The seed was already a hard local
   optimum on these.

4. **Most point weights** at their seed values (mostly 1) — any move
   to 0 or ≥ 2 degrades PnL substantially. The one exception was
   `pts_hma_slow=0` (slight +WR / −PnL trade); not retained because
   the slot was better spent on `ema_prin_len=34`.

5. **`sl_lookback`** — 2…10 sweep, seed=5 is the unique optimum.

6. **`rr_tp=2.25`** — gives +1.1 pp WR but −$7k PnL (the WR/RR
   tradeoff is structural; trades become smaller wins).

7. **Blackouts other than 07-08** — `+01:00-02:00` (the obvious
   candidate from the H=01 hour bucket: -$1.087k net at 26 % WR)
   removes those losers but the trades that would have followed them
   were profitable on average; net −$2.6k PnL. Counter-intuitive but
   reproducible.

## Engine change shipped with this campaign

The simulator now returns three additional metrics in `metrics`:

- `sl_rate`   — % of trades whose status is `"Stop Loss"` or `"Trailing SL"`
- `be_rate`   — % of trades whose final price travel was ≤ 2 ticks
                AND ended in the red (catches the user's "in/out at
                same price, fees turn it red" phenomenon, plus any
                `status == "Breakeven"` exits)
- `loss_other_rate` — remaining non-winning trades (small losses from
                      EMA/Canal/Auto-Close exits)

`win_rate + sl_rate + be_rate + loss_other_rate ≈ 100 %`. Available
in:
  - `src/engine/simulator.py:1857-1882` (computation + metrics dict)
  - `frontend/src/api.ts` (`BacktestMetrics` type)
  - `frontend/src/components/Dashboard.tsx:72-79` (compact display
    under Win Rate)
  - `scripts/goals/_shared/harness.py::summarize()` and `fmt_summary()`

**Important finding from the breakdown**: on this strategy with
`tp1_full_exit=True` and `be_at_rr=0` (seed values), the `be_rate` is
**0.0 %** — there are no trades exiting at price ≈ entry. The "BE
losses from fees" phenomenon the user described visually is therefore
not present in this particular preset. It would appear if `be_at_rr > 0`
were ever turned on (which would also drop PnL substantially, per P2E).

The breakdown's main signal is `sl_rate`, not `be_rate`: the seed's
60.3 % → WINNER's 57.9 %.

## Phase-by-phase

| Phase | Description                                   | Sims |
|-------|-----------------------------------------------|------|
| 0     | Baseline reproduction + hour & sample dump   | 1    |
| 1     | SL geometry (lookback, min_pct, max, tb, rr) | 65   |
| 2     | SIG bonus filter + be_at_rr + sig_extreme    | 36   |
| 2b    | NEW `sig_range_reject` true filter           | 12   |
| 3     | Oscillator & core params                     | 71   |
| 4     | Point weights + EMA/ST/UT lengths            | 88   |
| 5     | Blackouts                                    | 11   |
| 6     | Combo lattice on survivors                   | 25   |
| 7     | Fine-tune around P6 winner                   | 47   |
| 8     | Final Pareto crystallization                 | 47   |
| 9     | Risk edge crawl + last blackout combos       | 22   |
| 10    | Winner + verify                              | 2    |
| 11    | User-combo discriminating test (`lb × mp`)   | 36   |
|       | **Total**                                    | **~463** |

### Phase 0 — Baseline & diagnostic
- Recomputed exact $-DD = $2,420 (the seed preset only stored % DD = 4.29).
- Status breakdown: 322 TPs, 499 SLs, 6 Auto-Close wins, 1 Auto-Close loss.
  **No "Breakeven" status exits** with seed config.
- Hour buckets identified H=01 (−$1,087 / 26 % WR / N=39) and H=07
  (+$1,374 / 33 % WR / N=48) as candidates.
- Sample of 10 lowest losers: 9/10 were SL hits at ~38 points (i.e.,
  the seed's sl_max_points=41 cap was the active constraint on most
  losses) — confirms user's "SL trop éloigné" intuition is structurally
  valid even though tightening it via lookback/min_pct didn't help in
  Phase 1.

### Phase 1 — SL geometry
65 sims across `sl_lookback`, the **new** `sl_min_pct`, `sl_max_points`,
`tick_buffer`, `rr_tp`. Findings:
- `sl_lookback=5` (seed) is the unique optimum.
- `sl_min_pct=0` (seed) — every positive floor degrades all metrics.
- `tick_buffer=0` gives +$3k PnL / +$384 DD (kept for combo).
- `sl_max_points=50` gives +$6k PnL / +$388 DD (close miss on DD).
- `rr_tp=2.25` gives +1.7 pp WR / −$7.7k PnL (structural).

Key conclusion: **the seed is already on a tight local optimum for SL
geometry — `sl_min_pct` does not help**.

### Phase 2 — SIG filter + be_at_rr
36 sims. Found that `sig_filter_on` is a *bilateral additive bonus*,
completely invariant on |sig| above level when min_gap is the binding
constraint (gap is `pts_long - pts_short`, the bonus shifts both
equally). With or without it, with all permutations of thresholds /
gap, no useful effect.

`be_at_rr ∈ {0.5, 1.0, 1.5, 2.0}` does create true "Breakeven" exits
(BE rate 5.9 %–55.9 %) but drops PnL substantially (−$9k to −$48k);
not retained.

### Phase 2b — True SIG range reject (NEW code)
The user described the SIG param as "une zone de range à éviter", i.e.
a reject. The existing implementation is a bonus. So I added a new
param `sig_range_reject` (default False) on `MomentumCheckerV2` that
rejects entries when `|sig| ≤ sig_level`.

12 sims with `sig_range_reject=True × sig_level ∈ [2, 25]`. Filtering
DOES drop trades (834 → 434) but WR stays flat or **decreases**, PnL
drops monotonically, DD blows up. The "median-SIG losers" hypothesis
is not supported.

The new param is shipped (defaults to False so no existing preset is
affected). It can be used later if a different strategy / seed
benefits, but not on this preset.

### Phase 3 — Oscillator & core params
71 sims. **Every single param at seed is the unique optimum**:
`mf_length=35`, `mf_smooth=5`, `hyper_wave_length=5`, `signal_length=3`,
`signal_type=SMA`, `hw_extreme=20`, `delta_off_mode="both"`,
`max_candle_pct=0.30`. The seed is a hard local optimum here.

### Phase 4 — Point weights & per-indicator params
88 sims. Most point weights are also at their seed optimum (1).
Notable finds:
- **`ema_prin_len=35`**: PnL $76,599 / DD $2,458 / WR 40.3 % / PF 1.61
  — clean +PnL +WR but +$38 DD. Promising for combos.
- `st_atr=14`: PnL $76,080 / DD $2,583 / WR 39.9 % — small +PnL but +$163 DD.
- `pts_hma_slow=0`: WR +0.4 pp, PnL −$650; marginal.
- `ut_atr_period=14`: PnL +$34, DD +$153; ~neutral.

### Phase 5 — Blackouts
11 sims. **`+07:00-08:00` is a clean Pareto win**:
PnL **+$1,652**, DD **−$256**, WR **+0.7 pp** — all three goals.
`+01-02` removes the H=01 toxic bucket but loses follow-on profitable
trades for a net −$2.6k PnL (kept-DD).

### Phase 6 — Combos
25 sims testing additive combinations of P1/P4/P5 survivors:
- Triple `ema_prin=35 + BO+07-08 + st_atr=14`:
  **$78,126 / $2,209 / 41.1 %** — the first config that improves all
  three goals at once.
- Quad with `tick_buffer=0`:
  **$79,815 / $2,286 / 41.2 %**.
- `+ sl_max_points=50` (+$4.6k PnL / +$599 DD) — DD over budget.

### Phase 7 — Fine-tune around Phase 6
47 sims. Surprises:
- **`ema_prin_len=34`** (not 35) — PnL **+$2k vs 35** at identical DD
  (=$2,286).
- **`ema_sec_len=18`** (not 20) — another +$2.8k PnL at identical DD.
- `sl_max_points=42` (not 41) — +$878 PnL at +$12 DD.
- `risk_per_trade` fine sweep showed PnL scales roughly linearly with
  risk in [0.55 %, 0.65 %], DD grows with it; cliff at 0.65→0.66 %
  jumps PnL from $84.9k → $96.3k but DD from $2,500 → $2,952
  (way over).

### Phase 8 — Final Pareto
47 sims. Confirmed:
- New anchor `ema_prin=34 + ema_sec=18 + st_atr=14 + tb=0 + sl_max=42 +
  BO+07-08` at risk=0.60 % = PnL $86,628 / DD $2,298 / WR 41.8 %.
- The cliff disappears with the new anchor — risk 0.65→0.67 is a
  smooth PnL curve, DD stays at $2,512.
- `ema_prin=34, ema_sec=18` confirmed jointly optimal on a 3×3 grid.

### Phase 9 — Risk edge crawl
22 sims at 0.005 % granularity. Confirmed:
- At 0.629 %, DD = $2,341 (under budget).
- At 0.630 %, DD jumps to $2,427 ($7 over).
- PnL grows ~$110 per 0.005 % in the safe band.
- The risk that maximises PnL strictly under DD = $2,420 is
  **0.625 %** (chosen as the round-number WINNER) or **0.629 %**
  (the literal edge, +$111 PnL).

### Phase 10 — Build & verify
Winner preset built, written to
`scripts/goals/2026-05-23_MomentumCheckerV2_MNQ_v4/winner_preset.json`,
inserted into `data/presets.json` (top of favorites list) as
**`BEST-MNQ MomentumCheckerV2 - MNQ 7m v4`**.

`verify_preset.py` prints `✅ MATCH` (PnL $88,430 / DD $2,341 / N=765 /
WR 41.8 % / PF 1.72, $0 deviation).

## Top alternatives

| Preset      | Risk    | PnL     | DD      | WR    | Notes                       |
|-------------|---------|---------|---------|-------|-----------------------------|
| **WINNER**  | 0.625 % | $88,430 | $2,341  | 41.8 %| **chosen** — DD under seed  |
| ALT-EDGE    | 0.629 % | $88,541 | $2,341  | 41.8 %| literal max-PnL within DD   |
| ALT-RELAX   | 0.65 %  | $91,994 | $2,512  | 41.8 %| DD +$92 over budget         |
| ALT-HIGHPNL | 0.66 %  | $93,338 | $2,512  | 41.8 %| DD over budget by $92       |
| ALT-WR      | 0.62 % + BO+14:30-15:30 | $85,661 | $2,523 | **42.5 %** | highest WR seen, DD +$103 over |

ALT-EDGE matches WINNER to within $111 PnL with the exact same DD —
use it if you want the absolute squeezed PnL within DD ≤ seed.
ALT-WR is interesting if the user wants to push WR above 42 % and
accepts a $103 DD overshoot.

## Reproducibility

```bash
cd <repo-root>
source venv/bin/activate
python scripts/goals/2026-05-23_MomentumCheckerV2_MNQ_v4/verify_preset.py
# Must print: ✅ MATCH
```

The preset is also visible in the UI favorites under the name
`BEST-MNQ MomentumCheckerV2 - MNQ 7m v4` (prepended to
`data/presets.json` by `write_preset`).

## Risks & next iteration

- **Period concentration risk**: 16 months on a single MNQ front-month
  contract. The H=07 blackout finding rests on the same period; a
  walk-forward (e.g. 6m train / 4m test rolled forward) would be the
  responsible next check.
- **The +07-08 hour might be a `MNQ.M26` contract-specific artefact**
  — worth re-checking after the next contract roll.
- **`sl_min_pct` and `sig_range_reject` are shipped but unused** —
  available as levers for future campaigns on different seeds /
  strategies / symbols where the parameter regime is different.
- The `ema_prin_len`/`ema_sec_len` neighborhood is tight; an
  out-of-sample walk-forward could pick 33/15 or 34/15 if the
  shoulder bars look different.
- **PnL ceiling** under DD ≤ seed is around $88.5k — to push higher
  the DD budget must be relaxed (ALT-RELAX/ALT-HIGHPNL territory).
