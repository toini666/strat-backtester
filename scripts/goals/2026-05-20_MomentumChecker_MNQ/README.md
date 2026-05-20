# 2026-05-20 — `MomentumChecker` on MNQ (7 m)

| | |
|-|-|
| Strategy | `MomentumChecker` |
| Symbol / TF | MNQ / 7 m |
| Period | 2025-01-07 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 50 |
| **Goal** | Maximise PnL with `max_dd_$ < $2,500` (strict). Strategy params first, then blackouts & risk. |
| **Baseline (saved preset)** | -$7,727 PnL / $22,178 DD / 3,220 trades / 35.9 % WR (PF 0.98) — heavy loss |
| **Result** | ✅ **$62,262 PnL / $2,431 DD / 764 trades / 40.1 % WR / PF 1.53** — **+P/DD = 25.6** |
| Sims used | ~360 (≈72 % of 500 budget) |

Status: **complete** — preset shipped to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

## How to reproduce

```bash
source venv/bin/activate
python scripts/goals/2026-05-20_MomentumChecker_MNQ/verify_preset.py
# → ✅ MATCH (PnL=$62,262 / DD=$2,431 / N=764 / PF=1.53)
```

## Files

- `sweeps/_campaign.py` — campaign constants and `baseline_engine()` (matches the user's saved preset)
- `sweeps/00_baseline.py` — Phase 0: reproduce saved preset
- `sweeps/00b_probe.py` / `00c_probe2.py` — diagnostic probes; identified `min_gap` as binding constraint
- `sweeps/01_thresholds_gap.py` — Phase 1: `min_gap=9` is the big lever (+$19k PnL)
- `sweeps/02_risk_geometry.py` — Phase 2: `rr_tp=2.5` adds another +$9k PnL, halves DD
- `sweeps/03_combo_geometry.py` — Phase 3: module triage; `tick_buffer=0`, `hw_extreme_filter_on=ON`, `rob_on=OFF` emerge
- `sweeps/04_combo_filters.py` — Phase 4: stack the filter winners; new champ PnL=$34.8k DD=$3.8k
- `sweeps/05_indicator_lengths.py` — Phase 5: indicator length sweep; `mf_smooth=5`, `st_atr=14`, `amp_mult=2.5`, `ema_sec_len=20` improve PnL/DD
- `sweeps/06_combo_indicators.py` — Phase 6: indicator combo → $43.7k / $3.4k / P/DD=12.8
- `sweeps/07_pts_weights.py` — Phase 7: pts_* sweeps — no improvement (gap is the binding constraint)
- `sweeps/08_hour_analysis.py` — hour-of-day & DoW bucket analysis on the Phase 6 winner
- `sweeps/09_blackouts.py` — Phase 9: blackout sweep → first DD-valid configs at $46k/$2.2k
- `sweeps/10_finetune.py` — risk + daily-limit sweeps
- `sweeps/11_final_combo.py` — final combo → **$62,262 / $2,431** (winner)
- `build_winner_preset.py` — build the UI-format preset, insert into `data/presets.json`
- `winner_preset.json` — standalone copy of the winner
- `verify_preset.py` — replay + compare; prints `✅ MATCH`
- `logs/*.log` — captured output of every sweep
- `REPORT.md` — detailed analysis & lever-by-lever attribution

## The winner config in one block

```python
# Strategy params (overrides on top of MomentumChecker.default_params)
{
    "min_gap":              9,
    "rr_tp":                2.5,
    "tick_buffer":          0,
    "hw_extreme_filter_on": True,
    "hw_extreme":           20.0,
    "rob_on":               False,
    "mf_smooth":            5,
    "st_atr":               14,
    "ema_sec_len":          20,
    "amp_mult":             2.5,
}

# Engine settings
risk_per_trade            = 0.6 %
auto_close_hour           = 22:00 (CME close, reference Brussels)
blackouts                 = 09:00-10:00, 13:00-14:00, 17:00-21:00, 22:00-23:59  (all active)
daily_win_limit           = $800  (after_close)
daily_loss_limit          = $700  (after_close)
```
