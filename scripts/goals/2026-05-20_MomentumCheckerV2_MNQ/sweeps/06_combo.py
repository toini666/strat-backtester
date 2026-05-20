"""Phase 6 — Combo search.

Anchor: $61,313 / $2,143 / N=785.

Strong single-lever winners (DD ≤ $2,143):
  amp_mult=4.0         → $63,421
  max_candle_pct=0.5   → $63,064
  sig_extreme=40.0     → $62,679
  amp_mult=3.0         → $62,318
  hma_pol_bars=20      → $61,676

Off-budget but big PnL:
  sl_max_points=50.0   → $79,325 / $2,646 (best $-PnL ever seen)
  sl_max_points=75.0   → $68,889 / $2,566
  hma1_len=55          → $55,328 / $2,633

Plan:
  A) Stack the strict-DD winners (no sl_max change) and look for joint best.
  B) Try sl_max_points=50/75 combined with the DD-reducers — does the strict
     budget become attainable when entries are more selective?
  C) Try be_at_rr levels + sl_max=50 — BE caps the worst drawdown leg.
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
    ANCHOR_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
)


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
        engine_settings=anchor_engine(),
    )


def _override(**kw):
    p = dict(ANCHOR_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 6 — Combo search  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    s = bench("[anchor]", strategy_params=ANCHOR_PARAMS, **_common())
    results.append(("[anchor]", s))

    # ------------------------------------------------------------------
    # A) Strict-DD winner combos (no sl_max_points changes)
    # ------------------------------------------------------------------
    print("\n=== A) strict-DD winner combos ===")
    A_GRID = {
        "amp_mult":         [2.5, 3.0, 4.0],
        "max_candle_pct":   [0.4, 0.5],
        "sig_extreme":      [1e9, 25.0, 30.0, 40.0],   # 1e9 = effectively off
        "hma_pol_bars":     [-1, 5, 20],
    }
    keys_A = list(A_GRID.keys())
    for combo in product(*A_GRID.values()):
        params = dict(zip(keys_A, combo))
        if all(params[k] == ANCHOR_PARAMS[k] for k in keys_A):
            continue  # already done as anchor
        # sig_extreme>=1e8 means filter is effectively passive
        sig_on = True
        label = "A " + " ".join(f"{k}={v}" for k, v in params.items())
        s = bench(label, strategy_params=_override(
            amp_mult=params["amp_mult"],
            max_candle_pct=params["max_candle_pct"],
            sig_extreme_filter_on=sig_on,
            sig_extreme=params["sig_extreme"],
            hma_pol_bars=params["hma_pol_bars"],
        ), **_common())
        results.append((label, s))

    # ------------------------------------------------------------------
    # B) sl_max_points combined with DD-reducers
    # ------------------------------------------------------------------
    print("\n=== B) sl_max_points × DD-reducers ===")
    B_GRID = {
        "sl_max_points":   [40.0, 50.0, 60.0, 75.0, 90.0],
        "amp_mult":        [3.0, 4.0],
        "max_candle_pct":  [0.3, 0.4, 0.5],
        "sig_extreme":     [25.0, 40.0],
    }
    keys_B = list(B_GRID.keys())
    for combo in product(*B_GRID.values()):
        params = dict(zip(keys_B, combo))
        label = "B " + " ".join(f"{k}={v}" for k, v in params.items())
        s = bench(label, strategy_params=_override(
            sl_max_points=params["sl_max_points"],
            amp_mult=params["amp_mult"],
            max_candle_pct=params["max_candle_pct"],
            sig_extreme_filter_on=True,
            sig_extreme=params["sig_extreme"],
        ), **_common())
        results.append((label, s))

    # ------------------------------------------------------------------
    # C) be_at_rr to cap losing-leg DD on the big-PnL setups
    # ------------------------------------------------------------------
    print("\n=== C) be_at_rr × sl_max_points combos ===")
    C_GRID = {
        "be_at_rr":       [0.0, 0.5, 0.75, 1.0, 1.25, 1.5],
        "sl_max_points":  [40.0, 50.0, 75.0],
        "amp_mult":       [4.0],   # stick with the winning amp_mult
    }
    keys_C = list(C_GRID.keys())
    for combo in product(*C_GRID.values()):
        params = dict(zip(keys_C, combo))
        label = "C " + " ".join(f"{k}={v}" for k, v in params.items())
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ------------------------------------------------------------------
    # D) Cross-stack the top 5 combos of A with sl_max_points + be_at_rr
    # ------------------------------------------------------------------
    print("\n=== D) top-strict-DD stack with sl_max + be ===")
    D_BASE = {
        "amp_mult": 4.0, "max_candle_pct": 0.5,
        "sig_extreme_filter_on": True, "sig_extreme": 40.0,
        "hma_pol_bars": 20,
    }
    D_GRID = {
        "sl_max_points": [40.0, 50.0, 60.0, 75.0, 100.0],
        "be_at_rr":      [0.0, 0.5, 0.75, 1.0, 1.25],
    }
    for combo in product(*D_GRID.values()):
        params = dict(zip(D_GRID.keys(), combo))
        merged = dict(D_BASE)
        merged.update(params)
        label = "D " + " ".join(f"{k}={v}" for k, v in merged.items()
                                  if k not in ("sig_extreme_filter_on",))
        s = bench(label, strategy_params=_override(**merged), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 30 by PnL with DD ≤ $2,143 (strict anchor budget)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:30]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 30 by PnL with DD ≤ $2,000 (target!)")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    if not sub2k:
        print("  (none under $2,000)")
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:30]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 30 by P/DD ratio (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"]/max(x[1]["max_dd_$"], 1.0))[:30]:
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 30 by absolute PnL")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:30]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
