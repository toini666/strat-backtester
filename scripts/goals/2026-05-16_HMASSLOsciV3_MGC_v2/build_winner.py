"""Build and write the winner preset for the HMASSLOsciV3 / MGC v2 campaign.

Winner config:
    - 5BO (11-12, 06-07, 07-08, 03-04, 09-10) + 22:00-23:59 (UI default)
    - risk = 0.47%
    - hma2_len=34, hw_range_on=True, block_loss_exit_before_partial=True,
      hma1_len=9, max_sl_points=100.0, tick_buffer=1

Final metrics: PnL=$44,711 / DD=$2,378 / N=1142 / WR=55.9% / PF=1.56 / P/DD=18.80
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.preset import build_preset, write_preset


STRATEGY = "HMASSLOsciV3"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50
RISK = 0.0047

OVERRIDES = {
    "hma2_len": 34,
    "hw_range_on": True,
    "block_loss_exit_before_partial": True,
    "hma1_len": 9,
    "max_sl_points": 100.0,
    "tick_buffer": 1,
}


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


# 5 extra blackouts on top of UI default (22:00-23:59 only)
EXTRA_BLACKOUTS = [w(11, 12), w(6, 7), w(7, 8), w(3, 4), w(9, 10)]


if __name__ == "__main__":
    es = make_engine_settings(STRATEGY, extra_active_windows=EXTRA_BLACKOUTS)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=OVERRIDES,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    print(f"Build run: {fmt_summary(s)}")
    print(f"  P/DD = {s['net_pnl'] / s['max_dd_$']:.2f}")

    preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=OVERRIDES,
        engine_settings=es,
        metrics_summary=s,
        name="[Auto] HMASSLOsciV3 — MGC 7m v2 — both goals met (P/DD≈18.8)",
    )

    out = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, out)
    print(f"\nWritten to: {out}")
    print(f"Inserted at top of data/presets.json")
