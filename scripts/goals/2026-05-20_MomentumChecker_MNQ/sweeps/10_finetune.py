"""Phase 10 — Fine-tune around the current best.

Best so far: gap9 + rr2.5 + tickBuf0 + hw_ext=ON + rob=off + hw_extreme=20 +
mf_smooth=5 + st_atr=14 + ema_sec_len=20 + amp_mult=2.5
Plus BO 17:00-21:00 + 13:00-14:00 → PnL=$46,042, DD=$2,237, P/DD=20.59 (DD-valid).

Tuning attempts:
  (a) Blackout edges (17:00 vs 17:30, 21:00 vs 21:30, 12:30 vs 13:00, etc.)
  (b) Risk per trade: 0.4%, 0.5%, 0.6%, 0.7% (preset uses 0.5%)
  (c) Daily limits
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


def _engine(extras: list[tuple[int, int, int, int]],
            daily_win: float | None = None,
            daily_loss: float | None = None,
            daily_mode: str = "after_close"):
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


def _common(engine, risk: float = RISK_PER_TRADE):
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
    print("PHASE 10 — Fine-tune blackout edges + risk + daily limits")
    print("=" * 100)

    t0 = time.time()
    results = []

    bo_base = [(17, 0, 21, 0), (13, 0, 14, 0)]
    base = bench("Phase 9 winner (BO 17-21 + 13-14)", **_common(_engine(bo_base)))
    results.append(("Phase 9 winner", base))

    print()
    print("-" * 100)
    print("BLACKOUT EDGE TUNING")
    print("-" * 100)
    edge_variants = [
        ("BO 17:00-21:00 + 13:00-14:00 (base)",  [(17, 0, 21, 0), (13, 0, 14, 0)]),
        ("BO 17:00-20:30 + 13:00-14:00",          [(17, 0, 20, 30), (13, 0, 14, 0)]),
        ("BO 17:00-20:00 + 13:00-14:00",          [(17, 0, 20, 0), (13, 0, 14, 0)]),
        ("BO 17:30-21:00 + 13:00-14:00",          [(17, 30, 21, 0), (13, 0, 14, 0)]),
        ("BO 17:00-21:00 + 12:30-14:00",          [(17, 0, 21, 0), (12, 30, 14, 0)]),
        ("BO 17:00-21:00 + 13:00-14:30",          [(17, 0, 21, 0), (13, 0, 14, 30)]),
        ("BO 17:00-21:00 + 13:30-14:00",          [(17, 0, 21, 0), (13, 30, 14, 0)]),
        ("BO 16:30-21:00 + 13:00-14:00",          [(16, 30, 21, 0), (13, 0, 14, 0)]),
        ("BO 17:00-21:00 + 13:00-14:00 + 1:00-2:00", [(17, 0, 21, 0), (13, 0, 14, 0), (1, 0, 2, 0)]),
        ("BO 17:00-21:00 + 13:00-14:00 + 18:30-19:30", [(17, 0, 21, 0), (13, 0, 14, 0), (18, 30, 19, 30)]),
        ("BO 17:00-21:00 + 13:00-14:00 + 9:00-10:00", [(17, 0, 21, 0), (13, 0, 14, 0), (9, 0, 10, 0)]),
        ("BO 17:00-22:00 + 13:00-14:00 (extend to close)", [(17, 0, 22, 0), (13, 0, 14, 0)]),
    ]
    for label, windows in edge_variants:
        s = bench(label, **_common(_engine(windows)))
        results.append((label, s))

    print()
    print("-" * 100)
    print("RISK PER TRADE SWEEP (base BO 17-21 + 13-14)")
    print("-" * 100)
    for risk in [0.003, 0.0035, 0.004, 0.0045, 0.005, 0.0055, 0.006, 0.007, 0.008]:
        s = bench(f"risk={risk*100:.2f}%", **_common(_engine(bo_base), risk=risk))
        results.append((f"risk={risk*100:.2f}%", s))

    print()
    print("-" * 100)
    print("DAILY LIMITS (base BO 17-21 + 13-14, risk 0.5%)")
    print("-" * 100)
    limit_variants = [
        ("daily_loss=500 (after_close)",  None, 500.0, "after_close"),
        ("daily_loss=700 (after_close)",  None, 700.0, "after_close"),
        ("daily_loss=1000 (after_close)", None, 1000.0, "after_close"),
        ("daily_loss=500 (intra_bar)",    None, 500.0, "intra_bar"),
        ("daily_loss=700 (intra_bar)",    None, 700.0, "intra_bar"),
        ("daily_loss=1000 (intra_bar)",   None, 1000.0, "intra_bar"),
        ("daily_win=500 / loss=500 (after_close)",  500.0, 500.0, "after_close"),
        ("daily_win=800 / loss=700 (after_close)",  800.0, 700.0, "after_close"),
        ("daily_win=500 / loss=500 (intra_bar)",    500.0, 500.0, "intra_bar"),
        ("daily_win=1000 / loss=700 (intra_bar)",  1000.0, 700.0, "intra_bar"),
    ]
    for label, dw, dl, mode in limit_variants:
        s = bench(label, **_common(_engine(bo_base, daily_win=dw, daily_loss=dl, daily_mode=mode)))
        results.append((label, s))

    print()
    print("-" * 100)
    print("BEST COMBO with edge tuning + daily limits")
    print("-" * 100)
    # try the best edge-tuned blackout we find + daily loss 1000 intra_bar
    combo_pool = [
        ("Edge BO 17-21 + 12:30-14 + DL=1000 intrabar",
         [(17, 0, 21, 0), (12, 30, 14, 0)], None, 1000.0, "intra_bar"),
        ("Edge BO 17-22 + 13-14 + DL=1000 intrabar",
         [(17, 0, 22, 0), (13, 0, 14, 0)], None, 1000.0, "intra_bar"),
        ("Base + DL=1000 intrabar",
         bo_base, None, 1000.0, "intra_bar"),
        ("Base + DL=700 intrabar",
         bo_base, None, 700.0, "intra_bar"),
        ("Base + DL=500 intrabar",
         bo_base, None, 500.0, "intra_bar"),
    ]
    for label, bo, dw, dl, mode in combo_pool:
        s = bench(label, **_common(_engine(bo, daily_win=dw, daily_loss=dl, daily_mode=mode)))
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 20 by absolute PnL")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
