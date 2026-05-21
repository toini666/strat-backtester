# 2026-05-21 — MomentumCheckerV2 MNQ 7m v3

Optimization campaign seeded from the v2 WINNER preset (PnL $80.6k / DD $3.02k).

## Goal achieved

The hard DD target (DD < $2,500) **is satisfied** in the WINNER preset
($DD = $2,493), with PnL effectively at seed level (−$167 / −0.2%, within
noise of one trade).

The breakthrough came in Phase 10b: the `int(contracts)` rounding cliff
that appeared "structural" at `sl_max_points=40` was shifted into the
feasible zone by raising `sl_max_points` to 42.

## Deliverables

| Preset                            | PnL      | $ DD     | Notes                              |
|-----------------------------------|----------|----------|------------------------------------|
| `winner_preset.json`              | $80,398  | **$2,493** | **DD target ✓**, PnL noise-equal to seed |
| `alt_pnl_strict_preset.json`      | $80,790  | $2,539   | PnL strict above seed, DD +$39 over |
| `alt_high_pnl_preset.json`        | $88,247  | $2,845   | Max PnL gain (+$7,682 vs seed)     |

All three are inserted in `data/presets.json` at the top of UI favorites.

## Reproduction

```bash
# Replay the WINNER preset and verify ✅ MATCH
python scripts/goals/2026-05-21_MomentumCheckerV2_MNQ_v3/verify_preset.py
```

## Sweeps

| File                               | Purpose                                                 |
|------------------------------------|---------------------------------------------------------|
| `sweeps/00_baseline.py`            | Reproduce seed + trade-by-hour diagnostic              |
| `sweeps/01_risk_geometry.py`       | `be_at_rr × rr_tp`, `sl_max × tb`, `sl_lookback`       |
| `sweeps/02_hma_canal.py`           | HMA canal V3-inspired exploration                       |
| `sweeps/03_thresholds.py`          | `long × short_threshold × min_gap` joint               |
| `sweeps/04_pts_combos.py`          | Point-weight bumps / disables / combos                  |
| `sweeps/05_filters.py`             | `max_candle_pct × sig_extreme`, `hw_level × hw_extreme`|
| `sweeps/06_combo_lattice.py`       | Top deltas from P1–P5 stacked                           |
| `sweeps/07_blackouts.py`           | Blackout fine-tune (H=01 target)                        |
| `sweeps/08_compile_and_risk.py`    | Fine 0.005 % risk-band sweep on P6 anchor              |
| `sweeps/09_final_validation.py`    | Pareto refinement                                       |
| `sweeps/10b_break_dd_wall.py`      | **Cliff-shift discovery (sl_max=42 trick)**             |
| `sweeps/10c_final_push.py`         | Narrow the magic spot near the cliff                    |
| `sweeps/10d_final_final.py`        | tb / sl_lookback / blackouts at the edge                |

See `REPORT.md` for full phase-by-phase findings, the `int(contracts)`
cliff explanation, and lessons learned for future campaigns.
