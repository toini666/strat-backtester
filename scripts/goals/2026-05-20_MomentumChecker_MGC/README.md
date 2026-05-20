# 2026-05-20 — `MomentumChecker` on MGC (7 m)

| | |
|-|-|
| Strategy | `MomentumChecker` |
| Symbol / TF | MGC / 7 m |
| Period | 2025-01-07 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 20 (per user constraint) |
| **Goal** | Maximise PnL with `max_dd_$ < $2,500` (strict). Restart from clean defaults, only 22:00-23:59 blackout active initially. |
| **Baseline (defaults)** | $39,124 PnL / $7,884 DD / 2,582 trades / 38.8% WR (PF 1.11) — profitable but DD ~3× over budget |
| **Result** | ✅ **$56,353 PnL / $2,425 DD / 784 trades / 41.3% WR / PF 1.49** — **P/DD = 23.24** |
| Sims used | ~321 (≈64% of the 500 budget) |

Status: **complete** — preset shipped to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

## How to reproduce

```bash
source venv/bin/activate
python scripts/goals/2026-05-20_MomentumChecker_MGC/verify_preset.py
# → ✅ MATCH (PnL=$56,353 / DD=$2,425 / N=784 / PF=1.49)
```

## Files

- `sweeps/_campaign.py` — campaign constants + `baseline_engine()` (only 22:00-23:59 active)
- `sweeps/00_baseline.py` — Phase 0: defaults baseline, PnL=$39k / DD=$7.9k
- `sweeps/01_thresholds_gap.py` — Phase 1: `min_gap=8` chosen (best PnL before trade-count collapses)
- `sweeps/02_risk_geometry.py` — Phase 2: `sl_lookback=15` is the lever (+$15k PnL, ‑$2k DD)
- `sweeps/03_combo_geometry.py` — Phase 3: stack `rr_tp=3.0`+`sl_max=50`, then module triage
- `sweeps/04_combo_filters.py` — Phase 4: `ut_on=False`+`sig_extreme_filter_on=True`+`hw_extreme=15` (P/DD 14.05)
- `sweeps/05_indicator_lengths.py` — Phase 5: indicator length sweep; `stc_*` and `ema_*` dominate
- `sweeps/06_combo_indicators.py` — Phase 6: combine indicator winners; `stc_length=10`+`stc_fast_len=32` best
- `sweeps/07_hour_analysis.py` — hour-of-day & DoW bucket analysis on the Phase 6 winner
- `sweeps/08_blackouts.py` — Phase 8: first DD-valid configs (BO 13-14 + 17-21, DD=$2,273)
- `sweeps/09_risk_finetune.py` — risk sweep across the top blackout candidates; `risk=0.60%` is the sweet spot
- `sweeps/10_final_combo.py` — risk × blackout refinement → **$56,353 / $2,425** (winner)
- `build_winner_preset.py` — build the UI-format preset, insert into `data/presets.json`
- `winner_preset.json` — standalone copy of the winner
- `verify_preset.py` — replay + compare; prints `✅ MATCH`
- `logs/*.log` — captured output of every sweep
- `REPORT.md` — detailed analysis & lever-by-lever attribution

## The winner config in one block

```python
# Strategy params (overrides on top of MomentumChecker.default_params)
{
    "min_gap":               8,
    "sl_lookback":           15,
    "rr_tp":                 3.0,
    "sl_max_points":         50.0,
    "ut_on":                 False,
    "sig_extreme_filter_on": True,
    "hw_extreme":            15.0,
    "stc_length":            10,
    "stc_fast_len":          32,
}

# Engine
risk_per_trade  = 0.6 %
max_contracts   = 20
auto_close      = 22:00 (CME close, reference Brussels)
blackouts       = 12:30-14:00, 17:00-21:00, 22:00-23:59  (all active)
daily limits    = OFF  (per user instruction)
```
