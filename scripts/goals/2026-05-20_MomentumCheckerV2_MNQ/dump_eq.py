"""Dump raw equity_curve values to understand the DD discrepancy."""

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


def main() -> int:
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=0.0070,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
        strategy_params=WINNER,
    )
    eq = r["equity_curve"]
    print(f"equity_curve length: {len(eq)}")
    print(f"first 3 entries: {eq[:3]}")
    print(f"last 3 entries: {eq[-3:]}")
    print(f"min value: {min(p['value'] for p in eq):,.2f}")
    print(f"max value: {max(p['value'] for p in eq):,.2f}")
    print(f"initial equity expected: ${INITIAL_EQUITY:,.0f}")
    print(f"reported metrics: PnL=${r['metrics']['total_return']/100*INITIAL_EQUITY:.2f}, "
          f"DD$={r['metrics']['max_drawdown_dollars']:.2f}, "
          f"DD%={r['metrics']['max_drawdown']:.2f}")

    # Sum trade PnL
    active = [t for t in r["trades"] if not t.get("excluded", False)]
    net_pnl = sum(t["pnl"] for t in active)
    print(f"\nsum trade pnl: ${net_pnl:,.2f}")
    print(f"final equity from sum: ${INITIAL_EQUITY + net_pnl:,.2f}")
    print(f"final equity from eq_curve: ${eq[-1]['value']:,.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
