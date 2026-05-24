"""Build winner_preset.json and insert into data/presets.json.

WINNER: rr_tp=1.55 + sig_level=2 + sl_lookback=10 + tick_buffer=2
        + BO 11-12 + BO 14-15 + risk=0.83%
        period 2025-01-02 → 2026-05-22 (full available MNQ 7m history)

Metrics: PnL $69,571 / DD $2,367 / WR 52.6% / N=608 / PF 1.66
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import (
    ui_default_engine_settings, make_engine_settings,
)
from scripts.goals._shared.preset import build_preset, write_preset
from sweeps._campaign import (
    SEED_PARAMS, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)

CAMPAIGN_DIR = Path(__file__).resolve().parent

# Extended start — full available MNQ 7m history
WINNER_START = "2025-01-02T00:00"
WINNER_END = END

WINNER_PARAMS = dict(SEED_PARAMS)
WINNER_PARAMS.update({
    "rr_tp": 1.55,
    "sl_lookback": 10,
    "tick_buffer": 2,
    "sig_range_reject": True,
    "sig_level": 2,
})

WINNER_RISK_DECIMAL = 0.0083  # 0.83 %
WINNER_BO_EXTRA = [
    (11, 0, 12, 0),
    (14, 0, 15, 0),
]


def _winner_engine_settings():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS) + WINNER_BO_EXTRA
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm,
             "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in all_bo
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def main():
    # Replay to confirm metrics & extract summary
    engine = _winner_engine_settings()
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=WINNER_START,
        end=WINNER_END,
        strategy_params=WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(r)
    print("WINNER REPLAY:")
    print("  " + fmt_summary(s))
    print()

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=WINNER_START,
        end=WINNER_END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=engine,
        metrics_summary=s,
        name="BESTWR-MNQ MomentumCheckerV2 - MNQ 7m v5",
    )

    out_path = CAMPAIGN_DIR / "winner_preset.json"
    write_preset(preset, out_path, insert_into_presets_json=True)
    print(f"Winner preset written: {out_path}")
    print(f"Also inserted at top of: data/presets.json (UI favorites)")


if __name__ == "__main__":
    main()
