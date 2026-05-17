"""08 — Build winner preset + verify ✅ MATCH.

WINNER (sweep 06-A r=0.0052):
  PnL=$44,692 / DD=$1,944 / N=865 / WR=55.1% / PF=1.66 / P/DD=22.99
  margin $56 below $2,000 DD ceiling

Sims used: ~2 / 200 (build + verify) → cumulative ~189/200
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END,
    INITIAL_EQUITY, MAX_CONTRACTS,
    V2_WINNER_OVERRIDES, V2_WINNER_BLACKOUTS,
)


# Winner overrides
WINNER_OVERRIDES = dict(V2_WINNER_OVERRIDES)
WINNER_OVERRIDES.update({
    "cloud_on": True,
    "mf_length": 29,
    "mf_smooth": 5,
})
WINNER_RISK = 0.0052


CAMPAIGN_DIR = Path(__file__).resolve().parent.parent
PRESET_PATH = CAMPAIGN_DIR / "winner_preset.json"


def main():
    # Run winner config to populate metrics
    es = make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in V2_WINNER_BLACKOUTS
        ],
    )

    print("Running WINNER config to confirm metrics…")
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=WINNER_OVERRIDES,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"WINNER  PnL=${s['net_pnl']:,.0f}  DD=${s['max_dd_$']:,.0f}  N={s['trades']}  "
          f"WR={s['win_rate']}%  PF={s['profit_factor']}")

    name = (
        f"[Auto] {STRATEGY} — {SYMBOL} 7m v3 — DD<$2k (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k)"
    )
    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_OVERRIDES,
        engine_settings=es,
        metrics_summary=s,
        name=name,
    )

    write_preset(preset, PRESET_PATH, insert_into_presets_json=True)
    print(f"\nPreset written to {PRESET_PATH}")
    print(f"Also inserted at the top of data/presets.json")


if __name__ == "__main__":
    main()
