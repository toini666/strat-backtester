"""Phase 6 (v2) — Stack the small wins from P1-P5.

Single-lever winners (Pareto or near-Pareto):
  P1:  pts_hma_slow=1 ssl=80 hw=5  →  P/DD=25.46  ($69,349/$2,724)
  P3:  tick_buffer=2               →  P/DD=25.04  ($70,770/$2,826)
  P3:  sl_max_points=50            →  P/DD=24.26  ($67,704/$2,791)
  P5:  amp_mult=3.5                →  P/DD=24.89  ($72,163/$2,900) — best PnL
  P5:  stc_slow_len=65             →  P/DD=25.92  ($69,234/$2,671) — best P/DD
  P5:  st_atr=10                   →  P/DD=25.49  ($70,635/$2,771)
  P5:  ut_atr_period=7             →  P/DD=25.44  ($68,905/$2,709)

Cross-stack these wins to see if effects compound.
"""

from __future__ import annotations

import sys
import time
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, anchor_engine,
)


# Stack-able levers
STACK = {
    "amp_mult":        [3.0, 3.5, 4.0],
    "sl_max_points":   [50.0, 60.0, 75.0],
    "tick_buffer":     [0, 2],
    "stc_slow_len":    [50, 65, 80],
    "st_atr":          [10, 14],
    "ut_atr_period":   [7, 10],
}
# 3*3*2*3*2*2 = 216 — too many. Use a Plackett-Burman-style sample of corner combos
# instead of full factorial.

# Picked subset: pivot each "stack" lever individually to see joint effect
# (full lattice of all=216 too expensive). Use 3 amp × 3 sl_max × small grid.


def _common(risk=RISK_PER_TRADE):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=anchor_engine(),
    )


def _override(**kw):
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 6 (v2) — Stack small wins")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[B baseline]", s))

    # ---- A: amp_mult × sl_max_points (core 2-way) ----
    print("\n--- A: amp_mult × sl_max ---")
    for amp, sl in product([3.0, 3.5, 4.0], [40.0, 50.0, 60.0, 75.0, 100.0]):
        params = {"amp_mult": amp, "sl_max_points": sl}
        if amp == 3.0 and sl == 60.0:
            continue  # baseline
        label = f"A amp={amp} sl={sl}"
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ---- B: amp=3.5 (P5 winner) + small DD reducers ----
    print("\n--- B: amp=3.5 + DD-reducer stack ---")
    base_b = {"amp_mult": 3.5}
    OPTS = {
        "tick_buffer":     [1, 2],
        "stc_slow_len":    [65, 80],
        "st_atr":          [7, 10],
        "ut_atr_period":   [7],
        "pts_sig_extreme": [2],  # P4: slight DD reducer
    }
    # individual augmentations to amp=3.5
    for k, vals in OPTS.items():
        for v in vals:
            params = {**base_b, k: v}
            label = f"B amp=3.5 +{k}={v}"
            s = bench(label, strategy_params=_override(**params), **_common())
            results.append((label, s))

    # ---- C: amp=3.5 + multi-lever stacks (2-3 levers at once) ----
    print("\n--- C: amp=3.5 + pairs of DD reducers ---")
    pairs = [
        {"tick_buffer": 2, "stc_slow_len": 65},
        {"tick_buffer": 2, "st_atr": 10},
        {"tick_buffer": 2, "ut_atr_period": 7},
        {"stc_slow_len": 65, "st_atr": 10},
        {"stc_slow_len": 65, "ut_atr_period": 7},
        {"st_atr": 10, "ut_atr_period": 7},
        {"tick_buffer": 2, "stc_slow_len": 65, "st_atr": 10},
        {"tick_buffer": 2, "stc_slow_len": 65, "ut_atr_period": 7},
        {"tick_buffer": 2, "st_atr": 10, "ut_atr_period": 7},
        {"stc_slow_len": 65, "st_atr": 10, "ut_atr_period": 7},
        {"tick_buffer": 2, "stc_slow_len": 65, "st_atr": 10, "ut_atr_period": 7},
    ]
    for kv in pairs:
        params = {**base_b, **kv}
        label = "C amp=3.5 +" + " +".join(f"{k}={v}" for k, v in kv.items())
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ---- D: pts_hma_slow combo (P1's small winner) ----
    print("\n--- D: amp=3.5 + pts_hma_slow + sl_max variants ---")
    for ssl_len in [60, 80]:
        for hw_bars in [5]:
            for sl in [50.0, 60.0, 75.0]:
                params = {**base_b,
                          "pts_hma_slow": 1, "ssl_len": ssl_len, "hma_window_bars": hw_bars,
                          "sl_max_points": sl}
                label = f"D amp=3.5 +hma_slow ssl={ssl_len} hw={hw_bars} sl={sl}"
                s = bench(label, strategy_params=_override(**params), **_common())
                results.append((label, s))

    # ---- E: be_at_rr Pareto path (DD < $2k targeting) ----
    print("\n--- E: be_at_rr Pareto search (DD<$2k path) ---")
    for be in [1.0, 1.25, 1.5, 1.75]:
        for sl in [50.0, 60.0, 75.0]:
            params = {**base_b, "be_at_rr": be, "sl_max_points": sl}
            label = f"E amp=3.5 be={be} sl={sl}"
            s = bench(label, strategy_params=_override(**params), **_common())
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(3074, "V1 ceiling"), (2500, "moderate"), (2000, "target")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 20 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
            print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("Pareto frontier")
    print("=" * 110)
    buckets = [(0, 1500), (1500, 1700), (1700, 1900), (1900, 2100), (2100, 2300),
               (2300, 2500), (2500, 2700), (2700, 2900), (2900, 3074)]
    for lo, hi in buckets:
        configs_in = [(l, s) for l, s in results if lo < s["max_dd_$"] <= hi]
        if configs_in:
            best = max(configs_in, key=lambda x: x[1]["net_pnl"])
            l, s = best
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  PnL=${s['net_pnl']:>7,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")
        else:
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  (no configs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
