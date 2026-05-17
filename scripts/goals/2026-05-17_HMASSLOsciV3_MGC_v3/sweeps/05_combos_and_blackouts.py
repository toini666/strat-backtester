"""05 — Combos of 1D winners + blackout additions.

Winners from sweep 04 (DD<2000):
  - entry_window_bars=3 (DD$1,565)
  - hw_extreme=18 (DD$1,590)
  - tick_buffer=2 (DD$1,734)

Blackout candidates (from sweep 01 hour bucket):
  - H=17 (-$1,112, 52% WR) — V2 noted it dégrade légèrement; re-check on V3 base
  - H=21 (-$336, 47% WR) — small
  - H=22 (-$360, 33% WR) — only 15 trades but very low WR
  - H=10 (+$1,435 but maybe DD reducer)
  - H=16 (+$966 marginal)

Sims used: ~25 / 200 → cumulative ~117/200
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
    V2_WINNER_OVERRIDES, V2_WINNER_RISK, V2_WINNER_BLACKOUTS,
    pdd,
)


CLOUD_BASE = dict(V2_WINNER_OVERRIDES)
CLOUD_BASE.update({"cloud_on": True, "mf_length": 29, "mf_smooth": 5})


def _es(extra_bos):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in (list(V2_WINNER_BLACKOUTS) + list(extra_bos))
        ],
    )


def _run(label, overrides, extra_bos=(), risk=V2_WINNER_RISK):
    p = dict(CLOUD_BASE)
    p.update(overrides)
    s = bench(
        label,
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=p, initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk, max_contracts=MAX_CONTRACTS,
        engine_settings=_es(extra_bos),
    )
    return s


def main():
    results = []

    print("=" * 80)
    print("05-A — pairwise + triple combos of param winners")
    print("=" * 80)
    results.append(_run("BASE", {}))
    results.append(_run("ew=3",                       {"entry_window_bars": 3}))
    results.append(_run("hw_ext=18",                  {"hw_extreme": 18}))
    results.append(_run("tb=2",                       {"tick_buffer": 2}))
    results.append(_run("ew=3 + hw_ext=18",           {"entry_window_bars": 3, "hw_extreme": 18}))
    results.append(_run("ew=3 + tb=2",                {"entry_window_bars": 3, "tick_buffer": 2}))
    results.append(_run("hw_ext=18 + tb=2",           {"hw_extreme": 18, "tick_buffer": 2}))
    results.append(_run("ew=3 + hw_ext=18 + tb=2",    {"entry_window_bars": 3, "hw_extreme": 18, "tick_buffer": 2}))
    # hw_extreme=15 was slightly lower PnL but same DD as 18 — sanity
    results.append(_run("ew=3 + hw_ext=15 + tb=2",    {"entry_window_bars": 3, "hw_extreme": 15, "tick_buffer": 2}))

    # Pick best of param combos (by ratio)
    print()
    pcombo = sorted(results[1:], key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    best = pcombo[0]
    print(f"BEST PARAM COMBO: {best['label']} → PnL=${best['net_pnl']:,.0f} DD=${best['max_dd_$']:,.0f} P/DD={pdd(best['net_pnl'], best['max_dd_$']):.2f}")

    # Parse best label back to overrides
    overrides = {}
    parts = best["label"].split(" + ")
    for p in parts:
        if p.startswith("ew="): overrides["entry_window_bars"] = int(p.split("=")[1])
        elif p.startswith("hw_ext="): overrides["hw_extreme"] = float(p.split("=")[1])
        elif p.startswith("tb="): overrides["tick_buffer"] = int(p.split("=")[1])

    print()
    print("=" * 80)
    print(f"05-B — blackout single additions on top of {best['label']}")
    print("=" * 80)
    for bo in [(17, 0, 18, 0), (21, 0, 22, 0), (10, 0, 11, 0),
               (16, 0, 17, 0), (8, 0, 9, 0), (15, 0, 16, 0)]:
        sh, sm, eh, em = bo
        results.append(_run(f"BEST + BO {sh:02d}-{eh:02d}", overrides, extra_bos=[bo]))

    print()
    print("=" * 80)
    print("05-C — additive blackouts on top of best single BO")
    print("=" * 80)
    # Find best single BO addition
    single_bos = [r for r in results if r["label"].startswith("BEST + BO")]
    single_bos.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    top_bos = single_bos[:3]
    print("Top 3 single BOs:")
    for r in top_bos:
        print(f"  {r['label']:<35} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={pdd(r['net_pnl'], r['max_dd_$']):.2f}")

    # Pairwise
    def parse_bo(label):
        # "BEST + BO HH-HH" → (start, 0, end, 0)
        seg = label.split("BO ")[1]
        sh, eh = seg.split("-")
        return (int(sh), 0, int(eh), 0)

    if len(top_bos) >= 2:
        bo1 = parse_bo(top_bos[0]["label"])
        bo2 = parse_bo(top_bos[1]["label"])
        results.append(_run(f"BEST + 2BO {bo1[0]:02d}+{bo2[0]:02d}", overrides, extra_bos=[bo1, bo2]))
    if len(top_bos) >= 3:
        bo1 = parse_bo(top_bos[0]["label"])
        bo3 = parse_bo(top_bos[2]["label"])
        results.append(_run(f"BEST + 2BO {bo1[0]:02d}+{bo3[0]:02d}", overrides, extra_bos=[bo1, bo3]))
        bo2 = parse_bo(top_bos[1]["label"])
        results.append(_run(f"BEST + 3BO {bo1[0]:02d}+{bo2[0]:02d}+{bo3[0]:02d}",
                            overrides, extra_bos=[bo1, bo2, bo3]))

    print()
    print("=" * 80)
    print("ALL RESULTS — TOP 15 by ratio (DD<2000)")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    for r in safe[:15]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        passed = "✅" if (r["net_pnl"] > 30_000 and r["max_dd_$"] < 2_000) else "  "
        print(f"  {passed} {r['label']:<45} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
