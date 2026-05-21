"""Phase 11 — HMASSLOsciV3-inspired HMA params on MGC.

User-requested follow-up: test the V3 MGC winner HMA stack
(hma1=9, hma2=34, amp_mult=2.0, hma_pol_bars=3, ssl_len=60) inside
MomentumCheckerV2 + variants around it.

Anchor: the v2 WINNER config (mcp=0.25, +BO 15:30-17, r=0.55%, sl_max=100).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, build_engine,
)


# WINNER engine (v2 final)
WINNER_BO = [
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]
WINNER_RISK = 0.0055


def winner_anchor_params():
    """Returns the v2 WINNER param set (seed + mcp=0.25)."""
    p = dict(BASELINE_PARAMS)
    p["max_candle_pct"] = 0.25
    return p


def run(label, overrides, risk=WINNER_RISK):
    params = winner_anchor_params()
    params.update(overrides)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=build_engine(WINNER_BO),
    )
    s = summarize(r)
    tag = ""
    # v2 WINNER = $58,625 / $2,434
    if s["max_dd_$"] < 2000 and s["net_pnl"] >= 50_000:
        tag = " ⭐ DD<$2k"
    elif s["max_dd_$"] < 2500 and s["net_pnl"] > 58_625:
        tag = " 🏆 PnL>v2W"
    elif s["max_dd_$"] < 2434 and s["net_pnl"] > 55_000:
        tag = " 💎 lowerDD"
    print(f"{label:<75s} {fmt_summary(s)}{tag}")
    return s


def main() -> int:
    print("=" * 110)
    print("PHASE 11 — HMA V3-inspired params on MGC (anchor = v2 WINNER)")
    print("=" * 110)
    print(f"Baseline: v2 WINNER → PnL=$58,625 / DD=$2,434")
    print()

    # --- 11A: drop-in V3 MGC HMA stack ---
    print("--- 11A: V3 MGC HMA stack drop-in ---")
    run("V3 drop-in (hma1=9, hma2=34, pol_bars=3)",
        {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": 3})

    # --- 11B: hma1/hma2 grid around V3 values ---
    print("\n--- 11B: hma1 × hma2 grid (V3-style short lengths) ---")
    for h1 in [7, 9, 11, 13, 17, 21]:
        for h2 in [21, 28, 34, 42, 50]:
            run(f"hma1={h1:>2} hma2={h2:>2} pol=3",
                {"hma1_len": h1, "hma2_len": h2, "hma_pol_bars": 3})

    # --- 11C: hma_pol_bars sweep at V3 lengths ---
    print("\n--- 11C: hma_pol_bars at hma1=9, hma2=34 ---")
    for pol in [-1, 0, 1, 2, 3, 5, 8]:
        run(f"hma1=9 hma2=34 pol_bars={pol}",
            {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": pol})

    # --- 11D: amp_mult variations at V3 lengths ---
    print("\n--- 11D: amp_mult at hma1=9, hma2=34, pol=3 ---")
    for amp in [1.0, 1.5, 2.0, 2.5, 3.0]:
        run(f"hma1=9 hma2=34 pol=3 amp={amp}",
            {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": 3, "amp_mult": amp})

    # --- 11E: hma_ema_len at V3 lengths (MCV2-specific param) ---
    print("\n--- 11E: hma_ema_len at hma1=9, hma2=34, pol=3 ---")
    for hem in [3, 5, 7, 9, 12]:
        run(f"hma_ema_len={hem}",
            {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": 3, "hma_ema_len": hem})

    # --- 11F: ssl_len at V3 lengths ---
    print("\n--- 11F: ssl_len at hma1=9, hma2=34, pol=3 ---")
    for sl in [30, 40, 50, 60, 80, 100]:
        run(f"ssl_len={sl}",
            {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": 3, "ssl_len": sl})

    # --- 11G: hma_window_bars at V3 lengths ---
    print("\n--- 11G: hma_window_bars at hma1=9, hma2=34, pol=3 ---")
    for hwb in [3, 5, 7, 10, 15]:
        run(f"hma_window_bars={hwb}",
            {"hma1_len": 9, "hma2_len": 34, "hma_pol_bars": 3, "hma_window_bars": hwb})

    return 0


if __name__ == "__main__":
    sys.exit(main())
