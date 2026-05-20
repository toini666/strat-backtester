"""Phase 1 (v2) — V2-new features around B combo baseline.

B baseline: PnL=$71,371 / $DD=$2,900 / N=781

Now that the simulator's $DD is correct, re-test each V2-new feature:
  be_at_rr, hma_pol_bars, pts_hma_slow combos, cloud_zero, delta_off_mode,
  sig_extreme variants.

Previously: be_at_rr was thought to be a major DD-reducer, but that was
measured against the buggy %-anchored $DD. Re-check the real story.
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
    BASELINE_PARAMS,
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
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 1 (v2) — V2-new features  |  patched $DD  |  B baseline")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[B baseline]", s))

    # ---- be_at_rr ----
    print("\n--- be_at_rr (B has 0.0) ---")
    for v in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
        label = f"be_at_rr={v}"
        s = bench(label, strategy_params=_override(be_at_rr=v), **_common())
        results.append((label, s))

    # ---- hma_pol_bars ----
    print("\n--- hma_pol_bars (B has -1) ---")
    for v in [0, 3, 5, 8, 12, 20, 30]:
        label = f"hma_pol_bars={v}"
        s = bench(label, strategy_params=_override(hma_pol_bars=v), **_common())
        results.append((label, s))

    # ---- pts_hma_slow with ssl variations ----
    print("\n--- pts_hma_slow=1 × ssl_len × window_bars ---")
    for ssl_len in [40, 60, 80]:
        for hw_bars in [3, 5]:
            label = f"pts_hma_slow=1 ssl={ssl_len} hw={hw_bars}"
            s = bench(label, strategy_params=_override(
                pts_hma_slow=1, ssl_len=ssl_len, hma_window_bars=hw_bars,
            ), **_common())
            results.append((label, s))

    # ---- delta_off_mode ----
    print("\n--- delta_off_mode (B has 'both') ---")
    for m in ["counter_trend"]:
        label = f"delta_off_mode={m}"
        s = bench(label, strategy_params=_override(delta_off_mode=m), **_common())
        results.append((label, s))

    # ---- cloud_zero (likely bad, just confirm) ----
    print("\n--- cloud_zero_filter_on=True (B has False) ---")
    label = "cloud_zero_pts=1"
    s = bench(label, strategy_params=_override(
        cloud_zero_filter_on=True, pts_cloud_zero=1,
    ), **_common())
    results.append((label, s))

    # ---- sig_extreme variants (B has 40) ----
    print("\n--- sig_extreme variants (B has 40.0) ---")
    for v in [15.0, 20.0, 25.0, 30.0, 35.0, 50.0, 60.0]:
        label = f"sig_extreme={v}"
        s = bench(label, strategy_params=_override(sig_extreme=v), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    # Reporting
    print()
    print("=" * 110)
    print("TOP 20 by PnL with $DD ≤ $3,074 (V1 ceiling)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 3074.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by PnL with $DD ≤ $2,500")
    print("=" * 110)
    valid2 = [(l, s) for l, s in results if s["max_dd_$"] <= 2500.0]
    for l, s in sorted(valid2, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by P/DD")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"]/max(x[1]["max_dd_$"], 1.0))[:20]:
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
