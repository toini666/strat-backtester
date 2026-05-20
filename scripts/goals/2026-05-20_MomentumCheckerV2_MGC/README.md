# 2026-05-20 — `MomentumCheckerV2` on MGC (7 m)

Replication of the campaign approach used for V2 MNQ, applied to MGC.
The V1 MGC preset (`New base MomentumChecker — MGC 7m — WINNER`) had a
*reported* DD of $2,430 but a TRUE peak-to-trough $DD of **$3,708** under
the patched simulator (the reported value was `% × initial_equity` from
the pre-patch bug).

The user's $2,500 hard ceiling is BELOW V1's TRUE DD, so this campaign
had to *tighten* DD, not Pareto-improve from V1.

| | |
|-|-|
| Strategy | `MomentumCheckerV2` |
| Symbol / TF | MGC / 7 m |
| Period | 2025-01-07 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 20 (per user constraint) |
| Daily limits | OFF (per user constraint) |
| **V1 MGC Anchor (true DD)** | **$56,353 / DD $3,708 / N=784 / WR 41.3% / PF 1.49** |
| **WINNER** | **$58,249 / DD $2,486 / N=851 / WR 39.7% / PF 1.54 / P/DD 23.4** |
| **Delta vs V1 anchor** | **+$1,896 PnL (+3.4%) AND −$1,222 $DD (−33%)** |
| Constraint check | ✅ DD ≤ $2,500 (margin $14)   ❌ DD ≤ $2,000 not reachable |
| Sims used | 421 / 500 |

Status: **complete** — preset saved to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

## How to reproduce

```bash
source venv/bin/activate
python scripts/goals/2026-05-20_MomentumCheckerV2_MGC/verify_preset.py
# → ✅ MATCH (PnL=$58,249 / DD=$2,486 / N=851 / PF=1.54)
```

## Files

- `verify_v1_anchor.py` — replays the V1 MGC preset under the patched simulator to record its TRUE $DD ($3,708)
- `sweeps/_campaign.py` — campaign constants + V1-compat baseline params + blackout builder
- `sweeps/00_baseline.py` — V2 V1-compat baseline confirmation
- `sweeps/01_v2_features.py` — V2-new features re-tested (delta_off, hma_pol, pts_hma_slow, be_at_rr, etc.)
- `sweeps/02_thresholds_gap.py` — thresholds, prep, gap, candle filter
- `sweeps/03_risk_geometry.py` — sl_lookback, sl_max_points, rr_tp, tick_buffer
- `sweeps/04_module_toggles.py` — module on/off, sub-filter triage, point-weight perturbations
- `sweeps/05_indicator_lengths.py` — every indicator length around the V1-compat anchor
- `sweeps/06_combo_lattice.py` — stack single-lever winners
- `sweeps/07_master_combo_risk.py` — combo × risk + blackout variations
- `sweeps/08_pareto_finetune.py` — fine risk + sl_max variations + drop-E test
- `sweeps/08b_surgical_blackouts.py` — Hour-bucket-driven surgical blackouts (key finding)
- `sweeps/08c_break_dd_floor.py` — try to break the $2,685 NOBE floor (found WINNER at 0.55%)
- `sweeps/09_blackouts.py` — initial broad blackout sweep
- `sweeps/10_final_validation.py` — fine risk band around 0.55% on WINNER
- `build_winner_preset.py` — builds UI-format preset, inserts into `data/presets.json`
- `winner_preset.json` — standalone copy of the winner
- `verify_preset.py` — replay + compare; prints `✅ MATCH`
- `logs/*.log` — every sweep's captured output
- `REPORT.md` — detailed analysis & lever attribution

## The winner config in one block

```python
# Strategy params (overrides on top of MomentumCheckerV2.default_params)
{
    # --- V1-compat translation (MGC values from V1 preset) ---
    "long_threshold":         5,
    "short_threshold":        5,
    "min_gap":                8,
    "sl_lookback":           15,
    "rr_tp":                  3.0,
    "tick_buffer":            2,
    "mf_smooth":              6,
    "hw_extreme_filter_on":   False,
    "sig_extreme_filter_on":  True,
    "sig_extreme":           15.0,    # V1 shared with hw_extreme
    "hw_extreme":            15.0,
    "delta_off_mode":         "both",
    "ema_prin_len":          30,
    "st_atr":                10,
    "stc_length":            10,
    "stc_fast_len":          32,
    "ut_on":                  False,
    "amp_mult":               2.0,
    "hma_pol_bars":          -1,
    # --- Campaign winners ---
    "pts_hma_slow":           1,      # V2 SSL bucket — small Pareto+
    "hma_window_bars":        5,      # window for HMA-slow/SSL cross
    "max_candle_pct":         0.3,    # tightened from V1's 0.4
    "ema_sec_len":            5,      # shortened from V1's 9 (+$724 PnL)
    "be_at_rr":               2.0,    # BE at RR=2.0 — paired w/ surgical BO
    "sl_max_points":        100.0,    # raised from V1 MGC's 50 (smaller contracts → less $ loss/trade)
}

# Engine
risk_per_trade  = 0.55 %
max_contracts   = 20
auto_close      = 22:00 (CME close, reference Brussels)
blackouts       = 12:30-14:00, 18:00-19:00, 20:00-21:00, 22:00-23:59
daily limits    = OFF (per user instruction)
```

The **surgical blackout** (18-19, 20-21) is the campaign's key finding.
V1's broad 17:00-21:00 blackout was over-blocking: hours 17, 19, 21 are
PROFITABLE, while only hours 18 and 20 are net-loss. Cutting 18-19 and
20-21 only keeps the profitable trades while still suppressing the lossy
ones — gaining $1,616 in PnL with $263 less DD vs V1 anchor at the same
risk level.

## Why DD ≤ $2,000 isn't reachable on MGC

The strategy's worst peak-to-trough $-loss is dominated by the worst
consecutive-losing-streak at the **1-contract floor**. At risk levels
0.10%–0.30% the DD stays locked at $2,500 because every losing trade is
1 contract × ~$200–$250 = ~$200–$250. With ~8–10 consecutive losers in
the worst stretch, that's $2,500. No risk reduction breaks this floor
without changing the strategy itself or adding daily limits (which the
user excluded).

The $2,500 floor is reachable across a wide risk band (0.10%–0.30%) but
PnL drops to ~$37–$42k at that point. The selected winner at 0.55% gives
the highest PnL ($58.2k) while still under the $2,500 ceiling ($2,486).

## Sims used

| Phase | Description | Sims |
|---|---|---|
| 0 | V1 anchor + V2 V1-compat baseline | 7 |
| 1 | V2-new features re-test | 20 |
| 2 | Thresholds & gap | 31 |
| 3 | Risk geometry | 37 |
| 4 | Module toggles + point weights | 34 |
| 5 | Indicator lengths | 57 |
| 6 | Combo lattice (stack P1–P5 wins) | 39 |
| 9 | Initial blackout sweep | 27 |
| 7 | Master combo + risk sweep | 40 |
| 8 | Pareto fine-tune | 41 |
| 8b | Surgical blackouts (key finding) | 28 |
| 8c | Break the DD floor (winner found) | 40 |
| 10 | Final validation around winner | 20 |
| | **Total** | **421** |
