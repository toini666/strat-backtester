# Campaign Report — COMBO RIsky MGC+MNQ (MomentumCheckerV2)

**Date**: 2026-05-21
**Seed preset**: `COMBO RIsky Multi-Asset — MGC/MNQ`
**Period**: 2025-01-07 → 2026-05-15 · initial equity $50,000
**Sim budget**: 500 nominal · **~88 used**
**Goal**: drop combined `max_dd_$` < $2,500 with minimal PnL cost
**Locked constraints**: `maxContracts=20` on both legs; daily limits off
(deliverable); `auto_close_hour=22`

## TL;DR

The DD target is satisfied with the absolute minimum margin available:
**DD pulled from $3,252 → $2,494 (−23 %)**, paying **−$24,978 PnL (−19 %)**.
Two changes vs. seed; every other parameter, blackout, and engine setting is
preserved.

| | Seed (RIsky) | **WINNER** | Δ |
|---|---|---|---|
| Net PnL | $131,406 | **$106,428** | **−$24,978 (−19.0 %)** |
| Max $ DD | $3,252 | **$2,494** | **−$758 (−23.3 %)** |
| Trades | 1,638 | 1,639 | +1 |
| Win rate | 39.6 % | 39.5 % | −0.1 pp |
| Profit factor | 1.57 | 1.57 | 0 |
| P/DD ratio | 40.4 | **42.7** | **+2.3** |
| MGC PnL | $56,275 (810 t) | $56,275 (810 t) | unchanged |
| MNQ PnL | $75,132 (828 t) | $50,153 (829 t) | −$24,979 |

**Verified**: `verify_preset.py` confirms exact reproducibility through both
the harness and the actual backend `run_multi_backtest` path —
`harness vs backend: PnL Δ=$0, DD Δ=$0`. ✅ MATCH.

The preset is written to `data/presets.json` as:
> `[Auto] COMBO RIsky — MGC/MNQ — DD<$2.5k (PnL $106.4k / DD $2.49k)`

## What changed vs. the seed

Exactly two changes, both on the **MNQ** leg. MGC is byte-identical to the
seed (params, risk, blackouts).

| Param | seed | WINNER | Source |
|---|---|---|---|
| MNQ `riskPerTrade` | 0.60 % | **0.405 %** | Phase 08 |
| MNQ `be_at_rr` | 0 | **2.4** | Phase 01 / 05 |

MNQ `be_at_rr=2.4` makes the SL move to entry once price has progressed 2.4 R,
converting a sliver of would-be losers into breakeven exits. By itself it is
a small PnL-positive change (Phase 01 showed `be_at_rr=2.4` slightly *raises*
PnL at unchanged risk), so the deliverable layers it on top of the risk cut
to recover ~$500 of PnL "for free".

## Why this PnL cost is the floor on this seed

Three other levers were exhaustively tested and **none** reach DD<$2,500 with
less PnL cost than risk reduction.

### 1. `MNQ be_at_rr` alone is insufficient (Phase 01)
Sweep over `be_at_rr ∈ {0, 1.0, 1.5, 1.8, 2.0, 2.2, 2.4, 2.6, 3.0}` at base
risks. Best DD = **$2,933** at `be_at_rr=1.5` (still $433 over target). The
DD-driving trades are straight losers (Phase 02 episode trace: 5 consecutive
MNQ ~$250 losses on 04-23/24 and 04-27, no peak-before-trough), so the SL
never reaches the breakeven trigger.

### 2. MGC risk reduction barely moves DD (Phase 04)
At fixed MNQ risk=0.60 %, sweeping MGC risk 0.30 → 0.60 % keeps DD between
$3,252 and $3,493. MGC contributes too little to the combined DD episode;
MGC=0.53 % sits on a favorable `int(contracts)` rounding cell and is kept.

### 3. MNQ blackout extension makes things **worse** (Phase 06)
Trying to kill the DD cluster by extending MNQ blackouts (the 04-23 losing
trades sit at 15:17/15:38/16:48):

| Variant | PnL | DD |
|---|---|---|
| base | $131,406 | $3,252 |
| extend-13-17 | $113,630 | $3,161 |
| extend-15-17 | $114,242 | $3,357 |
| extend-15:30-17 | $115,256 | $3,681 |

Every blackout extension destroys 15–17 k of MNQ profit elsewhere in the
sample, and most actually *increase* DD because they cut winning trades that
were offsetting losses later in the day. The DD-driving cluster persists
because some of the losses are early (15:17, 15:38) and pulling the curtain
forward kills the winners that follow them.

### 4. The 0.0050 → 0.0049 rounding cliff (Phase 08)
The most informative finding for tuning: MNQ DD has a hard cliff between
risk 0.00500 and 0.00490 — DD drops from $3,030 to $2,625 (−$405) while
PnL drops from $126k to $116k (−$10k). Below that there's a second smaller
cliff at 0.00420 (DD $2,519 → $2,494 at 0.00405). The locked WINNER sits
right past the second cliff, on the highest-PnL cell that still satisfies
the DD constraint.

