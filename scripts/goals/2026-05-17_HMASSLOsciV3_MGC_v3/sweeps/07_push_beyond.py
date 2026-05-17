"""07 — Push beyond A r=0.0052 ($44,692 / $1,944).

Hypotheses to test:
  D1: A base + BO 21-22 (no ew=3) — does the extra BO compound with A?
  D2: A base + hw_extreme=18 with risk push (could free more DD margin)
  D3: 1-D risk in 0.0001 steps around best to find sweet spots in non-monotone
  D4: Daily limits sanity check on best (V5 confirmed dégrade)

Sims used: ~25 / 200 → cumulative ~187/200
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402

from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END,
    INITIAL_EQUITY, MAX_CONTRACTS,
    V2_WINNER_OVERRIDES, V2_WINNER_BLACKOUTS,
    pdd,
)


CLOUD_BASE = dict(V2_WINNER_OVERRIDES)
CLOUD_BASE.update({"cloud_on": True, "mf_length": 29, "mf_smooth": 5})


def _es(extra_bos, *, dl_win=None, dl_loss=None, dl_mode="after_close"):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in (list(V2_WINNER_BLACKOUTS) + list(extra_bos))
        ],
        daily_win_limit=dl_win,
        daily_loss_limit=dl_loss,
        daily_limit_mode=dl_mode,
    )


def _run(label, overrides, extra_bos, risk, **dl):
    p = dict(CLOUD_BASE)
    p.update(overrides)
    s = bench(
        label,
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=p, initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk, max_contracts=MAX_CONTRACTS,
        engine_settings=_es(extra_bos, **dl),
    )
    return s


def main():
    results = []

    print("=" * 80)
    print("07-D1 — A base (no ew=3) + BO 21-22 with risk sweep")
    print("=" * 80)
    for r in [0.0048, 0.0050, 0.0052, 0.0054, 0.0056]:
        results.append(_run(f"A+BO21 r={r:.4f}", {}, [(21, 0, 22, 0)], r))

    print()
    print("=" * 80)
    print("07-D2 — A base + hw_extreme=18 with risk push (lower DD baseline)")
    print("=" * 80)
    for r in [0.0050, 0.0055, 0.0060, 0.0065]:
        results.append(_run(f"A+hwe18 r={r:.4f}", {"hw_extreme": 18}, [], r))

    print()
    print("=" * 80)
    print("07-D3 — Fine risk grid around A r=0.0052 (find sweet spots in non-monotone)")
    print("=" * 80)
    for r in [0.0051, 0.0053]:
        results.append(_run(f"A r={r:.4f}", {}, [], r))
    # Same for B
    for r in [0.0053, 0.0055]:
        results.append(_run(f"B r={r:.4f}", {"entry_window_bars": 3}, [], r))

    print()
    print("=" * 80)
    print("07-D4 — Daily limits sanity check on best (A r=0.0052)")
    print("=" * 80)
    results.append(_run("A r=0.0052 DL intra +500/-700", {}, [], 0.0052,
                        dl_win=500, dl_loss=700, dl_mode="intra_bar"))
    results.append(_run("A r=0.0052 DL after +500/-700", {}, [], 0.0052,
                        dl_win=500, dl_loss=700, dl_mode="after_close"))
    results.append(_run("A r=0.0052 DL after +800/-500", {}, [], 0.0052,
                        dl_win=800, dl_loss=500, dl_mode="after_close"))

    print()
    print("=" * 80)
    print("TOP 15 by PnL (DD<2000)")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in safe[:15]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        margin = 2_000 - r["max_dd_$"]
        print(f"  {r['label']:<45} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f}) P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
