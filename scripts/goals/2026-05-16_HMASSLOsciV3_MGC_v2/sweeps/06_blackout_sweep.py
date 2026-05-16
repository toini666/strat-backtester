"""Sweep 06 — Blackout sweep on v2 baseline.

Toxic hours identified (sweep 05):
- H=11: -$3,559 / WR 41%   (definite)
- H=17: -$1,279 / WR 52%   (moderate)
- H=03: -$1,184 / WR 44%   (moderate)
- H=23, 22: already blacked via 22-23:59

Test additivity. Previous campaign found H=17 blackout HURT DD — re-validate.
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


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


if __name__ == "__main__":
    print("=" * 110)
    print("Sweep 06 — Blackout sweep on v2 baseline")
    print("=" * 110)
    run_one("BASELINE (only 22-23:59)", [])
    print("-" * 110)

    # Singles
    candidates = {
        "BO=03-04": [w(3, 4)],
        "BO=11-12": [w(11, 12)],
        "BO=17-18": [w(17, 18)],
        "BO=21-22": [w(21, 22)],
        "BO=06-07": [w(6, 7)],
    }
    print("\n## Singles")
    for name, ws in candidates.items():
        run_one(name, ws)

    # Pairs
    print("\n## Pairs (anchored on 11-12 — biggest toxic)")
    for name, ws in candidates.items():
        if name == "BO=11-12":
            continue
        run_one(f"BO=11-12 + {name}", [w(11, 12)] + ws)

    # Triple
    print("\n## Triple — 11-12 + 03-04 + 17-18")
    run_one("BO=11-12 + 03-04 + 17-18", [w(11, 12), w(3, 4), w(17, 18)])

    print("\n## All-the-toxic-ones quads")
    run_one("BO=11-12 + 03-04 + 17-18 + 21-22", [w(11, 12), w(3, 4), w(17, 18), w(21, 22)])
    run_one("BO=11-12 + 03-04 + 17-18 + 06-07", [w(11, 12), w(3, 4), w(17, 18), w(6, 7)])
