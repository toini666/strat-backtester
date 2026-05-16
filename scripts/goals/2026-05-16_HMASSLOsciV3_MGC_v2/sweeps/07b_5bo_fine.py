"""Sweep 07b — Fine risk grid on 5BO (11+06+07+03+09) config.

Best result: 5BO @ risk=0.42% → PnL=$40,162 / DD=$2,400 / P/DD=16.73

Push risk further to find the very best PnL that still satisfies DD < 2,500.
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


BO_4 = [w(11, 12), w(6, 7), w(7, 8), w(3, 4)]
BO_5 = BO_4 + [w(9, 10)]
BO_5_alt = BO_4 + [w(18, 19)]


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
    print("Sweep 07b — Fine risk grid on 5BO configs")
    print(f"Goal: PnL > ${GOAL_PNL:,.0f} AND DD < ${GOAL_DD:,.0f}")
    print("=" * 130)

    print("\n## 5BO (11+06+07+03+09)")
    for r in (0.0040, 0.0041, 0.0042, 0.0043, 0.0044, 0.0045, 0.0046,
              0.0047, 0.0048, 0.005, 0.0052):
        run_one(f"5BO @ risk={r*100:.2f}%", risk=r, blackouts=BO_5)

    print("\n## 5BO_alt (11+06+07+03+18)")
    for r in (0.0040, 0.0041, 0.0042, 0.0043, 0.0044, 0.0045, 0.0046):
        run_one(f"5BO_alt @ risk={r*100:.2f}%", risk=r, blackouts=BO_5_alt)

    print("\n## 4BO (11+06+07+03) — baseline reference")
    for r in (0.0037, 0.0038, 0.0039, 0.0040, 0.0041, 0.0042):
        run_one(f"4BO @ risk={r*100:.2f}%", risk=r, blackouts=BO_4)
