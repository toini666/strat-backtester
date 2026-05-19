"""Phase 5 — Risk and daily limits sweeps.

Two independent 1-D sweeps:
  A. risk_per_trade  — fine grid around the 0.48% baseline (non-monotone known)
  B. daily limits — try `intra_bar` first; `after_close` as fallback

Best of A applied during B.
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


def _engine_default():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
    )


def _engine_with_limits(mode: str, win: float | None, loss: float | None):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
        daily_win_limit=win,
        daily_loss_limit=loss,
        daily_limit_mode=mode,
    )


def _common(risk: float, engine):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=BASELINE_V4_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 5 — Risk / daily limits  |  TF={INTERVAL}")
    print("=" * 110)

    base = bench(f"V4 baseline risk={RISK_PER_TRADE*100:.2f}%", **_common(RISK_PER_TRADE, _engine_default()))
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"\nBaseline P/DD ratio = {base_ratio:.1f}\n")

    # ===== A. Risk sweep =====
    print("-" * 110)
    print("A. risk_per_trade (fine grid)")
    print("-" * 110)
    risk_grid = [0.0030, 0.0035, 0.0040, 0.0044, 0.0048, 0.0052, 0.0056, 0.0060, 0.0070, 0.0080]
    risk_results = []
    for r in risk_grid:
        s = bench(f"risk={r*100:.2f}%", **_common(r, _engine_default()))
        risk_results.append((r, s))

    valid_risks = [(r, s) for r, s in risk_results if s["max_dd_$"] < 2000]
    if valid_risks:
        best_r, best_s = max(valid_risks, key=lambda kv: kv[1]["net_pnl"])
        print(f"\n  → Best risk under DD<$2k: {best_r*100:.2f}%  PnL=${best_s['net_pnl']:,.0f}  "
              f"DD=${best_s['max_dd_$']:,.0f}")
    else:
        best_r = RISK_PER_TRADE
        print(f"\n  → No risk passes DD<$2k. Falling back to baseline {best_r*100:.2f}%")

    # ===== B. Daily limits, using best risk =====
    print()
    print("-" * 110)
    print(f"B. Daily limits (risk={best_r*100:.2f}%)")
    print("-" * 110)
    daily_specs = [
        # (mode, win, loss)
        ("none",       None,  None),    # baseline at this risk
        ("intra_bar",  500,   None),
        ("intra_bar",  None,  700),
        ("intra_bar",  500,   700),
        ("intra_bar",  300,   500),
        ("intra_bar",  1000,  1000),
        ("after_close",500,   None),
        ("after_close",None,  700),
        ("after_close",500,   700),
        ("after_close",300,   500),
        ("after_close",1000,  1000),
    ]
    for mode, win, loss in daily_specs:
        if mode == "none":
            engine = _engine_default()
            label = f"no limits"
        else:
            engine = _engine_with_limits(mode, win, loss)
            wl = f"W=${win}" if win else "W=-"
            ll = f"L=${loss}" if loss else "L=-"
            label = f"{mode:<12s} {wl} {ll}"
        bench(label, **_common(best_r, engine))

    return 0


if __name__ == "__main__":
    sys.exit(main())