| MNQ risk | PnL | DD |
|---|---|---|
| 0.00500 | $126,067 | $3,030 |
| 0.00490 | $115,675 | $2,625 |
| 0.00420 | $107,614 | $2,519 |
| **0.00405** | **$106,428** | **$2,494** ✓ |
| 0.00400 | $106,385 | $2,494 |

## Curiosity: daily win/loss limits in `after_close` mode (Phase 07)

User explicitly requested testing daily limits — results below. **None reach
DD<$2,500**; the lever does not break the structural DD floor and **the
deliverable does not use it**.

| Limit (W / L) | PnL | DD |
|---|---|---|
| baseline (no limits) | $131,406 | $3,252 |
| +500 / −700 (preset default fields) | $109,585 | $3,164 |
| +700 / −500 | $105,382 | $3,380 |
| +1000 / −700 | $124,709 | $3,252 |
| +1500 / −700 | $123,378 | $3,252 |
| +500 / −1000 | $113,618 | **$2,901** |
| no win / −500 only | $115,818 | $3,380 |
| no win / −700 only | $127,029 | $3,252 |
| no win / −1000 only | $131,171 | $3,252 |
| +500 only / no loss | $114,111 | **$2,901** |
| +1000 only / no loss | $129,320 | $3,252 |

The best DD with limits is $2,901 (`+500/-1000` or `+500-only/no-loss`), and
that costs −$17,788 PnL — *worse than the locked risk-reduction deliverable
on both axes*. So even before user preference, this lever is dominated.

The reason limits in `after_close` mode don't help: they only stop trading
**the next day** once the prior day already closed past the limit. The DD
cluster on 04-23 → 04-28 has multiple losing days in a row, and `after_close`
gates only halt entries the morning *after* a loss-day — meaning the first
losing day still runs to completion and contributes its full DD. With losses
clustered across 3 trading days the cumulative DD is barely dented.

## What I didn't change (preserved from the seed)

- MGC: every parameter, blackout window, and risk_per_trade=0.53 %.
- MNQ: every parameter except `be_at_rr` (0 → 2.4) and `riskPerTrade`
  (0.60 → 0.405 %). MNQ blackouts unchanged.
- `auto_close_hour=22` on both legs.
- `maxContracts=20` on both legs (user-locked).
- Daily limits off on both legs.

## Methodology notes

- **Harness path**: `scripts/goals/_shared/harness.py::run_backtest` is the
  single backtest entrypoint; the campaign-local `_campaign.py::run_multi`
  wraps it for the two-leg multi-asset case using the **same** mechanics the
  backend uses in `run_multi_backtest` (sorted-by-entry_time combined trade
  stream, max peak-to-trough $ across the merged stream).
- **DD metric**: `max_drawdown_dollars` from the simulator, not %×initial.
  The two diverge once equity grows past the starting $50 k — confirmed here:
  WINNER `max_drawdown_dollars` = $2,494 corresponds to `max_drawdown` =
  3.27 %, but the % only lines up at this single (peak, trough) pair.
- **Verify**: `verify_preset.py` replays the preset through the *backend's*
  `run_multi_backtest` (the same code path the UI uses for `/backtest/multi`),
  reconstructs `_combined_metrics` from the returned trade list, and asserts
  PnL Δ=$0, DD Δ=$0 vs. the harness. Both report PnL=$106,428 / DD=$2,494.

## File layout

```
scripts/goals/2026-05-21_MomentumCheckerV2_ComboRisky_MGC_MNQ/
├─ README.md
├─ REPORT.md                         (this file)
├─ build_winner_preset.py            writes winner_preset.json + presets.json
├─ verify_preset.py                  must print "✅ MATCH"
├─ winner_preset.json
├─ logs/
│  ├─ 00_baseline.log
│  ├─ 01_mnq_be_sweep.log
│  ├─ 02_dd_episode_analysis.log
│  ├─ 03_mnq_risk_sweep.log
│  ├─ 04_mgc_risk_sweep.log
│  ├─ 05_joint_risk_grid.log
│  ├─ 06_mnq_blackout.log
│  ├─ 07_daily_limits_curiosity.log
│  ├─ 08_fine_tune_boundary.log
│  └─ verify_preset.log
└─ sweeps/
   ├─ _campaign.py                    constants + run_multi helper
   ├─ 00_baseline.py
   ├─ 01_mnq_be_sweep.py
   ├─ 02_dd_episode_analysis.py
   ├─ 03_mnq_risk_sweep.py
   ├─ 04_mgc_risk_sweep.py
   ├─ 05_joint_risk_grid.py
   ├─ 06_mnq_blackout.py
   ├─ 07_daily_limits_curiosity.py
   └─ 08_fine_tune_boundary.py
```
