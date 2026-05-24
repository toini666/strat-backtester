"""Build the v5 PnL winner preset and insert it into data/presets.json.

WINNER (PnL focus on top of v4 WR winner):
  PnL  $51,984 / DD $2,377 / WR 53.7 % / N=1062 / PF 1.50
  +$23,822 PnL vs v4 WR winner (+84.6 %), DD -$61, WR +2.7 pp.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

# Campaign-local imports
sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END,
    INITIAL_EQUITY, MAX_CONTRACTS,
    SEED_PARAMS, build_engine_settings,
)


# Locked-in BO list (Phase 5 outcome)
WINNER_BOS = [
    (12, 0, 12, 30),
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (2, 0, 3, 0),
    (6, 30, 7, 0),
    (11, 30, 12, 0),
    (19, 30, 20, 0),
]

# Final strategy param overrides on top of SEED (= v4 WR winner)
WINNER_PARAM_OVERRIDES = {
    "ema_prin_len": 40,       # Phase 8: +$844 PnL / -$15 DD vs 30
    "lips_length": 6,         # Phase 9/10: +$2,420 PnL / -$49 DD
    "lips_offset": 5,         # Phase 9/10: +$2,845 PnL / +$5 DD
    "hma2_len": 76,           # Phase 9/10: +$656 PnL / 0 DD
    "sl_max_points": 80.0,    # Phase 11: +$1,254 PnL / 0 DD
    "rr_tp": 1.22,            # Phase 12: lifts WR margin (52.9 -> 53.7 %)
}

WINNER_RISK_DECIMAL = 0.0053  # 0.53 %


def main() -> None:
    params = dict(SEED_PARAMS)
    params.update(WINNER_PARAM_OVERRIDES)
    engine = build_engine_settings(blackouts=WINNER_BOS,
                                   auto_close_h=22, auto_close_m=0,
                                   daily_win_on=False, daily_loss_on=False,
                                   daily_limit_mode="after_close")

    print("Replay winner config...")
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_params=params,
        engine_settings=engine,
    )
    s = summarize(r)
    print(fmt_summary(s))

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=params,
        engine_settings=engine,
        metrics_summary=s,
        name="BESTPNL-MGC MomentumCheckerV2 - MGC 7m v5",
    )

    standalone = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, standalone, insert_into_presets_json=True)
    print(f"\nWrote {standalone}")
    print("Inserted into data/presets.json under name 'BESTPNL-MGC MomentumCheckerV2 - MGC 7m v5'.")

    # Save expected metrics
    import json
    expected = {
        "net_pnl": s["net_pnl"],
        "max_dd_$": s["max_dd_$"],
        "trades": s["trades"],
        "win_rate": s["win_rate"],
        "profit_factor": s["profit_factor"],
    }
    exp_path = Path(__file__).resolve().parent / "expected_winner_metrics.json"
    exp_path.write_text(json.dumps(expected, indent=2))
    print(f"Wrote {exp_path}")


if __name__ == "__main__":
    main()
