"""Phase 1 — Sweep V2-new features in isolation.

Anchor (V2 V1-compat on V1 engine): PnL=$61,313 / DD=$2,143 / N=785.

V2 adds:
  1. be_at_rr           — break-even @ RR (0 disables; V1: off)
  2. hma_pol_bars       — HMA-canal polarity tolerance window
  3. pts_hma_slow       — score bonus for HMA-slow / SSL cross (with ssl_len,
                          ssl_mult, hma_window_bars)
  4. cloud_zero_filter_on + pts_cloud_zero — MFI sign filter
  5. delta_off_mode     — V1 "both" vs V2 "counter_trend"
  6. sig_extreme separate from hw_extreme — independent threshold

Each lever is swept in isolation around the anchor. Results help us pick the
1-2 strongest V2 levers to layer into the combo sweep.
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
    print(f"PHASE 1 — V2-new features sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    s = bench("[anchor] V1-compat", strategy_params=ANCHOR_PARAMS, **_common())
    results.append(("[anchor] V1-compat", s))

    # ---- Lever 1: break-even @ RR ----
    print()
    print("-" * 110 + "\nLever 1: be_at_rr (break-even @ RR; V1=0.0 off)")
    for v in [0.3, 0.5, 0.7, 1.0, 1.25, 1.5, 1.75, 2.0]:
        label = f"be_at_rr={v}"
        s = bench(label, strategy_params=_override(be_at_rr=v), **_common())
        results.append((label, s))

    # ---- Lever 2: HMA polarity tolerance bars ----
    print()
    print("-" * 110 + "\nLever 2: hma_pol_bars (HMA-canal polarity tolerance; V1=-1 strict)")
    for v in [0, 1, 2, 3, 5, 8, 12, 20]:
        label = f"hma_pol_bars={v}"
        s = bench(label, strategy_params=_override(hma_pol_bars=v), **_common())
        results.append((label, s))

    # ---- Lever 3: HMA-slow / SSL cross bucket ----
    print()
    print("-" * 110 + "\nLever 3: pts_hma_slow=1 with various window/SSL combos (V1 had pts=0)")
    for ssl_len in [40, 60, 80]:
        for hw_bars in [3, 5, 8]:
            label = f"pts_hma_slow=1 ssl_len={ssl_len} hw_bars={hw_bars}"
            s = bench(label, strategy_params=_override(
                pts_hma_slow=1, ssl_len=ssl_len, hma_window_bars=hw_bars,
            ), **_common())
            results.append((label, s))

    # ---- Lever 4: cloud-zero MFI sign filter ----
    print()
    print("-" * 110 + "\nLever 4: cloud_zero_filter_on=True with pts_cloud_zero (V1 had it off)")
    for pts in [1, 2]:
        label = f"cloud_zero pts={pts}"
        s = bench(label, strategy_params=_override(
            cloud_zero_filter_on=True, pts_cloud_zero=pts,
        ), **_common())
        results.append((label, s))

    # ---- Lever 5: delta_off_mode ----
    print()
    print("-" * 110 + "\nLever 5: delta_off_mode (V1='both', V2-native='counter_trend')")
    for mode in ["counter_trend"]:
        label = f"delta_off_mode={mode}"
        s = bench(label, strategy_params=_override(delta_off_mode=mode), **_common())
        results.append((label, s))

    # ---- Lever 6: sig_extreme — split from hw_extreme ----
    print()
    print("-" * 110 + "\nLever 6: sig_extreme separate threshold (V1 anchor=1e9, i.e. effectively neutral filter passing)")
    # First TRUE sig_extreme filter at various tighter thresholds
    for v in [10.0, 15.0, 20.0, 25.0, 30.0, 40.0]:
        label = f"sig_extreme={v}"
        s = bench(label, strategy_params=_override(
            sig_extreme_filter_on=True, sig_extreme=v,
        ), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    # ----------------------------------------------------------------
    # Rankings
    # ----------------------------------------------------------------
    print()
    print("=" * 110)
    print("TOP 15 by PnL (DD ≤ $2,143 = V1 anchor DD)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={p_dd:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by P/DD ratio (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={p_dd:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by absolute PnL (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={p_dd:.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
