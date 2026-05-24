"""Build the WINNER preset for MomentumCheckerV2 MGC v4_WR.

WINNER:
  ut_off rr_tp=1.25 sl_lookback=14 tick_buffer=0 risk=0.40%
  + BO 7-8, BO 12-12:30 added on top of seed's 5 BOs
  -> PnL=$27,900 DD=$2,278 ($222 headroom) WR=51.0% N=1056

The trade-off: ~55% PnL reduction vs seed ($61.4k → $27.9k) to gain +11.4 pp
WR (39.6% → 51.0%) while staying $222 under DD budget.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize
from scripts.goals._shared.preset import build_preset, write_preset
from _campaign import (
    SEED_PARAMS, build_engine_settings, SEED_BLACKOUTS_ACTIVE,
    STRATEGY, SYMBOL, INTERVAL, INITIAL_EQUITY, MAX_CONTRACTS, START, END,
)


# WINNER overrides
WINNER_OVERRIDES = {
    "ut_on": False,
    "rr_tp": 1.25,
    "sl_lookback": 14,
    "tick_buffer": 0,
}
WINNER_RISK_DEC = 0.0042  # max-PnL cell strictly under DD budget (Phase 18)
WINNER_BLACKOUTS = SEED_BLACKOUTS_ACTIVE + [
    (7, 0, 8, 0),
    (12, 0, 12, 30),
]


def main():
    full_params = dict(SEED_PARAMS)
    full_params.update(WINNER_OVERRIDES)

    es = build_engine_settings(blackouts=WINNER_BLACKOUTS,
                               auto_close_h=22, auto_close_m=0)

    print("--- Reproducing WINNER metrics ---")
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=WINNER_RISK_DEC,
        max_contracts=MAX_CONTRACTS, strategy_params=full_params,
        engine_settings=es,
    )
    s = summarize(r)
    raw_dd = r["metrics"]["max_drawdown_dollars"]
    print(f"PnL=${s['net_pnl']:,.0f}  DD=${s['max_dd_$']:,.0f} (raw ${raw_dd:.2f})  "
          f"WR={s['win_rate']:.1f}%  N={s['trades']}  PF={s['profit_factor']}")

    preset_name = "BESTWR-MGC MomentumCheckerV2 - MGC 7m v4"
    # IMPORTANT: pass the FULL params dict (SEED + WINNER overrides) so the preset
    # is self-contained. build_preset merges over default_params, but SEED is not
    # identical to default_params; passing the merged dict bypasses this issue.
    merged_overrides = dict(SEED_PARAMS)
    merged_overrides.update(WINNER_OVERRIDES)
    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_DEC,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=merged_overrides,
        engine_settings=es,
        metrics_summary=s,
        name=preset_name,
    )

    out = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, out, insert_into_presets_json=True)
    print(f"\n✅ WINNER preset written: {out}")
    print(f"   Name in UI favorites: {preset_name}")

    # Save expected metrics for verify_preset.py
    expected = {
        "net_pnl": s["net_pnl"],
        "max_dd_$": s["max_dd_$"],
        "trades": s["trades"],
        "win_rate": s["win_rate"],
        "profit_factor": s["profit_factor"],
    }
    import json as _json
    (Path(__file__).resolve().parent / "expected_winner_metrics.json").write_text(
        _json.dumps(expected, indent=2)
    )
    print(f"   Expected metrics saved for verify_preset.py")


if __name__ == "__main__":
    main()
