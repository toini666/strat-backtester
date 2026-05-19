"""Phase 8 — Combine the KEEPs from previous phases.

KEEPs collected:
  Phase 2/3: hw_extreme_on=False (+$1.4k), sig_extreme_on=False (+$1.1k)
             (equivalent to relaxing the thresholds — same effect)
  Phase 4:   none (all V4 levers rejected under DD<$2k)
  Phase 5:   daily after_close L=$700 (+$238 PnL, same DD); risk non-monotone
             around 0.60% needs fine probing
  Phase 7:   +H=06-08 blackout (+$2.2k PnL, DD $1,892 < $2k budget) → strongest single lever

Strategy:
  C1. Apply +H=06-08 alone (= Phase 7 winner).
  C2. + filter relaxations.
  C3. + daily limit after_close L=$700.
  C4. + risk fine sweep around 0.60% (memory: non-monotone).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
)


EXTRA_06_08 = {"start_hour": 6, "start_minute": 0, "end_hour": 8, "end_minute": 0}

RELAX_PARAMS = dict(BASELINE_V4_PARAMS)
RELAX_PARAMS["hw_extreme_on"] = False
RELAX_PARAMS["sig_extreme_on"] = False


def _engine(*, extra=(), win_limit=None, loss_limit=None, mode="after_close"):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=list(BASELINE_ACTIVE_BLACKOUTS) + list(extra),
        daily_win_limit=win_limit,
        daily_loss_limit=loss_limit,
        daily_limit_mode=mode,
    )


def _run(label, *, params, engine, risk=RISK_PER_TRADE):
    return bench(
        label,
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 120)
    print(f"PHASE 8 — Combine KEEPs  |  TF={INTERVAL}")
    print("=" * 120)

    base = _run("BASELINE (V3-migrated, risk=0.48%)",
                params=BASELINE_V4_PARAMS, engine=_engine())
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"\nBaseline P/DD = {base_ratio:.1f}\n")

    rows = [("BASELINE", base)]

    print("-" * 120)
    print("C1. +H=06-08 alone (Phase 7 winner)")
    print("-" * 120)
    rows.append(("C1 +H=06-08",
                 _run("C1 +H=06-08",
                      params=BASELINE_V4_PARAMS,
                      engine=_engine(extra=[EXTRA_06_08]))))

    print()
    print("-" * 120)
    print("C2. +H=06-08 + filter relaxations")
    print("-" * 120)
    rows.append(("C2a +H=06-08 + hw_extreme_on=F",
                 _run("C2a +H=06-08 + hw_extreme_on=F",
                      params={**BASELINE_V4_PARAMS, "hw_extreme_on": False},
                      engine=_engine(extra=[EXTRA_06_08]))))
    rows.append(("C2b +H=06-08 + sig_extreme_on=F",
                 _run("C2b +H=06-08 + sig_extreme_on=F",
                      params={**BASELINE_V4_PARAMS, "sig_extreme_on": False},
                      engine=_engine(extra=[EXTRA_06_08]))))
    rows.append(("C2c +H=06-08 + relax BOTH",
                 _run("C2c +H=06-08 + relax BOTH",
                      params=RELAX_PARAMS,
                      engine=_engine(extra=[EXTRA_06_08]))))

    print()
    print("-" * 120)
    print("C3. C2c + daily limit after_close L=$700")
    print("-" * 120)
    rows.append(("C3 C2c + ac L=$700",
                 _run("C3 C2c + ac L=$700",
                      params=RELAX_PARAMS,
                      engine=_engine(extra=[EXTRA_06_08],
                                     loss_limit=700,
                                     mode="after_close"))))

    print()
    print("-" * 120)
    print("C4. Risk fine sweep on C2c")
    print("-" * 120)
    for r in [0.0048, 0.0050, 0.0052, 0.0054, 0.0056, 0.0058, 0.0060,
              0.0062, 0.0064, 0.0066, 0.0070]:
        rows.append((f"C4 risk={r*100:.2f}% on C2c",
                     _run(f"C4 risk={r*100:.2f}% on C2c",
                          params=RELAX_PARAMS,
                          engine=_engine(extra=[EXTRA_06_08]),
                          risk=r)))

    print()
    print("=" * 120)
    print("TOP-10 CONFIGS UNDER DD<$2,000  (sorted by PnL)")
    print("=" * 120)
    valid = [(lbl, s) for lbl, s in rows if s["max_dd_$"] < 2000]
    if not valid:
        print("  (no config under $2k DD — listing top-5 by lowest DD)")
        valid = sorted(rows, key=lambda r: r[1]["max_dd_$"])[:5]
    else:
        valid.sort(key=lambda r: -r[1]["net_pnl"])
    print(f"{'Rank':<5}{'Config':<45}{'PnL':>11}{'DD':>9}{'N':>7}{'PF':>7}{'WR':>7}{'P/DD':>8}")
    print("-" * 120)
    for i, (lbl, s) in enumerate(valid[:10]):
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"{i+1:<5}{lbl:<45}${s['net_pnl']:>9,.0f}${s['max_dd_$']:>7,.0f}"
              f"{s['trades']:>7}{s['profit_factor']:>7.2f}{s['win_rate']:>6.1f}%{ratio:>8.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
