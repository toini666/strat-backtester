"""Phase 7 (v2) — Master combo: stack Phase-6 winners and explore risk.

Phase-6 winners by category:
  D winner: amp=3.5 + pts_hma_slow=1 ssl=60 hw=5 + sl_max=60 → $71,539/$2,724 (Pareto)
  C winner: amp=3.5 + tick_buffer=2 + stc_slow_len=65 → $69,758/$2,690
  A winner: amp=3.5 + sl=60 → $72,163/$2,900 (best raw PnL)
  B winner: amp=3.5 + tick_buffer=1 → $71,892/$2,883

Sub-strategy goals:
  - Combine best DD-reducers with amp=3.5 to push PnL up at lower $DD
  - Run risk variations on the top 3-4 finalists to map the Pareto curve
"""

from __future__ import annotations

import sys
import time
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, anchor_engine,
)


def _common(risk=RISK_PER_TRADE):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=anchor_engine(),
    )


def _override(**kw):
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 7 (v2) — Master combo with amp=3.5 as core")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[B baseline]", s))

    CORE = {"amp_mult": 3.5}

    # ---- A: 4-way binary lattice of P6 lever winners ----
    # tick_buffer (0 vs 2), pts_hma_slow (0 vs 1 with ssl=60 hw=5),
    # stc_slow_len (50 vs 65), st_atr (10 vs 14)
    print("\n--- A: 4-way binary lattice (16 combos) ---")
    LEVERS = {
        "tick_buffer":   (0, 2),
        "hma_slow":      ("off", "on_60_5"),
        "stc_slow_len":  (50, 65),
        "st_atr":        (14, 10),
    }
    for combo in product(*LEVERS.values()):
        params = dict(CORE)
        tb, hs, stc, sta = combo
        params["tick_buffer"] = tb
        if hs == "on_60_5":
            params.update({"pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5})
        params["stc_slow_len"] = stc
        params["st_atr"] = sta
        label = f"A tb={tb} hs={hs} stc={stc} sta={sta}"
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ---- B: sig_extreme variants on amp=3.5 + best A combos ----
    print("\n--- B: sig_extreme tweaks ---")
    BEST_BASE = {"amp_mult": 3.5,
                 "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5,
                 "tick_buffer": 0, "stc_slow_len": 50, "st_atr": 14}
    for v in [30.0, 35.0, 45.0, 50.0]:
        params = {**BEST_BASE, "sig_extreme": v}
        label = f"B sig_extreme={v}"
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ---- C: candle_pct variations on top ----
    print("\n--- C: max_candle_pct variations ---")
    for v in [0.2, 0.25, 0.35, 0.4, 0.5]:
        params = {**BEST_BASE, "max_candle_pct": v}
        label = f"C max_candle_pct={v}"
        s = bench(label, strategy_params=_override(**params), **_common())
        results.append((label, s))

    # ---- D: risk variations on the 3 leading combos (Pareto curve) ----
    print("\n--- D: risk sweep on leading combos ---")
    LEAD = {
        "D_amp35_hma_slow": {"amp_mult": 3.5,
                              "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5},
        "A_amp35_only":      {"amp_mult": 3.5},
        "C_amp35_tb2_stc65": {"amp_mult": 3.5, "tick_buffer": 2, "stc_slow_len": 65},
    }
    RISKS = [0.0035, 0.0040, 0.0045, 0.0050, 0.0055, 0.0060, 0.0065, 0.0070]
    for cfg_name, cfg in LEAD.items():
        for r in RISKS:
            label = f"D {cfg_name} risk={r*100:.2f}%"
            s = bench(label, strategy_params=_override(**cfg), **_common(risk=r))
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(3074, "V1 ceiling"), (2500, "moderate"), (2000, "TARGET")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 25 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
            print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("Pareto frontier")
    print("=" * 110)
    buckets = [(0, 1500), (1500, 1700), (1700, 1900), (1900, 2100), (2100, 2300),
               (2300, 2500), (2500, 2700), (2700, 2900), (2900, 3074)]
    for lo, hi in buckets:
        configs_in = [(l, s) for l, s in results if lo < s["max_dd_$"] <= hi]
        if configs_in:
            best = max(configs_in, key=lambda x: x[1]["net_pnl"])
            l, s = best
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  PnL=${s['net_pnl']:>7,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")
        else:
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  (no configs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
