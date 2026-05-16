"""06 — Combine top sweep-05 movers on best blackout combo.

Sweep 05 discoveries:
  ema_len=11      → $48,592 / $2,073 / ratio 23.44 (HUGE)
  mf_length=35    → $43,956 / $2,378 / ratio 18.48
  amp_mult=2.5    → $45,942 / $3,627 (DD over but PnL strong)
  ewb=4           → $43,318 / $2,825 (DD over)
  hw_extreme=15   → $39,172 / $2,498 (marginal)
  ssl_mult        → NO-OP (filter not active in this combo)

Strategy:
  1. ema_len fine-grained: {10, 11, 12} on BO 11+14+08 + r=0.0034
  2. ema_len=11 risk ladder
  3. ema_len=11 + mf_length=35 risk ladder
  4. ema_len=11 + (amp_mult=2.5 OR ewb=4) risk ladder
  5. ema_len=11 + various blackout combos
  6. ema_len=11 + mf_length=35 + best blackout combo

Sim count: ~35
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


def _window_dict(start_h, end_h):
    if end_h >= 24:
        return {"start_hour": start_h, "start_minute": 0, "end_hour": 23, "end_minute": 59}
    return {"start_hour": start_h, "start_minute": 0, "end_hour": end_h, "end_minute": 0}


def run(label, windows, overrides, risk=0.0034):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in windows],
    )
    params = dict(C.V3_WINNER_PARAMS)
    params.update(overrides)
    return bench(
        f"{label:<55s} r={risk:.4f}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )


def main():
    print(f"=== 06 COMBOS — ema_len discoveries + blackouts ===\n")
    BO_3 = [(11, 12), (14, 15), (8, 9)]
    BO_2 = [(11, 12), (14, 15)]
    BO_4 = [(11, 12), (14, 15), (8, 9), (6, 7)]

    rows = []

    print("--- ema_len fine-grained (BO 11+14+08, r=0.0034) ---")
    for v in [10, 11, 12]:
        rows.append((f"ema={v}", run(f"ema={v}", BO_3, {"ema_len": v})))

    print("\n--- ema_len=11 risk ladder (BO 11+14+08) ---")
    for r in [0.0032, 0.0034, 0.0036, 0.0038, 0.0040, 0.0042, 0.0044]:
        rows.append((f"ema=11 r={r}", run("ema=11", BO_3, {"ema_len": 11}, r)))

    print("\n--- ema_len=11 + mf_length=35 risk ladder ---")
    for r in [0.0034, 0.0036, 0.0038, 0.0040, 0.0042]:
        rows.append((f"ema=11 mf=35 r={r}",
                     run("ema=11 mf=35", BO_3, {"ema_len": 11, "mf_length": 35}, r)))

    print("\n--- ema_len=11 + amp=2.5 risk ladder ---")
    for r in [0.0030, 0.0032, 0.0034, 0.0036]:
        rows.append((f"ema=11 amp=2.5 r={r}",
                     run("ema=11 amp=2.5", BO_3, {"ema_len": 11, "amp_mult": 2.5}, r)))

    print("\n--- ema_len=11 + ewb=4 risk ladder ---")
    for r in [0.0030, 0.0032, 0.0034, 0.0036]:
        rows.append((f"ema=11 ewb=4 r={r}",
                     run("ema=11 ewb=4", BO_3, {"ema_len": 11, "entry_window_bars": 4}, r)))

    print("\n--- ema_len=11 on different blackout sets (r=0.0036) ---")
    for label, bo in [("BO 11+14", BO_2), ("BO 11+14+08+06", BO_4)]:
        rows.append((f"ema=11 {label}",
                     run(f"ema=11 {label}", bo, {"ema_len": 11}, 0.0036)))

    print("\n--- ema_len=11 + mf=35 + ewb=4 risk ladder ---")
    for r in [0.0032, 0.0034, 0.0036, 0.0038]:
        rows.append((f"ema=11 mf=35 ewb=4 r={r}",
                     run("ema=11 mf=35 ewb=4", BO_3,
                         {"ema_len": 11, "mf_length": 35, "entry_window_bars": 4}, r)))

    print("\n=== TOP 30 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:30]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<38s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
