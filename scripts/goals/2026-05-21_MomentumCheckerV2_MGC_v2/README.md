# 2026-05-21 — MomentumCheckerV2 MGC 7m v2

Re-optimization campaign on MGC for MomentumCheckerV2, seeded from the
v1 WINNER preset (`BEST-MGC MomentumCheckerV2 — MGC 7m — WINNER`).

## Goal achieved

The hard DD target (DD < $2,500) **is satisfied with margin** — the
WINNER preset improves on the seed on both axes simultaneously (+$376
PnL and −$52 DD). The stretch target (DD < $2,000) is **not reachable**
without sacrificing too much PnL — the structural floor for MGC sits
at ≈$2,100.

## Deliverables

| Preset                         | PnL      | $ DD     | P/DD  | Notes                              |
|--------------------------------|----------|----------|-------|------------------------------------|
| `winner_preset.json`           | **$58,625** | **$2,434** | 24.10 | **Pareto-improved seed** (both axes) |
| `alt_robust_preset.json`       | $56,275  | $2,135   | 26.36 | More margin (−$1,974 PnL, +$299 margin) |
| `alt_mindd_preset.json`        | $55,054  | **$2,117** | 26.00 | Min-DD that isn't Pareto-dominated (−$3,571 PnL) |
| Seed (v1 WINNER)               | $58,249  | $2,486   | 23.43 | —                                  |

All three are inserted at the top of UI favorites via `data/presets.json`.

## Reproduction

```bash
# Replay each preset and verify ✅ MATCH (no deviation)
python scripts/goals/2026-05-21_MomentumCheckerV2_MGC_v2/verify_preset.py
```

All three presets reproduce to **$0 deviation** vs the campaign metrics.

## Sweeps

| File                                | Purpose                                                       |
|-------------------------------------|---------------------------------------------------------------|
| `sweeps/00_baseline.py`             | Reproduce seed + hour diagnostic + minimal vs seed BO compare |
| `sweeps/01_sl_max_cliff.py`         | `sl_max_points × risk` cliff-shift (MNQ v3 trick)             |
| `sweeps/02_risk_geometry.py`        | `be_at_rr × rr_tp`, `sl_lookback × tick_buffer`               |
| `sweeps/03_thresholds.py`           | thresholds × `min_gap` × `max_candle_pct`                     |
| `sweeps/04_pts_combos.py`           | point-weight bumps and disables, ema_align combos             |
| `sweeps/05_filters.py`              | `sig_extreme`, `signal_length × mf_smooth`, `delta_off_mode`, `signal_type` |
| `sweeps/06_indicator_lengths.py`    | EMA / ST / STC / Alligator / HMA lengths                      |
| `sweeps/07_blackouts_direction.py`  | blackout variants + direction restriction (long-only/short-only) |
| `sweeps/08_combo_lattice.py`        | combo stacks of P6 ema_prin=15 finding + BO/mcp adjustments    |
| `sweeps/09_fine_risk.py`            | fine risk-band around winners + push for DD<$2k                |
| `sweeps/11_hma_v3_inspired.py`      | HMASSLOsciV3-inspired HMA params on MCV2 (user follow-up)      |
| `build_winner_preset.py`            | builds the 3 presets, inserts in `data/presets.json`           |
| `verify_preset.py`                  | replays presets, prints ✅ MATCH                              |

See `REPORT.md` for the full phase-by-phase findings, the structural
DD-floor explanation, and budget accounting.
