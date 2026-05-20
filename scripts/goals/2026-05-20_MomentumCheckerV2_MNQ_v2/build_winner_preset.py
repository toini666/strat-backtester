"""Build the v2 winner preset and insert into data/presets.json.

WINNER (Phase 10):
  Strategy: amp_mult=3.5, pts_hma_slow=1 ssl=60 hw=5, st_atr=10, tick_buffer=2
  Blackouts: 09-10, 13-14:30, 17-23:59
  Risk: 0.66%
  Result: PnL=$80,565 / $DD=$3,023 / N=797 / WR=40.4% / PF=1.58 / P/DD=26.65

vs V1 anchor: +$19,252 PnL (+31.4%), -$51 $DD (-1.7%)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    build_engine,
)


WINNER_OVERRIDES = {
    **BASELINE_PARAMS,  # B-baseline (V1-compat + amp=3.0+B overrides)
    # P7+P8 winners
    "amp_mult":         3.5,    # P5 finding
    "pts_hma_slow":     1,      # P1 finding
    "ssl_len":          60,
    "hma_window_bars":  5,
    "st_atr":           10,     # P5 finding
    "tick_buffer":      2,      # P3 finding
}

RISK_PER_TRADE = 0.0066

PRESET_NAME = (
    "[Auto] MomentumCheckerV2 — MNQ 7m — v2 WINNER "
    "(PnL $80.6k / DD $3.02k / P/DD 26.7)"
)

# Winning blackout windows (V1 + 13-14 extended to 14:30)
WINNING_WINDOWS = [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]


def main() -> int:
    engine = build_engine(WINNING_WINDOWS)

    print("Running winner config for verification...")
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=WINNER_OVERRIDES,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(r)
    print(fmt_summary(s))
    print(f"max_dd_pct: {r['metrics']['max_drawdown']:.2f}%")
    print()

    preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_OVERRIDES,
        engine_settings=engine,
        metrics_summary=s,
        name=PRESET_NAME,
    )

    out_path = CAMPAIGN_DIR / "winner_preset.json"
    write_preset(preset, out_path, insert_into_presets_json=True)
    print(f"Wrote {out_path}")
    print("Inserted into data/presets.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
