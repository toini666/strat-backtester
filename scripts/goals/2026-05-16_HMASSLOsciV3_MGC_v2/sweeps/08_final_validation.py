"""Sweep 08 — Final validation.

Winner: 5BO (11-12, 06-07, 07-08, 03-04, 09-10) @ risk=0.47%
        → PnL=$44,711 / DD=$2,378 / P/DD=18.80

Re-run winner + 4 close alternatives. Confirms top choice and provides
report-ready comparison.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, pdd, GOAL_PNL, GOAL_DD,
)

V2_BASELINE = dict(PREV_WINNER_OVERRIDES)
V2_BASELINE["block_loss_exit_before_partial"] = True
V2_BASELINE["hma1_len"] = 9
V2_BASELINE["max_sl_points"] = 100.0
V2_BASELINE["tick_buffer"] = 1


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


BO_5_winner = [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(9, 10)]
BO_5_alt = [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(18, 19)]
BO_4 = [w(11, 12), w(6, 7), w(7, 8), w(3, 4)]


def run_one(label, *, risk, blackouts):
    es = make_engine_settings(STRATEGY, extra_active_windows=list(blackouts))
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=V2_BASELINE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    ok = "✅" if s["net_pnl"] >= GOAL_PNL and s["max_dd_$"] <= GOAL_DD else "❌"
    print(f"{ok} {label:<70s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 130)
    print("Sweep 08 — Final validation of WINNER + alternatives")
    print(f"Goal: PnL > ${GOAL_PNL:,.0f} AND DD < ${GOAL_DD:,.0f}")
    print("=" * 130)

    print("\n## Top 5 alternatives")
    run_one("WINNER: 5BO (11+06+07+03+09) @ risk=0.47%", risk=0.0047, blackouts=BO_5_winner)
    run_one("ALT 1: 5BO (11+06+07+03+09) @ risk=0.48%", risk=0.0048, blackouts=BO_5_winner)
    run_one("ALT 2: 5BO (11+06+07+03+09) @ risk=0.43%", risk=0.0043, blackouts=BO_5_winner)
    run_one("ALT 3: 5BO_alt (11+06+07+03+18) @ risk=0.41%", risk=0.0041, blackouts=BO_5_alt)
    run_one("ALT 4: 4BO (11+06+07+03) @ risk=0.37%", risk=0.0037, blackouts=BO_4)
    run_one("ALT 5: 4BO (11+06+07+03) @ risk=0.40%", risk=0.0040, blackouts=BO_4)

    print("\n## Sanity: closest losers (to document margin)")
    run_one("CLOSE FAIL: 5BO @ 0.50%", risk=0.0050, blackouts=BO_5_winner)
    run_one("CLOSE FAIL: 5BO @ 0.46%", risk=0.0046, blackouts=BO_5_winner)

    print("\n## Reference: previous campaign winner (with 3 blackouts)")
    OLD_OVERRIDES = {"hma2_len": 34, "hw_range_on": True}
    OLD_BO = [w(3, 4), w(8, 9), w(11, 12)]
    es = make_engine_settings(STRATEGY, extra_active_windows=OLD_BO)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=OLD_OVERRIDES,
        initial_equity=INITIAL_EQUITY, risk_per_trade=0.0052,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    ok = "✅" if s["net_pnl"] >= GOAL_PNL and s["max_dd_$"] <= GOAL_DD else "❌"
    print(f"{ok} {'PREV WINNER (v1 campaign)':<70s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
