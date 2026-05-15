"""Build the final winner_preset.json and insert into data/presets.json.

Run this ONCE after sweep 08 declares the winning config.  The values in
`WINNER` and `EXPECTED` below are filled by sweep 08 — keep them in sync.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

# --- Winning configuration --------------------------------------------------
STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
TF = "7m"
START = "2025-01-06T00:00"
END = "2026-05-13T18:39"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

WINNER_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 4,
    "sig_extreme": 30,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}
WINNER_RISK = 0.0034
WINNER_DAILY_WIN = None
WINNER_DAILY_LOSS = None
WINNER_DAILY_MODE = "intra_bar"
WINNER_EXTRA_BLACKOUTS: list[dict] = [
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 0,  "start_minute": 0, "end_hour": 1,  "end_minute": 0},
    {"start_hour": 6,  "start_minute": 0, "end_hour": 7,  "end_minute": 0},
    {"start_hour": 8,  "start_minute": 0, "end_hour": 9,  "end_minute": 0},
    {"start_hour": 4,  "start_minute": 0, "end_hour": 5,  "end_minute": 0},
]
WINNER_ACTIVATE_EXISTING: list[tuple[int, int, int, int]] = [
    (12, 0, 14, 0),  # UI-default-inactive, re-activated
]


def main():
    es = make_engine_settings(
        STRATEGY,
        extra_active_windows=WINNER_EXTRA_BLACKOUTS,
        activate_existing=WINNER_ACTIVATE_EXISTING,
        daily_win_limit=WINNER_DAILY_WIN,
        daily_loss_limit=WINNER_DAILY_LOSS,
        daily_limit_mode=WINNER_DAILY_MODE,
    )
    assert es.auto_close_hour == 22 and es.auto_close_minute == 0, \
        "Auto-close must be 22:00 reference Brussels."

    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END, strategy_params=WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY, risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    print("WINNER replayed:", fmt_summary(s))

    preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=es,
        metrics_summary=s,
    )

    standalone = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, standalone, insert_into_presets_json=True)
    print(f"✅ Preset written → {standalone}")
    print(f"   and inserted into data/presets.json")

    # Echo expected metrics block for verify_preset.py
    print("\nUpdate verify_preset.py with:")
    print(json.dumps({
        "net_pnl": s["net_pnl"],
        "max_dd_$": s["max_dd_$"],
        "trades": s["trades"],
        "win_rate": s["win_rate"],
        "profit_factor": s["profit_factor"],
    }, indent=2))


if __name__ == "__main__":
    main()
