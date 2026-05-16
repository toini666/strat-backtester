"""05 — Unexplored strategy params (1-D sweep on best blackout combo).

Base = v3 winner + BO 11+14+08 + r=0.0034 + cd=3 = $40,412 / $2,151 / ratio 18.79

v3 sweep 03 was killed mid-flight — only signal_length, sig_extreme, partial
hyper_wave_length were tested. The full v3 parameter space remains unexplored.

Sweep 1-D on each param:
  entry_window_bars, hma_pol_bars, ssl_len, ssl_mult, amp_mult,
  ema_len, hma1_len, hma2_len, hyper_wave_length, mf_length, mf_smooth, hw_extreme.

Sim count: ~32
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


BO_3 = [(11, 12), (14, 15), (8, 9)]
RISK = 0.0034


def run(label, overrides):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in BO_3],
    )
    params = dict(C.V3_WINNER_PARAMS)
    params.update(overrides)
    return bench(
        f"{label:<55s}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=RISK,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )


def main():
    print(f"=== 05 STRATEGY PARAMS 1-D — BO=11+14+08, r=0.0034 ===\n")

    rows = []
    rows.append(("REF base", run("REF base", {})))

    print("\n--- entry_window_bars (current 3) ---")
    for v in [2, 4, 5, 6, 8]:
        rows.append((f"ewb={v}", run(f"entry_window_bars={v}", {"entry_window_bars": v})))

    print("\n--- hma_pol_bars (current 0) ---")
    for v in [1, 2, 3, 5]:
        rows.append((f"hpb={v}", run(f"hma_pol_bars={v}", {"hma_pol_bars": v})))

    print("\n--- ssl_len (current 80) ---")
    for v in [40, 60, 100, 120]:
        rows.append((f"ssl_len={v}", run(f"ssl_len={v}", {"ssl_len": v})))

    print("\n--- ssl_mult (current 0.2) ---")
    for v in [0.1, 0.15, 0.25, 0.3]:
        rows.append((f"ssl_mult={v}", run(f"ssl_mult={v}", {"ssl_mult": v})))

    print("\n--- amp_mult (current 2.0) ---")
    for v in [1.5, 2.5, 3.0]:
        rows.append((f"amp_mult={v}", run(f"amp_mult={v}", {"amp_mult": v})))

    print("\n--- ema_len (current 13) ---")
    for v in [9, 11, 15, 17]:
        rows.append((f"ema_len={v}", run(f"ema_len={v}", {"ema_len": v})))

    print("\n--- hma1_len / hma2_len ---")
    for v in [9, 17]:
        rows.append((f"hma1_len={v}", run(f"hma1_len={v}", {"hma1_len": v})))
    for v in [17, 25]:
        rows.append((f"hma2_len={v}", run(f"hma2_len={v}", {"hma2_len": v})))

    print("\n--- hyper_wave_length (current 7) ---")
    for v in [5, 9]:
        rows.append((f"hwl={v}", run(f"hyper_wave_length={v}", {"hyper_wave_length": v})))

    print("\n--- mf_length / mf_smooth ---")
    for v in [35, 45]:
        rows.append((f"mf_length={v}", run(f"mf_length={v}", {"mf_length": v})))
    for v in [4, 8]:
        rows.append((f"mf_smooth={v}", run(f"mf_smooth={v}", {"mf_smooth": v})))

    print("\n--- hw_extreme (current 20) ---")
    for v in [15, 25]:
        rows.append((f"hw_extreme={v}", run(f"hw_extreme={v}", {"hw_extreme": v})))

    print("\n=== TOP 25 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<30s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
