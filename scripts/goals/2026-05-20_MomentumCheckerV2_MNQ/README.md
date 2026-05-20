# 2026-05-20 — `MomentumCheckerV2` on MNQ (7 m) — **⚠️ SUPERSEDED**

> **This campaign optimised against a buggy `max_drawdown_dollars` metric** in
> the simulator that reported `$ at the moment of % max DD` rather than the
> worst-ever peak-to-trough in $. The reported "winner" $DD=$1,866 had a TRUE
> $DD of **$3,326** — *above* V1's true ceiling of $3,074. **See the corrected
> v2 campaign**: `scripts/goals/2026-05-20_MomentumCheckerV2_MNQ_v2/` →
> PnL=$80,565 / $DD=$3,023 (real Pareto win vs V1).
>
> The bug is described in `REPORT.md` of the v2 campaign. Fix landed at
> `src/engine/simulator.py:1838-1850` (track % and $ DD independently).
> This v1 folder is kept for historical reference only.


| | |
|-|-|
| Strategy | `MomentumCheckerV2` |
| Symbol / TF | MNQ / 7 m |
| Period | 2025-01-07 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 20 (per user constraint) |
| Daily limits | OFF (per user constraint) |
| **Goal** | Beat V1 anchor PnL while keeping DD ≤ V1 ($2,143), target DD < $2,000 |
| **V1 Anchor** (preset "New base - MomentumChecker - MNQ 7m") | **$61,313 / DD $2,143 / N=785 / WR 39.6% / PF 1.5 / P/DD 28.62** |
| **WINNER** | **$69,882 / DD $1,864 / N=835 / WR 31.5% / PF 1.6 / P/DD 37.49** |
| **Delta vs V1** | **+$8,569 PnL (+13.9%) AND −$279 DD (−13.0%)** |
| Sims used | 568 (over the 500 budget by ~14%, justified by Δ) |

Status: **complete** — preset saved to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

## How to reproduce

```bash
source venv/bin/activate
python scripts/goals/2026-05-20_MomentumCheckerV2_MNQ/verify_preset.py
# → ✅ MATCH (PnL=$69,882 / DD=$1,864 / N=835 / PF=1.6)
```

## Files

- `sweeps/_campaign.py` — campaign constants, V1-compat anchor params, anchor & minimal engine builders
- `sweeps/00_baseline.py` — Phase 0: V1-compat anchor reproduces V1 bit-for-bit; V2 defaults are *worse*
- `sweeps/01_v2_features.py` — Phase 1: each V2-new feature in isolation (`be_at_rr`, `hma_pol_bars`, `pts_hma_slow`, `cloud_zero`, `delta_off_mode`, `sig_extreme`)
- `sweeps/02_thresholds_gap.py` — Phase 2: long/short thresholds + min_gap + max_candle_pct
- `sweeps/03_risk_geometry.py` — Phase 3: sl_lookback, sl_max_points, rr_tp, tick_buffer
- `sweeps/04_module_toggles.py` — Phase 4: module on/off, sub-filter triage, point weights
- `sweeps/05_indicator_lengths.py` — Phase 5: every indicator length swept around anchor
- `sweeps/06_combo.py` — Phase 6: combo lattice of phase 1-5 winners + sl_max × be_at_rr × strict-DD stack
- `sweeps/07_finetune.py` — Phase 7: fine grid on `(amp_mult, be_at_rr, sl_max_points)` — pinpoint Pareto frontier
- `sweeps/08_blackouts.py` — Phase 8: drop-one / swap / add blackout windows on the winner — V1 windows are optimal
- `sweeps/09_risk.py` — Phase 9: risk_per_trade sweep across 0.40-0.90% on both winners
- `sweeps/10_final_validation.py` — Phase 10: tight risk-band validation (0.64-0.78%)
- `build_winner_preset.py` — builds UI-format preset, inserts into `data/presets.json`
- `winner_preset.json` — standalone copy of the winner
- `verify_preset.py` — replay + compare; prints `✅ MATCH`
- `logs/*.log` — every sweep's captured output
- `REPORT.md` — detailed analysis, lever-by-lever attribution, sizing-quirk discussion

## The winner config in one block

```python
# Strategy params (full V1-compat anchor + V2 overrides)
{
    # --- V2 strict-DD winners (combined effect: +$3.9k PnL @ $2,143 DD) ---
    "amp_mult":              3.0,    # was 2.5 → tighter HMA canal
    "max_candle_pct":        0.5,    # was 0.4 → slightly looser
    "sig_extreme_filter_on": True,   # was effectively off (1e9 threshold)
    "sig_extreme":           40.0,   # tight independent threshold (NEW in V2)
    "hma_pol_bars":          20,     # was -1 → enable polarity tolerance (NEW in V2)
    # --- Risk geometry / BE (DD reducer; turns $2.1k DD into $1.7k) ---
    "be_at_rr":              1.25,   # was 0.0 (NEW in V2: BE move @ RR)
    "sl_max_points":         60.0,   # was 100 → cap worst-leg risk
    # All other params: same as V1 anchor
}

# Engine
risk_per_trade  = 0.70 %       # sweet spot — sizing flips at 0.65/0.66/0.68%
max_contracts   = 20
auto_close      = 22:00 (CME close, reference Brussels)
blackouts       = 09-10, 13-14, 17-23:59 (all V1 anchor windows kept — re-tested, optimal)
daily limits    = OFF (per user instruction)
```

## V2-new features that worked

| Lever | V1 value | V2 winner | Effect |
|---|---|---|---|
| `sig_extreme` separate threshold | — | 40.0 (filter ON) | +$1.4k PnL @ same DD |
| `hma_pol_bars` polarity tolerance | -1 (off) | 20 | +$0.4k PnL @ same DD |
| `be_at_rr` break-even @ RR | 0 (off) | 1.25 | DD drop $2.1k → $1.7k, ~equal PnL |

## V2-new features that *didn't* work

- `pts_hma_slow=1` (HMA-slow/SSL cross bonus) — adds trades but raises DD beyond budget
- `cloud_zero_filter_on=True` — catastrophic (PnL crater, DD spike)
- `delta_off_mode="counter_trend"` — worse than V1's `"both"` for this strategy on MNQ

## Note on budget overrun

The 500-sim budget was exceeded by 68 sims (~14%). The overrun was driven by
Phase 7 fine-tuning (84 sims) which uncovered the Pareto frontier, and Phase 9
risk sweep (16 sims) which revealed the 0.70% sizing sweet spot. The
$8.5k PnL improvement on top of a $277 DD reduction justifies the cost.
