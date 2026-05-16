"""Sweep 04 — Risk + daily limits.

v2 winning config so far:
    V2_BASELINE + 4 blackouts (11-12, 06-07, 07-08, 03-04)
    → PnL=$48,979 / DD=$3,147 / P/DD=15.56  @ risk=0.52%

To satisfy goal (PnL > 30k AND DD < 2.5k):
- Need to scale DD from 3,147 → 2,500 (×0.795)
- Linear scaling guess: risk ≈ 0.52 × 0.795 = 0.0041

Sweep risk values around that area, then test daily limits.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)

V2_BASELINE = dict(PREV_WINNER_OVERRIDES)
V2_BASELINE["block_loss_exit_before_partial"] = True
V2_BASELINE["hma1_len"] = 9
V2_BASELINE["max_sl_points"] = 100.0
V2_BASELINE["tick_buffer"] = 1


def w(sh, eh):
    return {"start_hour": sh, "start_minute": 0, "end_hour": eh, "end_minute": 0}


# Winning blackout combo from sweep 06c
WINNER_BO = [w(11, 12), w(6, 7), w(7, 8), w(3, 4)]


def run_one(label, *, risk=PREV_WINNER_RISK,
            win_lim=None, loss_lim=None, mode="after_close"):
    es = make_engine_settings(
        STRATEGY,
        extra_active_windows=WINNER_BO,
        daily_win_limit=win_lim,
        daily_loss_limit=loss_lim,
        daily_limit_mode=mode,
    )
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=V2_BASELINE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    print(f"{label:<70s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 120)
    print("Sweep 04 — Risk + daily limits (on winning 4-blackout config)")
    print("=" * 120)
    run_one("BASELINE risk=0.52%, no daily limits")
    print("-" * 120)

    print("\n## Risk sweep")
    for r in (0.001, 0.0015, 0.002, 0.0025, 0.003, 0.0035, 0.004, 0.0042, 0.0045,
              0.0048, 0.005, 0.0052, 0.0055, 0.0058, 0.006, 0.007, 0.008, 0.010):
        run_one(f"risk={r*100:.2f}%", risk=r)

    print("\n## Daily limits (intra_bar) on risk=0.0052")
    for wl, ll in [(500, 700), (400, 500), (600, 800), (300, 400), (800, 1200), (None, 500)]:
        wl_s = f"+${wl}" if wl else "off"
        ll_s = f"-${ll}" if ll else "off"
        run_one(f"DL win={wl_s} loss={ll_s} intra_bar",
                risk=0.0052, win_lim=wl, loss_lim=ll, mode="intra_bar")

    print("\n## Daily limits (after_close) on risk=0.0052")
    for wl, ll in [(500, 700), (400, 500), (600, 800), (300, 400), (800, 1200), (None, 500)]:
        wl_s = f"+${wl}" if wl else "off"
        ll_s = f"-${ll}" if ll else "off"
        run_one(f"DL win={wl_s} loss={ll_s} after_close",
                risk=0.0052, win_lim=wl, loss_lim=ll, mode="after_close")
