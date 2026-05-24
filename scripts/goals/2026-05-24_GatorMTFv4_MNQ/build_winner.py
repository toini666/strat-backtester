"""Build winner_preset.json for the GatorMTFv4 MNQ campaign.

WINNER: ABCD=1101 (case_c off) + rr=2.0 + cd=90 + amp=1.0
        + 9-hour blackouts (H06,H11,H12,H14,H16,H17,H19,H21,H23)
        + risk=0.26% + auto-close 22:00
        period 2025-01-08 → 2026-05-22 (full available MNQ 1m history)

Metrics: PnL $13,156 / DD $2,461 / WR 37.9% / N 1,424 / PF 1.17
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.preset import build_preset, write_preset
from sweeps._campaign import (
    SEED_PARAMS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


CAMPAIGN_DIR = Path(__file__).resolve().parent


WINNER_PARAMS = dict(SEED_PARAMS)
WINNER_PARAMS.update({
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
    "case_c_on": False,
})

WINNER_RISK_DECIMAL = 0.0026  # 0.26 %

WINNER_BO_EXTRA = [
    (6, 0, 7, 0),
    (11, 0, 12, 0),
    (12, 0, 13, 0),
    (14, 0, 15, 0),
    (16, 0, 17, 0),
    (17, 0, 18, 0),
    (19, 0, 20, 0),
    (21, 0, 22, 0),
    (23, 0, 23, 59),
]


def _winner_engine_settings():
    extras = [{"start_hour": sh, "start_minute": sm,
               "end_hour": eh, "end_minute": em}
              for sh, sm, eh, em in WINNER_BO_EXTRA]
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=extras,
    )
    # Keep the 22:00–23:59 seed BO active (it's the auto-close adjacent).
    seed_set = {(22, 0, 23, 59)}
    extra_set = {(e["start_hour"], e["start_minute"], e["end_hour"], e["end_minute"])
                 for e in extras}
    for w in es.blackout_windows:
        key = (w.start_hour, w.start_minute, w.end_hour, w.end_minute)
        w.active = key in seed_set or key in extra_set
    return es


def main():
    engine = _winner_engine_settings()
    print("Active blackouts:",
          [(w.start_hour, w.start_minute, w.end_hour, w.end_minute)
           for w in engine.blackout_windows if w.active])
    print()

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
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
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=engine,
        metrics_summary=s,
        name="BESTPNL-MNQ GatorMTFv4 - MNQ 1m v1",
    )

    out_path = CAMPAIGN_DIR / "winner_preset.json"
    write_preset(preset, out_path, insert_into_presets_json=True)
    print(f"Winner preset written: {out_path}")
    print(f"Also inserted at top of: data/presets.json (UI favorites)")


if __name__ == "__main__":
    main()
