"""Build the MomentumCheckerV2 MNQ 7m winner preset and write it to
`data/presets.json` (UI favorites) + a standalone JSON for the campaign folder.

Winner config (Phase 9/10):
  W_LowDD risk=0.70% → PnL=$69,819 / DD=$1,866 / N=835 / WR=31.5% / PF=1.59

Strategy: MomentumCheckerV2 (V1-compat baseline + V2 strict-DD winners)
Beats V1 anchor ($61,313/$2,143) in BOTH dimensions:
  +$8,506 PnL  /  −$277 DD  /  P/DD 37.42 vs 28.62
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
    ANCHOR_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
)


# Final winner overrides
WINNER_OVERRIDES = {
    # V1-compat anchor base (already in ANCHOR_PARAMS)
    # V2 strict-DD winners:
    "amp_mult":              3.0,
    "max_candle_pct":        0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme":           40.0,
    "hma_pol_bars":          20,
    # Risk geometry / BE
    "be_at_rr":              1.25,
    "sl_max_points":         60.0,
}


RISK_PER_TRADE = 0.0070   # 0.70% — sizing sweet spot (DD <$2k)

PRESET_NAME = (
    "[Auto] MomentumCheckerV2 — MNQ 7m — WINNER "
    "(PnL $69.8k / DD $1.87k)"
)


def main() -> int:
    # Build the full param dict on top of the anchor base
    full_overrides = dict(ANCHOR_PARAMS)
    full_overrides.update(WINNER_OVERRIDES)

    engine = anchor_engine()

    print("Running winner config for verification...")
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=full_overrides,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(r)
    print(fmt_summary(s))
    print()

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=full_overrides,
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
