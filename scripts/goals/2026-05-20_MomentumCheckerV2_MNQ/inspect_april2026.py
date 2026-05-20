"""Dump the V2 winner's trades + running equity in the 2026-04-20 → 2026-05-01
window, to investigate whether reported max_dd_$ matches the worst stretch
the user spots in the UI.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    ANCHOR_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
)


WINNER = dict(ANCHOR_PARAMS)
WINNER.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
    "be_at_rr": 1.25,
    "sl_max_points": 60.0,
})


def main() -> int:
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=0.0070,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
        strategy_params=WINNER,
    )
    s = summarize(r)
    print(fmt_summary(s))
    print(f"\nReported max_drawdown_$: ${r['metrics']['max_drawdown_dollars']:,.2f}")
    print(f"Reported max_drawdown_%: {r['metrics']['max_drawdown']:.2f}%")

    # ----- Compute peak/trough on equity curve to find the worst DD window -----
    eq = r["equity_curve"]
    peak = eq[0]["value"]
    peak_ts = eq[0]["time"]
    worst_dd = 0.0
    worst_peak_ts = peak_ts
    worst_trough_ts = peak_ts
    worst_peak_v = peak
    worst_trough_v = peak
    cur_peak_ts = peak_ts
    cur_peak_v = peak
    for p in eq:
        v = p["value"]
        ts = p["time"]
        if v > peak:
            peak = v
            peak_ts = ts
            cur_peak_v = v
            cur_peak_ts = ts
        dd = peak - v
        if dd > worst_dd:
            worst_dd = dd
            worst_peak_ts = cur_peak_ts
            worst_peak_v = cur_peak_v
            worst_trough_ts = ts
            worst_trough_v = v

    print(f"\nWORST DD WINDOW:")
    print(f"  Peak   : ${worst_peak_v:>10,.2f} at {worst_peak_ts}")
    print(f"  Trough : ${worst_trough_v:>10,.2f} at {worst_trough_ts}")
    print(f"  DD     : ${worst_dd:>10,.2f}  ({(worst_dd/worst_peak_v)*100:.2f}%)")

    # ----- Show trades on 2026-04-23 and 2026-04-24 -----
    trades = r["trades"]
    print(f"\nTOTAL TRADES = {len(trades)} (excluded={sum(1 for t in trades if t.get('excluded',False))})")
    active = [t for t in trades if not t.get("excluded", False)]
    apr_trades = [t for t in active
                  if t["entry_time"][:10] in ("2026-04-22", "2026-04-23", "2026-04-24", "2026-04-25", "2026-04-26", "2026-04-27", "2026-04-28")]
    print(f"\nTrades 2026-04-22 to 2026-04-28 ({len(apr_trades)} total):")
    print(f"  {'entry':<19} {'exit':<19} {'side':<6} {'entry_p':<10} {'exit_p':<10} {'ctr':<4} {'pnl':>10} {'cum':>12}")
    running_eq = INITIAL_EQUITY
    for t in active:
        running_eq += t["pnl"]
        if t["entry_time"][:10] in ("2026-04-22", "2026-04-23", "2026-04-24", "2026-04-25",
                                     "2026-04-26", "2026-04-27", "2026-04-28"):
            side = "Long" if t["side"] == "long" else "Short"
            print(f"  {t['entry_time'][:19]:<19} {t['exit_time'][:19]:<19} "
                  f"{side:<6} {t['entry_price']:<10.2f} {t['exit_price']:<10.2f} "
                  f"{t.get('contracts','?'):<4} {t['pnl']:>10.2f}  ${running_eq:>10,.2f}")

    # ----- Show running equity at end of each date in April 2026 -----
    print("\nEnd-of-day equity April 2026 (active trades only):")
    daily_pnl: dict[str, float] = {}
    for t in active:
        d = t["entry_time"][:10]
        if d.startswith("2026-04") or d.startswith("2026-05"):
            daily_pnl.setdefault(d, 0.0)
            daily_pnl[d] += t["pnl"]

    cum = INITIAL_EQUITY
    cum_peak = INITIAL_EQUITY
    cum_max_dd = 0.0
    for d in sorted(daily_pnl):
        cum += daily_pnl[d]
        if cum > cum_peak:
            cum_peak = cum
        dd = cum_peak - cum
        if dd > cum_max_dd:
            cum_max_dd = dd
        flag = "  ◄ NEW DD" if dd >= cum_max_dd else ""
        print(f"  {d}  daily_pnl=${daily_pnl[d]:>+8,.2f}  cum=${cum:>12,.2f}  peak=${cum_peak:>12,.2f}  dd=${dd:>8,.2f}{flag}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
