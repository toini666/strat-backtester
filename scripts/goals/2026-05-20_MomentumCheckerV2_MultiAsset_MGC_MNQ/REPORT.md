# Campaign Report — MomentumCheckerV2 Multi-Asset (MGC + MNQ 7m) — DD reduction

**Date**: 2026-05-20
**Goal**: reduce combined max_dd_$ below **$2,300** (ideally **$2,000**) on the
"Base combo momCheckv2 Multi-Asset — MGC/MNQ" preset, sacrificing as little PnL
as possible.
**Constraints (locked)**: maxContracts=20, no daily win/loss limits.
**Period**: 2025-01-07 → 2026-05-15 (16+ months), initial equity $50,000.
**Budget**: 500 sims. Used: **~474**.

## Result — WINNER

```
[Auto] MomentumCheckerV2 — MGC+MNQ multi-asset — DD<$2.3k (PnL $96.4k / DD $2.25k)

PnL=$96,428   DD=$2,254   N=1,654   WR=39.9%   PF=1.57   P/DD=42.8
  MGC=$55,592 (856 trades) at risk=0.53%
  MNQ=$40,836 (798 trades) at risk=0.345%

Margin under $2,300 hard ceiling: $46.
```

**Verified**: `verify_preset.py` confirms exact reproducibility via both the harness
and the actual backend `run_multi_backtest` code path — `harness vs backend: PnL Δ=$0, DD Δ=$0` ✅.

## Comparison vs baseline preset

| | Baseline ("Base combo") | **WINNER** | Delta |
|---|---|---|---|
| Net PnL | $138,814 | **$96,428** | **−$42,386 (−30.5%)** |
| Max $ DD | $3,601 | **$2,254** | **−$1,347 (−37.4%)** |
| Trades | 1,648 | 1,654 | +6 |
| Win rate | 40.0% | 39.9% | −0.1pp |
| Profit factor | 1.56 | 1.57 | +0.01 |
| **P/DD ratio** | **38.5** | **42.8** | **+4.3** |

The campaign hit the **hard ceiling ($2,300)** with $46 of margin while
sacrificing $42k of PnL — a 30% PnL cut for a 37% DD cut.

## Soft target ($2,000) — NOT REACHABLE

Despite extensive exploration (Phase 11 section B, Phase 12 section C with
extreme be_mgc=1.0-1.5 and very low risks), the combined account's DD never
went below **$2,204**. The floor is structural:

- MGC's mono-asset DD floor at the 1-contract minimum is ~$2,486 (per
  the mono-asset MGC campaign — `scripts/goals/2026-05-20_MomentumCheckerV2_MGC/REPORT.md`).
- In the combined account, when MGC's worst losing streak (early-April 2026)
  fires while MNQ is also slightly negative, the combined DD lands at $2,204+
  even when MNQ runs at ultra-low 0.15-0.20% risk.

Reaching <$2,000 would require strategy-level changes that eliminate ~2-3 of
MGC's worst losing trades, which is beyond a pure parameter sweep.

## Levers, in order of impact

1. **MNQ `be_at_rr=2.4`** — the breakthrough (Phase 7→9→13). MNQ has
   `be_at_rr=0` in the baseline (no breakeven). Setting it to 2.0-2.4
   moves the SL to entry once price has progressed 2-2.4R, converting
   would-be losers into BE exits. Drops DD by ~$300-400 with surprisingly
   small PnL cost (often net positive). Phase 13 found 2.4 to be the
   sweet spot (`+$5k PnL` vs `2.0` for `+$34 DD`).
2. **Per-leg risk tuning** — Phase 1 showed MGC risk has near-zero impact
   on combined DD (3.6k→3.8k range), while MNQ risk dominates DD. Phase 16
   found that MGC=0.53% hits a **favorable `int(contracts)` rounding cell**
   that gives DD=$2,254 vs $2,292 at MGC=0.50/0.52% (≈$40 lower DD with
   $2k more PnL).
3. **MGC `sl_max_points=80`** (was 100) — Phase 4. Marginally tightens DD
   floor from $2,424 → $2,395.
4. **MGC `max_candle_pct=0.26`** (was 0.30) — Phase 9. Filters out high-noise
   bars, slight PnL+ same-DD improvement.
5. **MNQ risk=0.345%** (was 0.66%) — biggest single risk reduction. Drops
   MNQ contribution from $80.5k to $40.8k, but is the only way to keep
   DD bounded.
6. **MGC params kept**: `be_at_rr=2.0` (the WINNER value), other params from
   mono-asset MGC WINNER (sl_lookback=15, rr_tp=3, etc).

## Levers tried and rejected

- **Blackout extensions** — Phase 5/6 identified MGC H=23 in DST transition
  windows is the worst hour (-$2,288, 12 trades, WR 8.3%). However the
  trades land at ref minutes 0:00-1:00 because of the DST `-1h` offset,
  and a blackout targeting them would also block legitimate winter wall H=0
  trades (+$8,361 net). Net unfavourable.
