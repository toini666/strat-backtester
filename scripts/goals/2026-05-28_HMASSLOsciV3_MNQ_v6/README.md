# 2026-05-28 — HMASSLOsciV3 MNQ 7m v6

Campaign restart on the production preset `MNQ-PROD - HMASSLOsciV3 - MNQ 7m`,
with new v3.1 parameters available (`min_sl_points`, `entry_cross_mode`,
`ema_exit_ext_on` + `ema_exit_len`).

## Locked
- symbol: MNQ
- interval: 7m
- date range: 2025-01-06 → 2026-05-22
- max_contracts: 20
- daily win/loss limits: OFF

## Free
- all strategy params
- blackout windows
- risk_per_trade

## Goal
Improve PnL (or keep similar) AND reduce max drawdown.

## Seed metrics
PnL=$63,143 | DD=$3,557 | N=1,070 | WR=49.3% | PF=1.75

## WINNER
PnL=$80,709 | DD=$3,236 | N=1,299 | WR=48.7% | PF=1.64
→ **+$17,566 PnL (+27.8%)** and **-$321 DD (-9.0%)** vs seed.

Preset file: `winner_preset.json` (also inserted into `data/presets.json`
as "[WIN MNQ v6] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $80.7k / DD $3.24k)").
Replays with `verify_preset.py` → ✅ MATCH.

## Sweeps
- `00_bench_seed.py` — reproduce seed metrics exactly.
- `01_new_params_1d.py` — explore v3.1 params one axis at a time.
- `02_new_param_combos.py` — `min_sl_points × max_sl_points × ema_exit_ext` combos.
- `03_core_params_1d.py` — re-sweep all core strategy params (~70 sims).
- `04_core_combos.py` — combine top picks from 03; finds `hma_pol_bars=5 +
  sig_extreme=60 + hw_extreme=35` champion (+$4,964 PnL / -$181 DD).
- `05_champion_stack.py` — extend champion stack (more extremes, mf_length,
  cloud/delta variations).
- `06_blackouts.py` — hour-of-day analysis + blackout window variants.
- `07_blackout_combos.py` — cross-product of blackout stacks with 3 strategy
  candidates (A=high PnL, B=balanced, C=DD-cut).
- `08_risk_sweep.py` — risk_per_trade ∈ [0.30%, 0.65%] on each candidate.
- `09_finetune_risk.py` — fine grid 0.525-0.625% around the optimum.
- `10_build_winner.py` — assemble & write the winner preset.

Total sims: ~332 / 500 budget.

## Verify
```bash
python scripts/goals/2026-05-28_HMASSLOsciV3_MNQ_v6/verify_preset.py
# → ✅ MATCH
```

See `REPORT.md` for the full analysis and findings on the new v3.1 params.
