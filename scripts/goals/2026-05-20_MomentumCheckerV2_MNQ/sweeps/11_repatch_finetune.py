"""Phase 11 — Re-rank top candidates with PATCHED simulator (correct $DD).

After the simulator's `max_drawdown_dollars` bug was fixed:
  V1 anchor TRUE $DD = $3,074  (was reported as $2,143 — wrong)

Goals on the corrected metric:
  Hard: $DD ≤ $3,074  (V1's true DD)
  Soft: $DD < $2,000

Test top-N strategy configs at multiple risk levels and pick the new Pareto
winner. Strategy logic is unchanged — equity curves and trade lists are the
same — only the metric reporting was wrong.
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
    ANCHOR_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS, START,
    STRATEGY, SYMBOL, anchor_engine,
)


# Top configs from phase 6/7 (all with V1-compat anchor base + overrides)
CONFIGS = {
    # The V1 anchor itself — baseline
    "V1_anchor": {},

    # Phase 6 A-base (best strict-DD with V2 simulator metric)
    "A_amp3_can5_sig40_pol20": {
        "amp_mult": 3.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20,
    },
    "A_amp4_can5_sig40_pol20": {
        "amp_mult": 4.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20,
    },

    # Phase 6 D combos — best sub-$2k apparent DD with BE+sl_max
    "D_amp3_be125_sl60": {
        "amp_mult": 3.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20, "be_at_rr": 1.25, "sl_max_points": 60.0,
    },
    "D_amp4_be125_sl60": {
        "amp_mult": 4.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20, "be_at_rr": 1.25, "sl_max_points": 60.0,
    },
    "D_amp4_be125_sl75": {
        "amp_mult": 4.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20, "be_at_rr": 1.25, "sl_max_points": 75.0,
    },

    # B-combos (sl_max=50/60 high PnL)
    "B_amp3_sl60_can3_sig40": {
        "amp_mult": 3.0, "max_candle_pct": 0.3,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "sl_max_points": 60.0,
    },
    "B_amp3_sl50_can3_sig40": {
        "amp_mult": 3.0, "max_candle_pct": 0.3,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "sl_max_points": 50.0,
    },

    # be at lower RR variants
    "D_amp3_be1_sl60": {
        "amp_mult": 3.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20, "be_at_rr": 1.0, "sl_max_points": 60.0,
    },
    "D_amp3_be1_sl70": {
        "amp_mult": 3.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20, "be_at_rr": 1.0, "sl_max_points": 70.0,
    },
}


RISKS = [0.0040, 0.0045, 0.0050, 0.0055, 0.0060, 0.0065, 0.0070, 0.0075, 0.0080]


def _override(cfg):
    p = dict(ANCHOR_PARAMS)
    p.update(cfg)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 11 — Re-rank with patched simulator (correct $DD)")
    print(f"  V1 anchor TRUE $DD = $3,074 (hard ceiling)  / target $DD < $2,000")
    print("=" * 110)

    results = []
    t0 = time.time()

    for cfg_name, cfg in CONFIGS.items():
        for r in RISKS:
            label = f"{cfg_name} risk={r*100:.2f}%"
            s = bench(label,
                strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
                start=START, end=END,
                initial_equity=INITIAL_EQUITY, risk_per_trade=r,
                max_contracts=MAX_CONTRACTS,
                engine_settings=anchor_engine(),
                strategy_params=_override(cfg),
            )
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with TRUE $DD ≤ $3,074 (V1 anchor ceiling)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 3074.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  %DD={s['max_dd_%']:>4.2f}%  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with TRUE $DD ≤ $2,000 (target)")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    if not sub2k:
        print("  (none)")
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  %DD={s['max_dd_%']:>4.2f}%  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by absolute PnL (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("Pareto frontier: best PnL within each $DD bucket")
    print("=" * 110)
    buckets = [(0, 1700), (1700, 2000), (2000, 2200), (2200, 2500), (2500, 2800), (2800, 3074)]
    for lo, hi in buckets:
        configs_in = [(l, s) for l, s in results if lo < s["max_dd_$"] <= hi]
        if configs_in:
            best = max(configs_in, key=lambda x: x[1]["net_pnl"])
            l, s = best
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  ← {l}")
        else:
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  (no configs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
