"""Build the V2 MGC winner preset and insert into data/presets.json.

WINNER:
  Strategy:  V2 V1-compat + {pts_hma_slow=1, hma_window_bars=5,
                              max_candle_pct=0.3, ema_sec_len=5,
                              be_at_rr=2.0, sl_max_points=100}
  Blackouts: 12:30-14:00, 18:00-19:00, 20:00-21:00, 22:00-23:59
  Risk:      0.55%
  Result:    PnL=$58,249 / $DD=$2,486 / N=851 / WR=39.7% / PF=1.54 / P/DD=23.4

UNDER user's hard ceiling of $2,500 with $14 margin.
Soft target $2,000 is NOT reachable (1-contract floor at $2,500).
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
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    build_engine,
)


WINNER_OVERRIDES = {
    **V1_COMPAT_PARAMS,
    # Phase 6/8c stack
    "pts_hma_slow":     1,     # B: V2 SSL bucket
    "hma_window_bars":  5,     # B: window for HMA-slow/SSL cross
    "max_candle_pct":   0.3,   # C: tightened candle filter (was 0.4)
    "ema_sec_len":      5,     # D: shorter EMA secondary (was 9)
    "be_at_rr":         2.0,   # E: move SL to entry at RR=2 (DD relief)
    "sl_max_points":    100.0, # A: SL cap (was V1 MGC's 50)
}

RISK_PER_TRADE = 0.0055

# Surgical blackouts: replaces V1's broad 17-21 with targeted 18-19 + 20-21
# to keep profitable H=17, H=19, H=21 trades.
WINNING_WINDOWS = [
    (12, 30, 14, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]

PRESET_NAME = (
    "[Auto] MomentumCheckerV2 — MGC 7m — WINNER "
    "(PnL $58.2k / DD $2.49k / P/DD 23.4)"
)


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
    print(f"User constraints check:")
    print(f"  Hard ceiling $DD ≤ $2,500: {'✅ PASS' if s['max_dd_$'] <= 2500 else '❌ FAIL'} (actual ${s['max_dd_$']:,.0f})")
    print(f"  Soft target $DD ≤ $2,000: {'✅ PASS' if s['max_dd_$'] <= 2000 else '❌ FAIL (floor at ~$2,500)'}")
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
