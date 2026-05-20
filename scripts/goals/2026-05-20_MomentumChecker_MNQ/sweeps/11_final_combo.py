"""Phase 11 — Final combo on the DD-valid Pareto frontier.

Phase 10 DD-valid champs:
  risk=0.60%                    → PnL=$56,275 DD=$2,439 P/DD=23.08   ← PnL leader
  BO +9-10 hour                 → PnL=$49,486 DD=$2,237 P/DD=22.13
  daily_win=800/loss=700 (AC)   → PnL=$46,208 DD=$2,025 P/DD=22.82
  daily_win=1000/loss=700 (IB)  → PnL=$44,859 DD=$1,889 P/DD=23.75   ← P/DD leader (low DD)

Stack hypothesis: combining boosters can push PnL further while staying DD-valid.
Risk per trade is the strongest amplifier — find the highest risk that keeps DD ≤ $2,500.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.api import BlackoutWindowSettings

from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


WINNER = dict(BASELINE_PARAMS)
WINNER.update({
    "min_gap": 9,
    "rr_tp": 2.5,
    "tick_buffer": 0,
    "hw_extreme_filter_on": True,
    "rob_on": False,
    "hw_extreme": 20.0,
    "mf_smooth": 5,
    "st_atr": 14,
    "ema_sec_len": 20,
    "amp_mult": 2.5,
})


def _engine(extras, daily_win=None, daily_loss=None, daily_mode="after_close"):
    e = baseline_engine()
    for (sh, sm, eh, em) in extras:
        e.blackout_windows.append(
            BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
        )
    if daily_win is not None:
        e.daily_win_limit_enabled = True
        e.daily_win_limit = daily_win
    if daily_loss is not None:
        e.daily_loss_limit_enabled = True
        e.daily_loss_limit = daily_loss
    e.daily_limit_mode = daily_mode
    return e


def _common(engine, risk=RISK_PER_TRADE):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 100)
    print("PHASE 11 — Final combo on DD-valid Pareto frontier")
    print("=" * 100)

    t0 = time.time()
    results = []

    bo_basic = [(17, 0, 21, 0), (13, 0, 14, 0)]
    bo_plus9 = [(17, 0, 21, 0), (13, 0, 14, 0), (9, 0, 10, 0)]

    # 1) Fine risk sweep on each blackout config
    print()
    print("-" * 100)
    print("Fine risk sweep — bo_basic")
    print("-" * 100)
    for r in [0.0055, 0.0058, 0.006, 0.0061, 0.0062]:
        s = bench(f"basic + risk={r*100:.2f}%", **_common(_engine(bo_basic), risk=r))
        results.append((f"basic + risk={r*100:.2f}%", s))

    print()
    print("-" * 100)
    print("Fine risk sweep — bo_plus9 (BO 17-21 + 13-14 + 9-10)")
    print("-" * 100)
    for r in [0.005, 0.0052, 0.0055, 0.0058, 0.006]:
        s = bench(f"+9-10 + risk={r*100:.2f}%", **_common(_engine(bo_plus9), risk=r))
        results.append((f"+9-10 + risk={r*100:.2f}%", s))

    # 2) Combine blackout + daily limits + risk
    print()
    print("-" * 100)
    print("Combo: blackout + daily limit + various risks")
    print("-" * 100)
    combo_specs = [
        ("basic + DL=700AC + r0.6",  bo_basic, None, 700.0, "after_close", 0.006),
        ("basic + DL=700AC + r0.55", bo_basic, None, 700.0, "after_close", 0.0055),
        ("basic + DW=800/DL=700 + r0.55", bo_basic, 800.0, 700.0, "after_close", 0.0055),
        ("basic + DW=800/DL=700 + r0.6",  bo_basic, 800.0, 700.0, "after_close", 0.006),
        ("basic + DW=1000/DL=700 IB + r0.55", bo_basic, 1000.0, 700.0, "intra_bar", 0.0055),
        ("basic + DW=1000/DL=700 IB + r0.6",  bo_basic, 1000.0, 700.0, "intra_bar", 0.006),
        ("+9-10 + DL=700AC + r0.55", bo_plus9, None, 700.0, "after_close", 0.0055),
        ("+9-10 + DL=1000AC + r0.55", bo_plus9, None, 1000.0, "after_close", 0.0055),
        ("+9-10 + DL=1000IB + r0.55", bo_plus9, None, 1000.0, "intra_bar", 0.0055),
        ("+9-10 + DW=1000/DL=700 IB + r0.55", bo_plus9, 1000.0, 700.0, "intra_bar", 0.0055),
        ("+9-10 + DW=1000/DL=700 IB + r0.5", bo_plus9, 1000.0, 700.0, "intra_bar", 0.005),
        ("+9-10 + DW=800/DL=700 AC + r0.55", bo_plus9, 800.0, 700.0, "after_close", 0.0055),
        ("+9-10 + DW=800/DL=700 AC + r0.6", bo_plus9, 800.0, 700.0, "after_close", 0.006),
    ]
    for label, bo, dw, dl, mode, risk in combo_specs:
        s = bench(label, **_common(_engine(bo, daily_win=dw, daily_loss=dl, daily_mode=mode), risk=risk))
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL — final shortlist")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")
    if not dd_valid:
        print("  (none)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
