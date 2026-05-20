"""Phase 9 (v2) — Blackout sensitivity on Combo_amp35_full.

Top 2 finalists from P8:
  W_MAX: Combo_amp35_full @ 0.62% → $76,060 / $3,036
  W_SUB2K: Combo_amp35_full @ 0.44% → $47,623 / $1,971

V1's anchor blackouts (re-tested optimal in v1 phase 8): 09-10, 13-14, 17-23:59.
Re-test on Combo_amp35_full to confirm they're still optimal with this stack.
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
    START, STRATEGY, SYMBOL, build_engine,
)


COMBO_FULL = dict(BASELINE_PARAMS)
COMBO_FULL.update({
    "amp_mult": 3.5,
    "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5,
    "st_atr": 10,
    "tick_buffer": 2,
})

ANCHOR_WINDOWS = [(9, 0, 10, 0), (13, 0, 14, 0), (17, 0, 23, 59)]


def _common(engine, risk):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
        strategy_params=COMBO_FULL,
    )


def main() -> int:
    print("=" * 110)
    print("PHASE 9 (v2) — Blackouts on Combo_amp35_full")
    print("=" * 110)

    results = []
    t0 = time.time()

    # Baselines
    print("\n--- Baselines ---")
    s = bench("[W_MAX 0.62% V1 windows]", **_common(build_engine(ANCHOR_WINDOWS), 0.0062))
    results.append(("[W_MAX 0.62% V1 windows]", s))
    s = bench("[W_SUB2K 0.44% V1 windows]", **_common(build_engine(ANCHOR_WINDOWS), 0.0044))
    results.append(("[W_SUB2K 0.44% V1 windows]", s))

    # Drop-one tests on W_MAX (0.62%)
    print("\n--- W_MAX drop-one ---")
    for i, w in enumerate(ANCHOR_WINDOWS):
        wins = [x for j, x in enumerate(ANCHOR_WINDOWS) if j != i]
        label = f"W_MAX drop {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins), 0.0062))
        results.append((label, s))

    # Add candidates on W_MAX
    print("\n--- W_MAX add candidate ---")
    EXTRA = [
        (11, 0, 13, 0),
        (12, 30, 14, 0),
        (15, 30, 16, 30),
        (16, 30, 17, 0),
    ]
    for w in EXTRA:
        wins = ANCHOR_WINDOWS + [w]
        label = f"W_MAX add {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins), 0.0062))
        results.append((label, s))

    # Window swaps on W_MAX
    print("\n--- W_MAX swap window ---")
    SWAPS = {
        (9, 0, 10, 0):  [(8, 30, 10, 0), (9, 0, 10, 30)],
        (13, 0, 14, 0): [(13, 0, 14, 30), (13, 30, 14, 30)],
        (17, 0, 23, 59):[(16, 30, 23, 59), (17, 30, 23, 59)],
    }
    for orig, candidates in SWAPS.items():
        for cand in candidates:
            others = [w for w in ANCHOR_WINDOWS if w != orig]
            wins = others + [cand]
            label = f"W_MAX swap {orig[0]:02d}-{orig[2]:02d}h → {cand[0]:02d}:{cand[1]:02d}-{cand[2]:02d}:{cand[3]:02d}"
            s = bench(label, **_common(build_engine(wins), 0.0062))
            results.append((label, s))

    # Quick drop-one on W_SUB2K
    print("\n--- W_SUB2K drop-one ---")
    for i, w in enumerate(ANCHOR_WINDOWS):
        wins = [x for j, x in enumerate(ANCHOR_WINDOWS) if j != i]
        label = f"W_SUB2K drop {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d}"
        s = bench(label, **_common(build_engine(wins), 0.0044))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 110)
    print("TOP 20 W_MAX-band (DD ≤ $3,074) by PnL")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 3074.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 W_SUB2K-band (DD ≤ $2,000) by PnL")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
