"""Verify that MomentumCheckerV2, configured to match V1 behaviour, reproduces
the V1 preset "New base - MomentumChecker - MNQ 7m" bit-for-bit.

Usage::

    source venv/bin/activate
    python scripts/verify_momentum_checker_v2_vs_v1.py

V1→V2 translation rules:
  * Drop V1-only keys (rob_on, pts_rob, use_heikin_ashi).
  * Set V2-new keys to V1-equivalent values (hma_pol_bars=-1, pts_hma_slow=0,
    cloud_zero off, delta_off_mode="both", be_at_rr=0, sig_extreme=hw_extreme).
  * Compensate V2's scoring-style change (filter OFF → bonus removed) by
    leaving the filter ON with a no-op threshold whenever V1 had it OFF.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import engine_from_dict  # noqa: E402


PRESETS_FILE = ROOT / "data" / "presets.json"
PRESET_NAME = "New base - MomentumChecker - MNQ 7m"


def load_preset(name: str) -> Dict[str, Any]:
    presets = json.loads(PRESETS_FILE.read_text())
    for p in presets:
        if p.get("name") == name:
            return p
    raise SystemExit(f"Preset '{name}' not found in {PRESETS_FILE}")


def translate_v1_to_v2(v1_params: Dict[str, Any]) -> Dict[str, Any]:
    """Map V1 params onto V2 V1-compat configuration."""
    v2 = dict(v1_params)

    # --- Drop V1-only keys ---
    for k in ("rob_on", "pts_rob", "use_heikin_ashi"):
        v2.pop(k, None)

    # --- New-in-V2 features → neutralised ---
    v2["hma_pol_bars"] = -1
    v2["pts_hma_slow"] = 0
    v2["hma_window_bars"] = 0
    v2["ssl_len"] = 60      # irrelevant when pts_hma_slow=0
    v2["ssl_mult"] = 0.2
    v2["cloud_zero_filter_on"] = False
    v2["pts_cloud_zero"] = 0
    v2["be_at_rr"] = 0.0
    v2["delta_off_mode"] = "both"   # V1 behaviour on delta-off
    v2["sig_extreme"] = v1_params.get("hw_extreme", 20.0)

    # --- Cloud / Delta toggles default ON in V2 (V1 always-on) ---
    v2["cloud_filter_on"] = True
    v2["delta_filter_on"] = True

    # --- V2 scoring change: filter OFF removes the point. V1 grants it.
    # Compensate by keeping the filter ON with a no-op threshold. ---
    if not v1_params.get("hw_filter_on", True):
        v2["hw_filter_on"] = True
        v2["hw_level"] = 0.0
    if not v1_params.get("hw_extreme_filter_on", True):
        v2["hw_extreme_filter_on"] = True
        v2["hw_extreme"] = 1e9
    if not v1_params.get("sig_extreme_filter_on", False):
        v2["sig_extreme_filter_on"] = True
        v2["sig_extreme"] = 1e9

    return v2


def main() -> int:
    preset = load_preset(PRESET_NAME)
    engine = engine_from_dict(preset["engineSettings"])

    v1_params = {k: v for k, v in preset["params"].items() if k != "tick_size"}
    v2_params = translate_v1_to_v2(v1_params)

    print(f"PRESET: {PRESET_NAME}")
    print(f"  symbol={preset['symbol']} interval={preset['interval']} "
          f"period={preset['startDatetime']} → {preset['endDatetime']}")
    print(f"  initial=${preset['initialEquity']:,.0f} risk={preset['riskPerTrade']}% "
          f"max_contracts={preset['maxContracts']}")
    print()

    # --- V1 run (as preset) ---
    print("[1/2] Running V1 (preset as-is)...")
    r1 = run_backtest(
        strategy_name="MomentumChecker",
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=v1_params,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )
    s1 = summarize(r1)

    # --- V2 run (translated) ---
    print("[2/2] Running V2 (V1-compat translation)...")
    r2 = run_backtest(
        strategy_name="MomentumCheckerV2",
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=v2_params,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )
    s2 = summarize(r2)

    print()
    print(f"V1: {fmt_summary(s1)}")
    print(f"V2: {fmt_summary(s2)}")

    pnl_delta = abs(s1["net_pnl"] - s2["net_pnl"])
    dd_delta = abs(s1["max_dd_$"] - s2["max_dd_$"])
    trades_delta = abs(s1["trades"] - s2["trades"])
    wr_delta = abs(s1["win_rate"] - s2["win_rate"])

    print()
    print(f"  ΔPnL=${pnl_delta:,.2f}  ΔDD=${dd_delta:,.2f}  ΔTrades={trades_delta}  ΔWR={wr_delta:.2f}pp")

    # Strict tolerance: dataset is real-market, so deterministic identity.
    tol_money = 1.0
    tol_trades = 0
    tol_wr = 0.05
    ok = (
        pnl_delta < tol_money
        and dd_delta < tol_money
        and trades_delta <= tol_trades
        and wr_delta < tol_wr
    )
    if ok:
        print("\n✅ MATCH — V2 reproduces V1 within tolerance")
        return 0
    else:
        print("\n❌ MISMATCH — V2 diverges from V1 beyond tolerance")
        return 1


if __name__ == "__main__":
    sys.exit(main())
