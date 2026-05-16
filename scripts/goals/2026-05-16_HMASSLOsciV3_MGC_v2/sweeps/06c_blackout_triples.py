"""Sweep 06c — Triple/quad blackout combos.

From 06b, ANCHOR (11-12 + 06-07) + a single extra:
- + 07-08: P/DD=12.31 (best)
- + 09-10: P/DD=12.10
- + 03-04: P/DD=11.38 (highest PnL=$48,972)
- + 18-19: P/DD=11.27
- + 13-14: P/DD=10.39
- + 16-17: P/DD=10.37

Test combos. Watch for non-additivity.
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
    print(f"{label:<70s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 120)
    print("Sweep 06c — Triple/quad blackout combos")
    print("=" * 120)
    anchor = [w(11, 12), w(6, 7)]
    run_one("ANCHOR (11-12 + 06-07)", anchor)
    print("-" * 120)

    extras = {
        "07-08": w(7, 8),
        "09-10": w(9, 10),
        "03-04": w(3, 4),
        "18-19": w(18, 19),
        "13-14": w(13, 14),
        "16-17": w(16, 17),
    }

    # Pairs of extras (so triple total)
    print("\n## Triples = ANCHOR + 2 extras")
    names = list(extras.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            run_one(f"ANCHOR + {names[i]} + {names[j]}",
                    anchor + [extras[names[i]], extras[names[j]]])

    # Quads = ANCHOR + 3 extras, anchored on top combos found above
    print("\n## Quads = ANCHOR + 07-08 + 2 extras (top DD-reducer)")
    for name in names:
        if name == "07-08":
            continue
        run_one(f"ANCHOR + 07-08 + {name}", anchor + [extras["07-08"], extras[name]])

    print("\n## Quads = ANCHOR + 09-10 + 2 extras")
    for name in names:
        if name in ("07-08", "09-10"):
            continue
        run_one(f"ANCHOR + 09-10 + {name}", anchor + [extras["09-10"], extras[name]])

    # All 6 extras
    print("\n## All 6 extras")
    run_one("ANCHOR + ALL 6 extras", anchor + list(extras.values()))
