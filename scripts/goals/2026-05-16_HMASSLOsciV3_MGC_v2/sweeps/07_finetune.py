"""Sweep 07 — Fine-tune.

Best so far (sweep 04): risk=0.40% gives PnL=$38,238 / DD=$2,449 / P/DD=15.61
                        (both goals met: PnL > 30k AND DD < 2.5k)

Fine grid around 0.36% - 0.42% to find the very best PnL with DD < 2500.
Also re-run a few alt blackout combos at the winning risk to ensure 4-BO combo
is the right one.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd, GOAL_PNL, GOAL_DD,
)

V2_BASELINE = dict(PREV_WINNER_OVERRIDES)
V2_BASELINE["block_loss_exit_before_partial"] = True
V2_BASELINE["hma1_len"] = 9
V2_BASELINE["max_sl_points"] = 100.0
V2_BASELINE["tick_buffer"] = 1


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


WINNER_BO = [w(11, 12), w(6, 7), w(7, 8), w(3, 4)]


def run_one(label, *, params=None, risk=PREV_WINNER_RISK, blackouts=None):
    es = make_engine_settings(STRATEGY, extra_active_windows=list(blackouts if blackouts is not None else WINNER_BO))
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params or V2_BASELINE,
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
    print("Sweep 07 — Fine-tune")
    print(f"Goal: PnL > ${GOAL_PNL:,.0f} AND DD < ${GOAL_DD:,.0f}")
    print("=" * 130)

    print("\n## Fine risk grid around the sweet spot (0.36 - 0.42)")
    for r in (0.0036, 0.0037, 0.0038, 0.0039, 0.0040, 0.0041, 0.0042, 0.0043):
        run_one(f"risk={r*100:.2f}%", risk=r)

    print("\n## Alt blackout combos at risk=0.40%")
    triples = {
        "3BO 11+06+07": [w(11, 12), w(6, 7), w(7, 8)],
        "3BO 11+06+03": [w(11, 12), w(6, 7), w(3, 4)],
        "3BO 11+07+03": [w(11, 12), w(7, 8), w(3, 4)],
        "3BO 11+09+03": [w(11, 12), w(9, 10), w(3, 4)],
        "5BO 11+06+07+03+09": [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(9, 10)],
        "5BO 11+06+07+03+18": [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(18, 19)],
        "5BO 11+06+07+03+16": [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(16, 17)],
    }
    for name, bo in triples.items():
        run_one(name, risk=0.0040, blackouts=bo)

    print("\n## Same alts at risk=0.42% (push PnL up)")
    for name, bo in triples.items():
        run_one(name + " @ 0.42%", risk=0.0042, blackouts=bo)

    print("\n## Winner re-check at multiple risks")
    for r in (0.0030, 0.0035, 0.0040):
        run_one(f"4BO winner @ risk={r*100:.2f}%", risk=r)
