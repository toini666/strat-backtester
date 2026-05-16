# HMASSLOsciV3 / MNQ — Campaign v3 (no time-of-day blackouts)

**Date**: 2026-05-16
**Strategy**: `HMASSLOsciV3`
**Symbol**: MNQ
**Period**: 2025-01-06 → 2026-05-15 (~17 months, contracts H25 → M26)

## Objectives

| Metric | Target |
|---|---|
| Net PnL | ≥ $35,000 (goal $40,000) |
| Max DD | < $2,500 |

## Constraint: no time-of-day blackouts

Starting point is the v2 campaign winner (`scripts/goals/2026-05-15_HMASSLOsciV3_MNQ_v2/winner_preset.json`, PnL $30.4k / DD $2.0k), but **all hourly blackouts removed**. Only the default `22:00-23:59` window stays active (post-close).

The campaign explores whether better parameter tuning can recover (and exceed) the v2 result *without* relying on time-of-day filtering — that filtering is the v2 winner's biggest lever (~+$30k captured from blackout hours), so dropping it forces the strategy itself to do the work.

## Method

8 sweeps in `sweeps/`:

1. **`01_baseline_tfs.py`** — replay v2 preset params (minus blackouts) across 7m/10m/3m/5m. Establishes how much the blackouts were worth.
2. **`02_filter_activation.py`** — toggle every optional v3 filter on the best TF.
3. **`03_strategy_params.py`** — 1-D sweeps on indicator lengths / thresholds.
4. **`04_risk_and_daily_limits.py`** — risk_per_trade sweep + daily limits (`intra_bar` first).
5. **`05_hour_analysis.py`** — bucket trades by hour/dow for diagnostic only (blackouts not added).
6. **`06_combo.py`** — 2-D combo of best params from sweeps 2-3.
7. **`07_finetune.py`** — tight fine-tune around best combo + risk to hit the targets.
8. **`08_final_validation.py`** — winner + 3-5 alternatives, write preset.

## Reproduction

```bash
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v3/verify_preset.py
```

Should print `✅ MATCH`.

The preset is also inserted into `data/presets.json` and visible at the top of the UI favorites list.
