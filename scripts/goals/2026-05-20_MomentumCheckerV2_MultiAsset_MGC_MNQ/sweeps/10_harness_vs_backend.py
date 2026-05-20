"""Verify the harness's _combined_metrics matches the backend's combined
trade-list peak-to-trough computation on the baseline preset.

Calls run_multi_backtest() directly (the same code path /backtest/multi
HTTP endpoint hits) and compares to our harness output.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    MGC_BLACKOUTS_BASE, MNQ_BLACKOUTS_BASE,
    run_multi, fmt_multi, _combined_metrics,
    START, END, INITIAL_EQUITY, MAX_CONTRACTS, STRATEGY, INTERVAL,
)
from backend.api import (
    MultiBacktestRequest, MultiConfigRequest, BacktestEngineSettings,
    BlackoutWindowSettings, run_multi_backtest, load_strategies,
)


def _engine(blackouts):
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(
                active=True,
                start_hour=h1, start_minute=m1,
                end_hour=h2, end_minute=m2,
            )
            for (h1, m1, h2, m2) in blackouts
        ],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500,
        daily_loss_limit_enabled=False, daily_loss_limit=700,
        daily_limit_mode="after_close",
    )


def main():
    load_strategies()

    # 1. Run via the harness
    s_h = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    print(f"HARNESS: {fmt_multi(s_h)}")

    # 2. Run via the actual backend code path
    req = MultiBacktestRequest(
        mode="multi_asset",
        start_datetime=START,
        end_datetime=END,
        initial_equity=INITIAL_EQUITY,
        configs=[
            MultiConfigRequest(
                strategy_name=STRATEGY, symbol="MGC", interval=INTERVAL,
                params=MGC_PARAMS_BASE,
                risk_per_trade=0.0055, max_contracts=MAX_CONTRACTS,
                engine_settings=_engine(MGC_BLACKOUTS_BASE),
            ),
            MultiConfigRequest(
                strategy_name=STRATEGY, symbol="MNQ", interval=INTERVAL,
                params=MNQ_PARAMS_BASE,
                risk_per_trade=0.0066, max_contracts=MAX_CONTRACTS,
                engine_settings=_engine(MNQ_BLACKOUTS_BASE),
            ),
        ],
    )
    res = run_multi_backtest(req)
    trades_dicts = [t.model_dump() for t in res.trades]
    s_b = _combined_metrics(INITIAL_EQUITY, trades_dicts)
    print(f"BACKEND: {fmt_multi(s_b)}")
    print()
    print(f"Backend response metrics: max_drawdown={res.metrics.get('max_drawdown', 0):.4f}%, "
          f"total_return={res.metrics.get('total_return', 0):.4f}%")
    print(f"Note: backend response does NOT include max_drawdown_dollars (multi-asset path).")
    print()

    pnl_d = abs(s_h["net_pnl"] - s_b["net_pnl"])
    dd_d = abs(s_h["max_dd_$"] - s_b["max_dd_$"])
    n_d = abs(s_h["trades"] - s_b["trades"])
    print(f"Deltas: PnL=${pnl_d:.0f}  DD=${dd_d:.0f}  N={n_d}")
    if pnl_d < 1 and dd_d < 1 and n_d == 0:
        print("✅ MATCH — harness is identical to backend code path")
    else:
        print("⚠️  Some divergence — investigate")


if __name__ == "__main__":
    main()
