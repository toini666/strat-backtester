"""Phase 2 (v3) — HMA canal V3-inspired exploration.

User pointed at: take inspiration from HMASSLOsciV3 MNQ 7m winner which uses
much shorter HMA lengths (hma1=13, hma2=21, amp=2.0, pol_bars=0, ssl_len=80)
vs MCV2 baseline (42, 84, 3.5, -1, 60).

Anchor for this phase: P1 best = sl_max=40, tb=2 (PnL=$86,619 / $DD=$2,933)
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine,
)

# P1-locked anchor for downstream phases
P1_ANCHOR = dict(BASELINE_PARAMS)
P1_ANCHOR.update({"sl_max_points": 40.0, "tick_buffer": 2})


def _common():
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS, engine_settings=seed_engine(),
    )


def _override(**kw):
    p = dict(P1_ANCHOR)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 2 (v3) — HMA canal V3-inspired | anchor = P1 best (sl_max=40, tb=2)")
    print("Anchor target: PnL=$86,619 / $DD=$2,933")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[P1 anchor]", strategy_params=P1_ANCHOR, **_common())
    results.append(("[P1 anchor]", s))

    # -------- 2.1: (hma1, hma2) × amp_mult sparse grid -----------
    print("\n--- (hma1, hma2) × amp_mult sparse grid ---")
    hma_pairs = [(13, 21), (13, 42), (21, 42), (21, 63), (32, 63), (42, 84), (55, 105), (70, 130)]
    for h1, h2 in hma_pairs:
        for amp in [1.5, 2.0, 2.5, 3.0, 3.5]:
            if (h1, h2, amp) == (42, 84, 3.5):
                continue  # anchor
            label = f"hma=({h1},{h2}) amp={amp}"
            s = bench(label, strategy_params=_override(hma1_len=h1, hma2_len=h2,
                                                       amp_mult=amp), **_common())
            results.append((label, s))

    # -------- 2.2: hma_pol_bars sweep at anchor + V3 short anchor ----
    print("\n--- hma_pol_bars sweep (at anchor and at V3 short-anchor) ---")
    for h1, h2, amp in [(42, 84, 3.5), (13, 21, 2.0)]:
        for pol in [-1, 0, 2, 3, 5, 8]:
            if (h1, h2, amp, pol) == (42, 84, 3.5, -1):
                continue  # anchor
            label = f"hma=({h1},{h2}) amp={amp} pol={pol}"
            s = bench(label, strategy_params=_override(hma1_len=h1, hma2_len=h2,
                                                       amp_mult=amp, hma_pol_bars=pol),
                      **_common())
            results.append((label, s))

    # -------- 2.3: ssl_len × ssl_mult sweep at anchor -----------
    print("\n--- ssl_len × ssl_mult ---")
    for ssl_l in [40, 60, 80, 100]:
        for ssl_m in [0.1, 0.2, 0.3, 0.4]:
            if (ssl_l, ssl_m) == (60, 0.2):
                continue
            label = f"ssl=({ssl_l},{ssl_m})"
            s = bench(label, strategy_params=_override(ssl_len=ssl_l, ssl_mult=ssl_m),
                      **_common())
            results.append((label, s))

    # -------- 2.4: hma_window_bars × hma_ema_len -----------
    print("\n--- hma_window_bars × hma_ema_len ---")
    for win in [0, 2, 3, 5, 8, 12]:
        for ema_l in [3, 5, 7, 10]:
            if (win, ema_l) == (5, 7):
                continue
            label = f"win={win} ema_l={ema_l}"
            s = bench(label, strategy_params=_override(hma_window_bars=win,
                                                       hma_ema_len=ema_l), **_common())
            results.append((label, s))

    # -------- 2.5: short-HMA combo with V3-style stack ----------
    print("\n--- V3-style short-HMA stacks ---")
    v3_stacks = [
        {"hma1_len": 13, "hma2_len": 21, "amp_mult": 2.0, "hma_pol_bars": 0, "ssl_len": 80, "hma_window_bars": 5},
        {"hma1_len": 13, "hma2_len": 21, "amp_mult": 2.0, "hma_pol_bars": 3, "ssl_len": 80, "hma_window_bars": 5},
        {"hma1_len": 13, "hma2_len": 21, "amp_mult": 1.5, "hma_pol_bars": 0, "ssl_len": 80, "hma_window_bars": 8},
        {"hma1_len": 21, "hma2_len": 42, "amp_mult": 2.0, "hma_pol_bars": 0, "ssl_len": 80, "hma_window_bars": 5},
        {"hma1_len": 21, "hma2_len": 42, "amp_mult": 2.5, "hma_pol_bars": 3, "ssl_len": 80, "hma_window_bars": 5},
        {"hma1_len": 32, "hma2_len": 63, "amp_mult": 2.5, "hma_pol_bars": 0, "ssl_len": 80, "hma_window_bars": 5},
        {"hma1_len": 32, "hma2_len": 63, "amp_mult": 3.0, "hma_pol_bars": -1, "ssl_len": 60, "hma_window_bars": 5},
    ]
    for stack in v3_stacks:
        label = "V3:" + " ".join(f"{k.replace('_len','').replace('hma_','h')}={v}" for k, v in stack.items())
        s = bench(label, strategy_params=_override(**stack), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    # Reports
    print()
    print("=" * 110)
    print(f"TOP 20 by PnL with $DD ≤ $2,933 (P1 anchor DD)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2933]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
              f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print(f"TOP 15 with $DD ≤ $2,500 (HARD CAP)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    if not valid:
        print("  (no candidates yet)")
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
              f"N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by P/DD ratio")
    print("=" * 110)
    valid_pos = [(l, s) for l, s in results if s["net_pnl"] > 0 and s["max_dd_$"] > 0]
    for l, s in sorted(valid_pos, key=lambda x: -x[1]["net_pnl"]/x[1]["max_dd_$"])[:20]:
        print(f"  P/DD={s['net_pnl']/s['max_dd_$']:>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
