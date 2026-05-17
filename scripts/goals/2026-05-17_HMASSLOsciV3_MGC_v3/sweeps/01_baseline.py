"""01 — Baseline: replay V2 winner.

Sims used: 1 / 200
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_hour,
    bucket_by_dow,
    print_hour_table,
    print_dow_table,
)
from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402

from _campaign import (  # noqa: E402
    STRATEGY,
    SYMBOL,
    INTERVAL,
    START,
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    V2_WINNER_OVERRIDES,
    V2_WINNER_RISK,
    V2_WINNER_BLACKOUTS,
    pdd,
)


def main() -> None:
    print("=" * 80)
    print("01 — Baseline: replay V2 winner")
    print("=" * 80)

    es = make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in V2_WINNER_BLACKOUTS
        ],
    )

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=V2_WINNER_OVERRIDES,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=V2_WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(
        f"V2 WINNER REPLAY  PnL=${s['net_pnl']:,.0f}  DD=${s['max_dd_$']:,.0f}  "
        f"N={s['trades']}  WR={s['win_rate']}%  PF={s['profit_factor']}  "
        f"P/DD={pdd(s['net_pnl'], s['max_dd_$']):.2f}"
    )

    print()
    print("Expected (from V2 REPORT.md): PnL=$44,711 DD=$2,378 N=1,142 WR=55.9% PF=1.56")

    print()
    print("=" * 80)
    print("Trade buckets on V2 winner — hour")
    print("=" * 80)
    by_h = bucket_by_hour(r["trades"])
    print_hour_table(by_h)

    print()
    print("=" * 80)
    print("Trade buckets on V2 winner — day of week")
    print("=" * 80)
    by_d = bucket_by_dow(r["trades"])
    print_dow_table(by_d)


if __name__ == "__main__":
    main()
