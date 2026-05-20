"""Phase 9 — Blackout sensitivity sweep.

The strategy's structural DD wall (~$3.2k after combo) needs blackout help to
get under the user's $2.5k hard ceiling. Strategy:

  1. Hour-bucket analysis on the best combo trades — find lossy hours.
  2. Hour-bucket WITHOUT any blackouts — see global pattern.
  3. Sweep alternative blackout configurations.

Best combo so far ([B+C+D+E, sl_max=100]):
  PnL=$59,655 / DD=$3,168 / N=807 / WR=39.4% / PF=1.53
V1 MGC blackouts: 12:30-14:00, 17:00-21:00, 22-23:59
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.analysis import bucket_by_hour, print_hour_table, bucket_by_dow, print_dow_table  # noqa: E402
from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402

from _campaign import (  # noqa: E402
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    build_engine,
)


# Best combo from Phase 6
BEST_COMBO = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,       # B
    "hma_window_bars":  5,       # B
    "max_candle_pct":   0.3,     # C
    "ema_sec_len":      5,       # D
    "be_at_rr":         2.0,     # E
    "sl_max_points":    100.0,   # A variant — top of P6
}


def _common(engine):
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
    )


def _engine_no_blackouts():
    """Only the 22-23:59 close lock (always required)."""
    return build_engine([(22, 0, 23, 59)])


def _engine_v1_blackouts():
    """V1 MGC blackouts."""
    return build_engine([(12, 30, 14, 0), (17, 0, 21, 0), (22, 0, 23, 59)])


def hour_bucket_pass(label, engine, params):
    """Run, summarize, and print hour bucket of the trades."""
    r = run_backtest(strategy_params=params, **_common(engine))
    s = summarize(r)
    print(f"\n{label}")
    print(fmt_summary(s))
    print()
    print("Hour bucket (entry hour, Brussels time):")
    by_hour = bucket_by_hour(r["trades"])
    print_hour_table(by_hour)
    return by_hour


def main() -> int:
    print("=" * 110)
    print(f"PHASE 9 — Blackouts  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Best combo (current blackouts): PnL=$59,655  $DD=$3,168")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # ---- 1) Hour-bucket diagnostics ----
    print("\n=== 1) Hour-bucket: Best combo with V1 blackouts ===")
    hour_bucket_pass("[Best combo + V1 blackouts]",
                     _engine_v1_blackouts(), BEST_COMBO); n += 1

    print("\n=== 2) Hour-bucket: Best combo with NO blackouts (only 22-23:59 close lock) ===")
    hour_bucket_pass("[Best combo + no blackouts]",
                     _engine_no_blackouts(), BEST_COMBO); n += 1

    # ---- 2) Test sweep over alternative blackout configurations ----
    print("\n" + "=" * 110)
    print("=== 3) Blackout configuration sweep ===")
    print("=" * 110)

    # Define candidate blackout configs
    configs = [
        ("V1_anchor", [(12, 30, 14, 0), (17, 0, 21, 0)]),  # +22-23:59 auto-added
        ("Just_close",  []),
        # Single-window experiments
        ("12-14",   [(12, 0, 14, 0)]),
        ("12-14:30", [(12, 0, 14, 30)]),
        ("13-14",   [(13, 0, 14, 0)]),
        ("17-21",   [(17, 0, 21, 0)]),
        ("17-22",   [(17, 0, 22, 0)]),
        ("16-22",   [(16, 0, 22, 0)]),
        ("16:30-22", [(16, 30, 22, 0)]),
        # Combinations: keep one of the V1 windows, drop the other
        ("only_lunch",    [(12, 30, 14, 0)]),
        ("only_evening",  [(17, 0, 21, 0)]),
        # V1 windows but shifted
        ("V1_12-14",      [(12, 0, 14, 0), (17, 0, 21, 0)]),
        ("V1_12-14:30",   [(12, 0, 14, 30), (17, 0, 21, 0)]),
        ("V1_12:30-14:30", [(12, 30, 14, 30), (17, 0, 21, 0)]),
        ("V1_17-22",      [(12, 30, 14, 0), (17, 0, 22, 0)]),
        ("V1_16-22",      [(12, 30, 14, 0), (16, 0, 22, 0)]),
        ("V1_16:30-22",   [(12, 30, 14, 0), (16, 30, 22, 0)]),
        ("V1_widened",    [(12, 0, 14, 30), (16, 30, 22, 0)]),
        # Add Asia early blackout (some strategies have lossy 00-02)
        ("V1+early",      [(0, 0, 2, 0), (12, 30, 14, 0), (17, 0, 21, 0)]),
        ("V1+morning",    [(8, 0, 10, 0), (12, 30, 14, 0), (17, 0, 21, 0)]),
        ("V1+morning2",   [(9, 0, 10, 0), (12, 30, 14, 0), (17, 0, 21, 0)]),
        # MNQ-style
        ("MNQ_style",     [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]),
        # Wider afternoon
        ("V1_14-21",      [(12, 30, 14, 0), (14, 0, 21, 0)]),
        ("V1_15-21",      [(12, 30, 14, 0), (15, 0, 21, 0)]),
        ("V1_15:30-21",   [(12, 30, 14, 0), (15, 30, 21, 0)]),
    ]

    results = []
    for lab, windows in configs:
        engine = build_engine(windows + [(22, 0, 23, 59)])  # always close-lock
        s = bench(f"[{lab}]", strategy_params=BEST_COMBO, **_common(engine))
        results.append((lab, s, windows))
        n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")

    # Print sorted summary
    print("\n" + "=" * 110)
    print("=== RANKED RESULTS (by PnL, then DD) ===")
    print("=" * 110)
    print(f"{'Config':<22}{'PnL':>10}{'DD':>8}{'WR':>7}{'PF':>6}{'N':>5}")
    valid = [r for r in results if r[1]["max_dd_$"] <= 2_500]
    over = [r for r in results if r[1]["max_dd_$"] > 2_500]
    print("\nValid (DD ≤ $2,500):")
    for lab, s, w in sorted(valid, key=lambda x: (-x[1]["net_pnl"], x[1]["max_dd_$"])):
        print(f"{lab:<22}{s['net_pnl']:>10,.0f}{s['max_dd_$']:>8,.0f}{s['win_rate']:>6.1f}%{s['profit_factor']:>6}{s['trades']:>5}")
    print("\nOver ceiling ($2,500):")
    for lab, s, w in sorted(over, key=lambda x: x[1]["max_dd_$"]):
        print(f"{lab:<22}{s['net_pnl']:>10,.0f}{s['max_dd_$']:>8,.0f}{s['win_rate']:>6.1f}%{s['profit_factor']:>6}{s['trades']:>5}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
