"""Sweep 08 — Final validation of winner + alternatives on full period.

Winner: BO[11,14,10] @ risk=0.01 (3-hour blackouts for robustness per advisor)
Expected: PnL=$44,006 DD=$6,588 P/DD=6.68
"""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import (
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench


BASE_V2 = {
    "delta_ext_on": True,
    "cloud_zero_on": True,
    "sig_extreme_on": True,
    "mf_smooth": 3,
    "cooldown_bars": 5,
    "max_candle_pct": 0.7,
}


def _es(hours):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": h, "start_minute": 0, "end_hour": h + 1, "end_minute": 0}
            for h in hours
        ],
    )


# (label, tf, overrides, blackout_hours, risk, intent)
CANDIDATES = [
    ("WINNER: BO[11,14,10] @ risk=0.01",
     "7m", {}, [11, 14, 10], 0.01,
     "best balance — 3-hour BO for robustness, satisfies PnL target with best DD"),
    ("ALT1: BO[11,14,10,6] @ risk=0.01",
     "7m", {}, [11, 14, 10, 6], 0.01,
     "4-hour BO — slightly more PnL, slightly more overfit risk"),
    ("ALT2: BO[11,14,10] + tick_buffer=1 @ risk=0.01",
     "7m", {"tick_buffer": 1}, [11, 14, 10], 0.01,
     "lower DD, lower PnL — defensive variant"),
    ("ALT3: BO[11,14,10,6] + tick_buffer=1 @ risk=0.008",
     "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.008,
     "tighter risk — PnL just above $30k, DD ≈ $5k"),
    ("ALT4: BO[11,14,10,6] @ risk=0.002 (DD-passing)",
     "7m", {}, [11, 14, 10, 6], 0.002,
     "only config close to passing DD<$2.5k — PnL very low ($8.6k)"),
    ("ALT5: BO[11,14,10] @ risk=0.012",
     "7m", {}, [11, 14, 10], 0.012,
     "higher PnL — moderate DD increase"),
]


def main():
    print(f"=== Sweep 08 — final validation — {STRATEGY} / {SYMBOL} ===")
    print()

    rows = []
    for label, tf, overrides, hours, risk, intent in CANDIDATES:
        params = {**BASE_V2, **overrides}
        es = _es(hours)
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=tf,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = label
        s["tf"] = tf
        s["overrides"] = overrides
        s["hours"] = hours
        s["risk"] = risk
        s["intent"] = intent
        s["pass_pnl"] = s["net_pnl"] > 30_000
        s["pass_dd"] = s["max_dd_$"] < 2_500
        rows.append(s)

    print("\n=== FINAL TABLE ===")
    for r in rows:
        marker_pnl = "✅" if r["pass_pnl"] else "❌"
        marker_dd = "✅" if r["pass_dd"] else "❌"
        print(f"\n  {r['label']}")
        print(f"    {marker_pnl} PnL=${r['net_pnl']:,.0f} (target >$30k)   "
              f"{marker_dd} DD=${r['max_dd_$']:,.0f} (target <$2.5k)")
        print(f"    PF={r['profit_factor']}  WR={r['win_rate']}%  N={r['trades']}  "
              f"P/DD={r['ratio_p_dd']}  Sharpe={r.get('sharpe', 0)}")
        print(f"    intent: {r['intent']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "08_final_validation.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
