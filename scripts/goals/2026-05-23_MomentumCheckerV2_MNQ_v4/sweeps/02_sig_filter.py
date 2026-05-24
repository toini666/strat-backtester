"""Phase 2 — SIG range filter activation.

`sig_filter_on=True` gives `pts_sig_value` bonus when |oscSig| > sig_level.
It is an ADDITIVE bonus, not a reject — so to actually filter out
low-|sig| setups we need to combine it with a HIGHER entry threshold
(min_gap, long_threshold, short_threshold).

Strategy:
  - Bare filter (no threshold change) — for reference, expected to admit more trades.
  - Threshold-coupled filter: enable + raise min_gap by 1, OR raise both
    long_threshold and short_threshold by 1 (= effectively requires the SIG
    bonus to clear the bar; low-|sig| trades blocked).
  - Sweep sig_level × pts_sig_value × {threshold lift mechanism}.

Also probes `be_at_rr` (pre-TP1 BE trigger) since it would create true
'BE' exits the user can see in the breakdown.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    SEED_PARAMS,
    SEED_RISK,
    START,
    STRATEGY,
    SYMBOL,
    make_engine_settings,
)


def run(label: str, overrides: dict):
    params = dict(SEED_PARAMS)
    params.update(overrides)
    result = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(),
    )
    s = summarize(result)
    s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 2 — SIG range filter (additive bonus) + be_at_rr")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6% / SL_rate 60.3%")
    print("=" * 140)

    print("\n--- 2A. Bare SIG filter (no threshold change) ---")
    for lvl in [5, 8, 10, 12, 15, 20]:
        run(f"sig_filter_on lvl={lvl}", {"sig_filter_on": True, "sig_level": lvl, "pts_sig_value": 1})

    print("\n--- 2B. SIG filter + min_gap+1 (require SIG bonus to clear bar) ---")
    for lvl in [5, 8, 10, 12, 15, 20]:
        run(f"sig+gap+1 lvl={lvl}", {
            "sig_filter_on": True, "sig_level": lvl, "pts_sig_value": 1,
            "min_gap": SEED_PARAMS["min_gap"] + 1,
        })

    print("\n--- 2C. SIG filter + thresholds+1 ---")
    for lvl in [5, 8, 10, 12, 15, 20]:
        run(f"sig+th+1 lvl={lvl}", {
            "sig_filter_on": True, "sig_level": lvl, "pts_sig_value": 1,
            "long_threshold": SEED_PARAMS["long_threshold"] + 1,
            "short_threshold": SEED_PARAMS["short_threshold"] + 1,
        })

    print("\n--- 2D. SIG filter + pts_sig_value=2 + gap+2 (stronger filter coupling) ---")
    for lvl in [5, 8, 10, 12, 15, 20]:
        run(f"sig pts=2 gap+2 lvl={lvl}", {
            "sig_filter_on": True, "sig_level": lvl, "pts_sig_value": 2,
            "min_gap": SEED_PARAMS["min_gap"] + 2,
        })

    print("\n--- 2E. be_at_rr (pre-TP1 BE trigger; will produce true 'BE' exits) ---")
    for be in [0.0, 0.5, 1.0, 1.5, 2.0]:
        run(f"be_at_rr={be}", {"be_at_rr": be})

    print("\n--- 2F. Try sig_extreme tighter (currently 40 — generous) ---")
    for se in [15, 20, 25, 30, 40, 50]:
        run(f"sig_extreme={se}", {"sig_extreme": se})

    print("\n--- 2G. pts_sig_extreme (seed=1) — toggle the weight ---")
    for w in [0, 1, 2, 3]:
        run(f"pts_sig_extreme={w}", {"pts_sig_extreme": w})


if __name__ == "__main__":
    main()
