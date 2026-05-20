"""Phase 7 — Per-module point weights on the Phase 6 winner.

Phase 6 winner: PnL=$43,665, DD=$3,420, P/DD=12.77.
Stack: gap9, rr2.5, tickBuf0, hw_ext=ON, rob=off, hw_extreme=20,
       mf_smooth=5, st_atr=14, ema_sec_len=20, amp_mult=2.5.

Goal: find pts_* tweaks that upweight high-quality signals or zero noise.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


WINNER = dict(BASELINE_PARAMS)
WINNER["min_gap"] = 9
WINNER["rr_tp"] = 2.5
WINNER["tick_buffer"] = 0
WINNER["hw_extreme_filter_on"] = True
WINNER["rob_on"] = False
WINNER["hw_extreme"] = 20.0
WINNER["mf_smooth"] = 5
WINNER["st_atr"] = 14
WINNER["ema_sec_len"] = 20
WINNER["amp_mult"] = 2.5


PTS_SWEEPS = {
    # Oscillator (6 components)
    "pts_hw_sens":      [0, 1, 2, 3],
    "pts_hw_value":     [0, 1, 2],
    "pts_hw_extreme":   [0, 1, 2],
    "pts_sig_extreme":  [0, 1, 2],
    "pts_cloud":        [0, 1, 2],
    "pts_delta":        [0, 1, 2],
    # EMA
    "pts_ema_break":    [0, 1, 2, 3],
    "pts_ema_align":    [0, 1, 2],
    # Supertrend
    "pts_st":           [0, 1, 2, 3],
    # Alligator
    "pts_alligator":    [0, 1, 2, 3],
    "pts_alli_offset":  [0, 1, 2],
    "pts_retest_lips":  [0, 1, 2],
    # UT bot
    "pts_ut_bot":       [0, 1, 2, 3],
    # Rob (off, so should be ignored — skip)
    # STC
    "pts_stc":          [0, 1, 2],
    # HMA
    "pts_hma_break":    [0, 1, 2, 3],
}


def _common():
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=baseline_engine(),
    )


def _ovr(**kw):
    p = dict(WINNER)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 7 — Point weights on Phase 6 winner")
    print("=" * 100)

    t0 = time.time()
    results = []
    base = bench("Phase-6 winner", strategy_params=WINNER, **_common())
    base_pdd = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"Base P/DD = {base_pdd:.2f}")
    results.append(("(=base)", base))

    best_by_param: dict = {}

    for param, values in PTS_SWEEPS.items():
        baseline_val = WINNER.get(param)
        print()
        print("-" * 100)
        print(f"SWEEP {param}  (winner baseline = {baseline_val})")
        param_results = []
        for v in values:
            if v == baseline_val:
                # avoid re-running baseline for every param
                s = base
                label = f"{param}={v} (=base)"
            else:
                label = f"{param}={v}"
                s = bench(label, strategy_params=_ovr(**{param: v}), **_common())
                results.append((label, s))
            param_results.append((v, s, label))
        valid = [(v, s) for v, s, _ in param_results if s["max_dd_$"] <= 5000]
        if valid:
            bv, bs = max(valid, key=lambda x: x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))
            best_by_param[param] = (bv, bs)

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} new sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("Best pts value per component (DD≤$5k, sorted by P/DD)")
    print("=" * 100)
    for p, (v, s) in sorted(best_by_param.items(), key=lambda x: -x[1][1]["net_pnl"] / max(x[1][1]["max_dd_$"], 1.0)):
        change = " (=base)" if v == WINNER.get(p) else f" (was {WINNER.get(p)})"
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  {p:<22}  best={v}{change:<14}  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}")

    print()
    print("=" * 100)
    print("Top 15 by P/DD")
    print("=" * 100)
    for l, s in sorted(results + [("(=base)", base)], key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 100)
    print("Top 15 by PnL")
    print("=" * 100)
    for l, s in sorted(results + [("(=base)", base)], key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
