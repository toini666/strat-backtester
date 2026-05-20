"""Phase 8 — Blackout window sensitivity on the new winner.

Two candidates from phase 7:
  W_LowDD : amp_mult=3.0 be_at_rr=1.25 sl_max=60 +A overrides
            → $61,474 / DD=$1,657 / N=835
  W_MaxPnL: amp_mult=3.0 +A overrides (no sl_max/be_at_rr)
            → $65,245 / DD=$2,143 / N=770

V1 anchor's active windows:  09-10, 13-14, 17-23:59.

Test each: drop one active window at a time, also try alternative windows
(11-13, 15:30-16:30, 16:30-18:00, 20-21, 21-22). Stop if a swap clearly helps.
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
    build_engine,
)


# Winner low-DD config
W_LOWDD = dict(ANCHOR_PARAMS)
W_LOWDD.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
    "be_at_rr": 1.25,
    "sl_max_points": 60.0,
})

# Winner max-PnL config
W_MAXPNL = dict(ANCHOR_PARAMS)
W_MAXPNL.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
})


# V1 anchor's active windows
ANCHOR_WINDOWS = [(9, 0, 10, 0), (13, 0, 14, 0), (17, 0, 23, 59)]


def _common(engine, params):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
        strategy_params=params,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 8 — Blackout sensitivity  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    # Both winners with anchor windows (baseline)
    sLow = bench("[W_LOWDD anchor windows]", **_common(build_engine(ANCHOR_WINDOWS), W_LOWDD))
    results.append(("[W_LOWDD anchor windows]", sLow))

    sMax = bench("[W_MAXPNL anchor windows]", **_common(build_engine(ANCHOR_WINDOWS), W_MAXPNL))
    results.append(("[W_MAXPNL anchor windows]", sMax))

    # ----- drop-one tests on W_LOWDD -----
    print("\n--- drop-one (W_LOWDD) ---")
    for i, w in enumerate(ANCHOR_WINDOWS):
        wins_minus = [x for j, x in enumerate(ANCHOR_WINDOWS) if j != i]
        label = f"W_LOWDD drop {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins_minus), W_LOWDD))
        results.append((label, s))

    # ----- add alternatives on top of W_LOWDD anchor windows -----
    print("\n--- add candidate window (W_LOWDD) ---")
    EXTRA = [
        (11, 0, 13, 0),   # London/Midday
        (12, 30, 14, 0),  # MGC winner-style
        (15, 30, 16, 30), # opening volatility
        (16, 30, 18, 0),
        (20, 0, 21, 0),
    ]
    for w in EXTRA:
        wins_plus = ANCHOR_WINDOWS + [w]
        label = f"W_LOWDD add {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins_plus), W_LOWDD))
        results.append((label, s))

    # ----- swap-tests on W_LOWDD: try replacing each anchor window with a longer/shorter one -----
    print("\n--- replace 09-10 / 13-14 with wider equivalents (W_LOWDD) ---")
    REPLACE_CANDIDATES = {
        (9, 0, 10, 0): [(8, 30, 10, 30), (9, 0, 11, 0), (8, 0, 10, 0)],
        (13, 0, 14, 0): [(12, 0, 14, 0), (12, 30, 14, 30), (13, 30, 14, 30)],
        (17, 0, 23, 59): [(16, 30, 23, 59), (17, 30, 23, 59), (18, 0, 23, 59), (15, 30, 23, 59)],
    }
    for orig, candidates in REPLACE_CANDIDATES.items():
        for cand in candidates:
            others = [w for w in ANCHOR_WINDOWS if w != orig]
            wins = others + [cand]
            label = f"W_LOWDD swap {orig[0]:02d}:{orig[1]:02d}-{orig[2]:02d}:{orig[3]:02d} → {cand[0]:02d}:{cand[1]:02d}-{cand[2]:02d}:{cand[3]:02d}"
            s = bench(label, **_common(build_engine(wins), W_LOWDD))
            results.append((label, s))

    # ----- same drop/add for W_MAXPNL (smaller set) -----
    print("\n--- drop-one + add candidate (W_MAXPNL) ---")
    for i, w in enumerate(ANCHOR_WINDOWS):
        wins_minus = [x for j, x in enumerate(ANCHOR_WINDOWS) if j != i]
        label = f"W_MAXPNL drop {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins_minus), W_MAXPNL))
        results.append((label, s))

    for w in [(11, 0, 13, 0), (12, 30, 14, 0), (15, 30, 16, 30)]:
        wins_plus = ANCHOR_WINDOWS + [w]
        label = f"W_MAXPNL add {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins_plus), W_MAXPNL))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 30 by PnL with DD ≤ $2,143")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:30]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 30 by PnL with DD ≤ $2,000")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:30]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