- **MGC `sl_max_points` < 60** — Phase 4 — tighter SL → more contracts at
  same $-risk → bigger $ losses per stop. DD goes UP.
- **MGC `be_at_rr=1.5`** — Phase 7 — DD goes UP (more trades hit SL before
  reaching new BE).
- **MGC risk > 0.55%** — already over budget.
- **MGC `sl_lookback` 10/12/18/20** — DD jumps to $3-4k. 15 is the sweet
  spot (same as mono-asset finding).
- **MNQ `be_at_rr` ≥ 2.5** — DD jumps to $2,374-$2,446. 2.4 is the cliff edge.

## Sub-$2,300 alternatives — Pareto frontier

For users who prefer different PnL/DD trade-offs while staying under
$2,300:

| Config | PnL | DD | Margin |
|---|---|---|---|
| **WINNER** — MGC=0.53% MNQ=0.345% MNQ_be=2.4 mcp=0.26 | **$96,428** | **$2,254** | **$46** |
| MGC=0.53% MNQ=0.34% MNQ_be=2.4 mcp=0.26 (slightly less MNQ) | $96,198 | $2,254 | $46 |
| MGC=0.55% MNQ=0.34% MNQ_be=2.4 mcp=0.26 (just over) | $98,566 | $2,503 | −$203 ⚠️ |
| MGC=0.50% MNQ=0.30% MNQ_be=2.0 mcp=0.25 (safer)    | $80,732 | $2,204 | $96 |

**Sub-$2,000**: NOT REACHABLE (floor $2,204).

## Fragility note

Like the mono-asset MGC winner, this preset sits on a **favorable
`int(contracts)` rounding cell**. The Phase 16 grid shows:

| MGC risk | DD$ |
|---|---|
| 0.525% | $2,292 |
| **0.530%** | **$2,254** |
| 0.535% | $2,412 |
| 0.540% | $2,503 |
| 0.550% | $2,503 |

The $158 DD jump between 0.530% and 0.535% reflects the rounding flip.
A future data update or contract switch could shift the boundary by ±$50.
A more robust fallback: **MGC=0.50% MNQ=0.30% MNQ_be=2.0 mcp=0.25**
(`$80,732 / $2,204`, $96 margin), at the cost of $15.7k PnL.

## Sim budget accounting

| Phase | Description | Sims |
|---|---|---|
| 0 | Baseline replay | 1 |
| 1 | Per-leg risk sensitivity | 15 |
| 2 | Joint risk grid (28 cells) | 28 |
| 3 | Worst DD episode analysis | 1 |
| 4 | MGC sl_max_points sweep | 8 |
| 5 | Hour-bucket analysis | 1 |
| 6 | H=23 trade inspection (no rerun) | 1 |
| 7 | BE/RR_TP per leg | 24 |
| 8 | Joint risk × MNQ_be 1.5/2.0 grid | 48 |
| 9 | Pareto fine-tune (MNQ_be fine, mcp, sll, MGC_be) | 49 |
| 11 | Stack winning levers + sub-$2k push | 104 |
| 12 | High-PnL push + sub-$2k aggressive | 65 |
| 13 | Final refine — MNQ_be high, MNQ risk fine, mcp, MGC risk | 18 |
| 14 | Final micro-combos | 14 |
| 15 | Final winner search | 14 |
| 16 | Winner lock (MGC risk fine grid + variants) | 19 |
| Verify | harness ↔ backend cross-check | 1 |
| | **Total** | **~411** |

Within budget (~89 sims unused).

## Files

- `winner_preset.json` — the winning multi-asset preset, written to
  `data/presets.json` for the UI favorites list.
- `verify_preset.py` — replays the preset through both the harness and the
  actual backend code path. Outputs `✅ MATCH`.
- `sweeps/*.py` — one script per phase. Run any of them with the venv
  active.
- `logs/*.log` — captured outputs of each sweep.
- `build_winner_preset.py` — re-runs the winning config and rewrites the
  preset. Edit the constants if you want a different lock.

## Recommendation for live use

- **Primary**: load **"[Auto] MomentumCheckerV2 — MGC+MNQ multi-asset — DD<$2.3k (PnL $96.4k / DD $2.25k)"** from favorites. PnL $96.4k, DD $2,254. Margin $46 under the user's $2,300 ceiling.
- **Safer fallback**: switch MGC risk in the UI from 0.53% → 0.50% and MNQ to 0.30% with MNQ be_at_rr=2.0 → PnL $80.7k, DD $2,204, margin $96.
- **The MGC=0.53% sweet spot is fragile** — verify the DD again after any data update or contract rollover. If the margin drops below ~$30, switch to the safer fallback.
