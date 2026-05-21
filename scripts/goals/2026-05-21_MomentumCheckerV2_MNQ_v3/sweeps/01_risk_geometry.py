"""Phase 1 (v3) — Risk-geometry sweeps (DD is the binding constraint).

be_at_rr is the single most direct DD lever (move SL→entry at given RR).
Was disabled in v2 winner because the buggy DD metric made it look misleading.
With patched metric, deserves a real combined sweep with rr_tp.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, SEED_PNL, SEED_DD, seed_engine,
)


def _common():
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS, engine_settings=seed_engine(),
    )


def _override(**kw):
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 1 (v3) — Risk-geometry | seed = v2 WINNER")
    print(f"Seed metrics: PnL=${SEED_PNL:,.0f} / $DD=${SEED_DD:,.0f}")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[seed]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[seed]", s))

    # ---------- be_at_rr × rr_tp grid ----------
    print("\n--- be_at_rr × rr_tp grid ---")
    for rr in [2.0, 2.5, 3.0]:
        for be in [0.0, 0.5, 0.75, 1.0, 1.25, 1.5]:
            if be == 0.0 and rr == 2.5:
                continue  # seed
            label = f"be_at_rr={be}  rr_tp={rr}"
            s = bench(label, strategy_params=_override(be_at_rr=be, rr_tp=rr), **_common())
            results.append((label, s))

    # ---------- sl_max_points × tick_buffer ----------
    print("\n--- sl_max_points × tick_buffer ---")
    for sl_max in [40.0, 50.0, 60.0, 70.0, 80.0, 100.0]:
        for tb in [0, 1, 2, 3, 4]:
            if sl_max == 60.0 and tb == 2:
                continue  # seed
            label = f"sl_max={sl_max:.0f}  tb={tb}"
            s = bench(label, strategy_params=_override(sl_max_points=sl_max, tick_buffer=tb),
                      **_common())
            results.append((label, s))

    # ---------- sl_lookback ----------
    print("\n--- sl_lookback ---")
    for lb in [3, 4, 5, 7, 10]:
        if lb == 5:
            continue
        label = f"sl_lookback={lb}"
        s = bench(label, strategy_params=_override(sl_lookback=lb), **_common())
        results.append((label, s))

    # ---------- rr_tp standalone (extras) ----------
    print("\n--- rr_tp standalone (be off) ---")
    for rr in [1.5, 1.75, 2.0, 2.25, 2.75, 3.0, 3.5]:
        if rr == 2.5:
            continue
        label = f"rr_tp={rr}  be=off"
        s = bench(label, strategy_params=_override(rr_tp=rr), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    # ---- Top by PnL filtered by DD cap ----
    for cap, lbl in [(3023, "seed DD"), (2500, "user hard cap"), (2000, "stretch")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 15 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
                  f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    # ---- Top by P/DD ratio overall ----
    print()
    print("=" * 110)
    print("TOP 15 by P/DD ratio (any DD)")
    print("=" * 110)
    valid_pos = [(l, s) for l, s in results if s["net_pnl"] > 0 and s["max_dd_$"] > 0]
    for l, s in sorted(valid_pos, key=lambda x: -x[1]["net_pnl"]/x[1]["max_dd_$"])[:15]:
        print(f"  P/DD={s['net_pnl']/s['max_dd_$']:>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
