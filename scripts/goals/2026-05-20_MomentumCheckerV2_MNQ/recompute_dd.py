"""Compute the TRUE max dollar drawdown from the equity curve.

The simulator's `max_drawdown_dollars` is anchored to the moment of max %
drawdown — not the max $ drawdown. When PnL grows large, the % and $ maxima
diverge. This recomputes both for V1 anchor and V2 winner.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest  # noqa: E402

from _campaign import (  # noqa: E402
    ANCHOR_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS, START,
    STRATEGY, SYMBOL, anchor_engine,
)


WINNER = dict(ANCHOR_PARAMS)
WINNER.update({
    "amp_mult": 3.0, "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True, "sig_extreme": 40.0,
    "hma_pol_bars": 20, "be_at_rr": 1.25, "sl_max_points": 60.0,
})


def true_dd(eq_curve):
    """Return (max_$_DD, max_%_DD, $_at_%_max, peak_ts_$, trough_ts_$)."""
    peak = eq_curve[0]["value"]
    peak_ts = eq_curve[0]["time"]
    max_dollar = 0.0
    max_pct = 0.0
    dollar_at_pct_max = 0.0
    peak_ts_at_dollar_max = peak_ts
    trough_ts_at_dollar_max = peak_ts
    cur_peak_ts = peak_ts
    cur_peak = peak
    for p in eq_curve:
        v = p["value"]
        if v > peak:
            peak = v
            cur_peak = v
            cur_peak_ts = p["time"]
        dollar_dd = peak - v
        pct_dd = dollar_dd / peak if peak > 0 else 0
        if dollar_dd > max_dollar:
            max_dollar = dollar_dd
            peak_ts_at_dollar_max = cur_peak_ts
            trough_ts_at_dollar_max = p["time"]
        if pct_dd > max_pct:
            max_pct = pct_dd
            dollar_at_pct_max = dollar_dd
    return max_dollar, max_pct, dollar_at_pct_max, peak_ts_at_dollar_max, trough_ts_at_dollar_max


def run(strat, params, label, risk):
    r = run_backtest(
        strategy_name=strat, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
        strategy_params=params,
    )
    md, mp, dp, pt, tt = true_dd(r["equity_curve"])
    net_pnl = sum(t["pnl"] for t in r["trades"] if not t.get("excluded", False))
    print(f"\n=== {label} ===")
    print(f"  PnL=${net_pnl:,.2f}  ({len([t for t in r['trades'] if not t.get('excluded', False)])} trades)")
    print(f"  Simulator reports:    DD=${r['metrics']['max_drawdown_dollars']:,.2f}  ({r['metrics']['max_drawdown']:.2f}%)")
    print(f"  TRUE worst $ DD:      ${md:,.2f}  ({md/INITIAL_EQUITY*100:.2f}% of initial equity)")
    print(f"  TRUE worst % DD:      {mp*100:.2f}%  (${dp:,.2f} at that moment)")
    print(f"  $-DD window: peak {pt} → trough {tt}")


def main() -> int:
    # V1 anchor (V2 with V1-compat translation)
    run(STRATEGY, ANCHOR_PARAMS, "V1 anchor (V2-compat)", 0.0060)
    # V2 winner
    run(STRATEGY, WINNER, "V2 winner", 0.0070)

    # Also check a lower-risk variant of the V2 winner — does dropping risk
    # bring the TRUE $ DD under target?
    for r_pc in (0.0060, 0.0055, 0.0050, 0.0045, 0.0040):
        run(STRATEGY, WINNER, f"V2 winner @ risk={r_pc*100:.2f}%", r_pc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
