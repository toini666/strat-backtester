"""Sweep 03b — Combos of the most promising 1D winners from sweep 03.

Winners from 03 (baseline = prev_winner_overrides + block_loss):
- hma1_len = 9   →   PnL +$10k, DD +$1k     (PF↑↑)
- hma_pol_bars = 2 →  DD -$170             (PF↑)
- max_sl_points = 100 (or 150) → PnL +$3k, DD =     (clear gain)
- tick_buffer = 1 → DD -$56                 (marginal)
- max_candle_pct = 0.5 → marginal
- hw_extreme = 15 → marginal

Test additivity.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)

ES = ui_default_engine_settings(STRATEGY)
BASE = dict(PREV_WINNER_OVERRIDES)
BASE["block_loss_exit_before_partial"] = True


def run_one(label, params):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=PREV_WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=ES,
    )
    s = summarize(r)
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    print(f"{label:<70s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 120)
    print("Sweep 03b — Combos of 1D winners")
    print("=" * 120)
    run_one("BASELINE (hma2=34 + hw_range + block_loss)", BASE)
    print("-" * 120)

    # Pairwise additivity tests
    overlays = {
        "hma1=9": {"hma1_len": 9},
        "hma_pol=2": {"hma_pol_bars": 2},
        "maxsl=100": {"max_sl_points": 100.0},
        "tickbuf=1": {"tick_buffer": 1},
        "maxcdl=0.5": {"max_candle_pct": 0.5},
        "hwext=15": {"hw_extreme": 15.0},
    }

    # Single
    print("\n## Singles (sanity check)")
    for name, ov in overlays.items():
        cfg = dict(BASE); cfg.update(ov)
        run_one(f"+ {name}", cfg)

    # Pairs
    print("\n## Pairs")
    names = list(overlays.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            cfg = dict(BASE)
            cfg.update(overlays[names[i]])
            cfg.update(overlays[names[j]])
            run_one(f"+ {names[i]} + {names[j]}", cfg)

    # Promising triples (heuristic: anchored on hma1=9 and maxsl=100 — the two biggest PnL lifts)
    print("\n## Triples and full combo (anchored on hma1=9 and maxsl=100)")
    anchors = {"hma1=9": overlays["hma1=9"], "maxsl=100": overlays["maxsl=100"]}
    for name, ov in overlays.items():
        if name in anchors:
            continue
        cfg = dict(BASE)
        cfg.update(overlays["hma1=9"])
        cfg.update(overlays["maxsl=100"])
        cfg.update(ov)
        run_one(f"+ hma1=9 + maxsl=100 + {name}", cfg)

    # Quad
    for extras in (
        ("hma_pol=2", "tickbuf=1"),
        ("hma_pol=2", "maxcdl=0.5"),
        ("hma_pol=2", "hwext=15"),
        ("tickbuf=1", "maxcdl=0.5"),
        ("tickbuf=1", "hwext=15"),
    ):
        cfg = dict(BASE)
        cfg.update(overlays["hma1=9"])
        cfg.update(overlays["maxsl=100"])
        for e in extras:
            cfg.update(overlays[e])
        run_one(f"+ hma1=9 + maxsl=100 + {extras[0]} + {extras[1]}", cfg)

    # All combo
    cfg = dict(BASE)
    for ov in overlays.values():
        cfg.update(ov)
    run_one("+ ALL overlays", cfg)
