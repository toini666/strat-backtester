"""Phase 4 — 1-D sweep over each of the 9 V4-new exit/entry levers.

Baseline = V4 with neutral defaults (= reproduces V3).

V4 new params:
  • reject_entry_at_sl_extreme : bool
  • move_to_be_on_fast_hma_cross: bool
  • final_exit_min_rr           : float (numeric sweep)
  • move_to_be_on_rejected_exit : bool (pertinent if RR > 0 or report_tp_if_mfi_ok)
  • early_exit_fired_mode       : str ('off','hw_rr','canal_inverse','next_slow_cross')
  • block_entry_if_both_windows : bool
  • tp_mode_fast_hma_hw         : bool (test OFF only in combo with slow_cross=True)
  • tp_mode_slow_hma_cross      : bool
  • report_tp_if_mfi_ok         : bool (only acts if tp_mode_fast_hma_hw=True)

Verdict KEEP / REJECT / MIXED per param.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
)


def _engine():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
    )


def _common():
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )


def _verdict(s_base: dict, s_new: dict) -> str:
    ratio_base = s_base["net_pnl"] / max(s_base["max_dd_$"], 1.0)
    ratio_new = s_new["net_pnl"] / max(s_new["max_dd_$"], 1.0)
    if s_new["max_dd_$"] >= 2000:
        return "❌ REJECT (DD>$2k)"
    if ratio_new > ratio_base * 1.03 and s_new["net_pnl"] >= s_base["net_pnl"] * 0.95:
        return "✅ KEEP"
    if ratio_new < ratio_base * 0.97 or s_new["net_pnl"] < s_base["net_pnl"] * 0.80:
        return "❌ REJECT"
    return "≈ MIXED"


def main() -> int:
    print("=" * 110)
    print(f"PHASE 4 — V4-new exit/entry params  |  TF={INTERVAL}  baseline = V3-migrated (neutral V4)")
    print("=" * 110)

    base = bench("V4 baseline (neutral V4 defaults)", strategy_params=BASELINE_V4_PARAMS, **_common())
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"\nBaseline P/DD ratio = {base_ratio:.1f}\n")

    rows = []

    def run_variant(name: str, overrides: dict):
        params = dict(BASELINE_V4_PARAMS)
        params.update(overrides)
        s = bench(name, strategy_params=params, **_common())
        rows.append((name, overrides, s, _verdict(base, s)))
        return s

    # 1. reject_entry_at_sl_extreme: bool
    print("\n--- reject_entry_at_sl_extreme")
    run_variant("reject_entry_at_sl_extreme=True", {"reject_entry_at_sl_extreme": True})

    # 2. move_to_be_on_fast_hma_cross: bool
    print("\n--- move_to_be_on_fast_hma_cross")
    run_variant("move_to_be_on_fast_hma_cross=True", {"move_to_be_on_fast_hma_cross": True})

    # 3. final_exit_min_rr: numeric (0=baseline, sweep)
    print("\n--- final_exit_min_rr (numeric sweep)")
    for rr in [0.5, 1.0, 1.5, 2.0]:
        run_variant(f"final_exit_min_rr={rr}", {"final_exit_min_rr": rr})

    # 4. move_to_be_on_rejected_exit: bool (combined with rr>0 for meaningful effect)
    print("\n--- move_to_be_on_rejected_exit")
    run_variant("move_to_be_on_rejected_exit=True (alone)", {"move_to_be_on_rejected_exit": True})
    run_variant("move_to_be_on_rejected_exit=True + min_rr=1.0",
                {"move_to_be_on_rejected_exit": True, "final_exit_min_rr": 1.0})

    # 5. early_exit_fired_mode: categorical
    print("\n--- early_exit_fired_mode")
    for mode in ["hw_rr", "canal_inverse", "next_slow_cross"]:
        run_variant(f"early_exit_fired_mode={mode}", {"early_exit_fired_mode": mode})

    # 6. block_entry_if_both_windows: bool
    print("\n--- block_entry_if_both_windows")
    run_variant("block_entry_if_both_windows=True", {"block_entry_if_both_windows": True})

    # 7. tp_mode_fast_hma_hw: bool — must combine with slow_cross=True (else no TP path)
    print("\n--- tp_mode_fast_hma_hw (alone is dangerous; test combos)")
    run_variant("tp_mode_fast=False + slow=True",
                {"tp_mode_fast_hma_hw": False, "tp_mode_slow_hma_cross": True})

    # 8. tp_mode_slow_hma_cross: bool (alone)
    print("\n--- tp_mode_slow_hma_cross (alone)")
    run_variant("tp_mode_slow_hma_cross=True", {"tp_mode_slow_hma_cross": True})

    # 9. report_tp_if_mfi_ok: bool
    print("\n--- report_tp_if_mfi_ok")
    run_variant("report_tp_if_mfi_ok=True", {"report_tp_if_mfi_ok": True})

    # Verdict table
    print()
    print("=" * 110)
    print("V4 LEVER VERDICTS")
    print("=" * 110)
    print(f"{'Variant':<55}{'PnL':>11}{'ΔPnL':>10}{'DD':>9}{'ΔDD':>9}{'P/DD':>8}  Verdict")
    print("-" * 110)
    keepers = []
    for name, overrides, s, verdict in rows:
        dpnl = s["net_pnl"] - base["net_pnl"]
        ddd = s["max_dd_$"] - base["max_dd_$"]
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"{name:<55}${s['net_pnl']:>9,.0f}{dpnl:>+10,.0f}"
              f"${s['max_dd_$']:>7,.0f}{ddd:>+9,.0f}{ratio:>8.1f}  {verdict}")
        if "KEEP" in verdict:
            keepers.append((name, overrides, s, ratio))

    print()
    if keepers:
        print("KEEPERS for Phase 8 combo:")
        for name, _, s, ratio in keepers:
            print(f"  • {name}  →  P/DD={ratio:.1f}  PnL=${s['net_pnl']:,.0f}  DD=${s['max_dd_$']:,.0f}")
    else:
        print("No V4 levers improved on the V3 baseline by ≥3% P/DD ratio.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
