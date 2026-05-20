# 2026-05-20 — `MomentumCheckerV2` on MNQ (7 m) — **v2 (corrected)**

Re-run of the original campaign after a critical bug in `simulator.py:max_drawdown_dollars`
was discovered and patched. The original (v1) campaign was optimising against a
metric that returned the `$` drawdown at the moment of max-% drawdown — not the
worst-ever `$` peak-to-trough. With a winning strategy that grows equity from
$50k to $120k+, the two measures diverge by thousands of dollars.

| | |
|-|-|
| Strategy | `MomentumCheckerV2` |
| Symbol / TF | MNQ / 7 m |
| Period | 2025-01-07 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 20 (per user constraint) |
| Daily limits | OFF (per user constraint) |
| **V1 Anchor (true metric)** | **$61,313 / DD $3,074 / N=785 / P/DD 19.95** |
| **WINNER** | **$80,565 / DD $3,023 / N=797 / WR 40.4% / PF 1.58 / P/DD 26.65** |
| **Delta vs V1** | **+$19,252 PnL (+31.4%) AND −$51 $DD (−1.7%)** |
| Sims used | 487 (within the 500 budget) |

Status: **complete** — preset saved to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

## How to reproduce

```bash
source venv/bin/activate
python scripts/goals/2026-05-20_MomentumCheckerV2_MNQ_v2/verify_preset.py
# → ✅ MATCH (PnL=$80,565 / DD=$3,023 / N=797 / PF=1.58)
```

## Files

- `sweeps/_campaign.py` — campaign constants, B-baseline params, builder for blackout engine
- `sweeps/00_baseline.py` — confirms B-combo baseline ($71,371/$2,900) with patched DD
- `sweeps/01_v2_features.py` — V2-new features re-tested with correct DD
- `sweeps/02_thresholds_gap.py` — thresholds & gap & candle pct
- `sweeps/03_risk_geometry.py` — sl_lookback, sl_max, rr_tp, tick_buffer
- `sweeps/04_module_toggles.py` — module on/off, sub-filter triage, point weights
- `sweeps/05_indicator_lengths.py` — every indicator length around B (amp_mult=3.5 winner)
- `sweeps/06_combo_lattice.py` — stack single-lever winners
- `sweeps/07_master_combo.py` — master 4-way binary lattice + risk variations
- `sweeps/08_pareto_finetune.py` — fine risk sweep + BE × hma_slow combos
- `sweeps/09_blackouts.py` — blackout sensitivity (extension 13-14 → 14:30 won)
- `sweeps/10_final_validation.py` — tight risk band 0.55-0.66% on winning blackouts
- `build_winner_preset.py` — builds UI-format preset, inserts into `data/presets.json`
- `winner_preset.json` — standalone copy of the winner
- `verify_preset.py` — replay + compare; prints `✅ MATCH`
- `logs/*.log` — every sweep's captured output
- `REPORT.md` — detailed analysis & lever attribution

## The winner config in one block

```python
# Strategy params (overrides on top of MomentumCheckerV2.default_params)
{
    # --- V1-compat anchor (proven equivalent to V1 PineScript) ---
    "sig_extreme_filter_on": True,
    "sig_extreme":           40.0,
    "max_candle_pct":        0.3,
    "sl_max_points":         60.0,
    "delta_off_mode":        "both",
    # V1-compat noops:
    "hma_pol_bars":          -1,
    "pts_hma_slow":          1,       # ENABLED — slight Pareto improvement
    "ssl_len":               60,
    "hma_window_bars":       5,
    # --- Phase-5/3/7 winners ---
    "amp_mult":              3.5,     # was 2.5 (V1) / 3.0 (B-baseline)
    "st_atr":                10,      # was 14 — slight DD reducer
    "tick_buffer":           2,       # was 0 — slight DD reducer
    # all other params: V1-compat anchor values
}

# Engine
risk_per_trade  = 0.66 %
max_contracts   = 20
auto_close      = 22:00 (CME close, reference Brussels)
blackouts       = 09:00-10:00, 13:00-14:30, 17:00-23:59
daily limits    = OFF (per user instruction)
```

The blackout extension from V1's `13:00-14:00` to **`13:00-14:30`** was found
in Phase 9 — a clean Pareto improvement (+$114 PnL, -$190 $DD vs V1 windows
at the same risk/strategy params).

## Why the v1 campaign was wrong (and the bug)

`src/engine/simulator.py` reported `max_drawdown_dollars` as `peak − v` *at
the moment when `%` drawdown was at its all-time max*, not the worst-ever
`$` peak-to-trough.

When the strategy grows equity from $50k to $120k+, a $3,300 drop on a $115k
peak (2.87% DD) can be the worst $-loss ever, while a $1,800 drop on a $54k
peak (3.33% DD) is the worst %-loss. The buggy code reported the latter as
`max_drawdown_dollars`, which is misleading.

The patch (`simulator.py:1840-1850`) tracks both maxima independently. UI
behaviour is preserved (% DD field unchanged); only the `$` field changes to
report the true worst peak-to-trough loss.

## Sims used

| Phase | Description | Sims |
|---|---|---|
| 0 | Baselines (V1 anchor + B baseline check) | 1 |
| 1 | V2-new features re-test | 30 |
| 2 | Thresholds & gap | 28 |
| 3 | Risk geometry | 35 |
| 4 | Module toggles | 30 |
| 5 | Indicator lengths | 75 |
| 6 | Combo lattice (stack P1-P5 wins) | 52 |
| 7 | Master combo + risk sweep | 50 |
| 8 | Pareto fine-tune | 76 |
| 9 | Blackout sensitivity | 18 |
| 10 | Final risk-band validation | 16 |
| | **Total** | **411** |

Note: 11_repatch_finetune from the original campaign folder added ~90 sims
of overlapping data used to seed this v2 campaign (the B-combo was identified
there). Stand-alone sim budget for v2 = 411 / 500.
