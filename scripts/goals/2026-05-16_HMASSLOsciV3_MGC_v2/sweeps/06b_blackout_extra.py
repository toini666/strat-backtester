"""Sweep 06b — Extended blackout search.

Best from 06: BO=11-12 + BO=06-07 → PnL=$43,443 / DD=$3,817 / P/DD=11.38

Test additional anchor combos with this duo. Some hours may paradoxically lower DD
even with positive avg PnL (cf. previous campaign's H=17 paradox in reverse).
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)

V2_BASELINE = dict(PREV_WINNER_OVERRIDES)
V2_BASELINE["block_loss_exit_before_partial"] = True
V2_BASELINE["hma1_len"] = 9
V2_BASELINE["max_sl_points"] = 100.0
V2_BASELINE["tick_buffer"] = 1


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


def run_one(label, extra_windows):
    es = make_engine_settings(STRATEGY, extra_active_windows=list(extra_windows))
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=V2_BASELINE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=PREV_WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    print(f"{label:<60s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 110)
    print("Sweep 06b — Extra blackouts on (BO=11-12 + BO=06-07) anchor")
    print("=" * 110)
    anchor = [w(11, 12), w(6, 7)]
    run_one("ANCHOR (11-12 + 06-07)", anchor)
    print("-" * 110)

    # Add each individual hour
    print("\n## ANCHOR + single extra")
    for hour in range(0, 22):
        if hour in (6, 11):
            continue
        # 1h-wide blackout
        run_one(f"ANCHOR + BO={hour:02d}-{hour+1:02d}", anchor + [w(hour, hour + 1)])
