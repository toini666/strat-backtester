"""08 — Micro fine-tune: squeeze last $$ of PnL while keeping DD < $2,400 safe.

Current leader: ema=11 BO 11+14 r=0.0036 → $50,770 / $2,268 (margin $232).
Push:
  - Fine risk ladder between 0.00360 and 0.00370 to find risk wall
  - hpb=1 / hpb=2 on the leading combo
  - Try ema=11 with BO 11+14+12 (filtering instead of H8)
  - Try ema=11 with smaller / different windows (BO h=11:30-12:30)
  - Last-mile: max_sl_points fine-grained on the leader

Sim count: ~15
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from backend.api import BlackoutWindowSettings  # noqa: E402


def _build_windows(specs):
    """specs: list of (sh, sm, eh, em) -> dict."""
    out = []
    for sh, sm, eh, em in specs:
        if eh >= 24:
            eh, em = 23, 59
        out.append({"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em})
    return out


def run(label, window_specs, overrides, risk):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=_build_windows(window_specs),
    )
    params = dict(C.V3_WINNER_PARAMS)
    params.update(overrides)
    return bench(
        f"{label:<55s} r={risk:.5f}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )


def main():
    print(f"=== 08 MICRO FINETUNE — push ema=11 BO 11+14 ===\n")
    BO_11_14 = [(11, 0, 12, 0), (14, 0, 15, 0)]
    BO_11_14_12 = [(11, 0, 12, 0), (14, 0, 15, 0), (12, 0, 13, 0)]
    BO_NARROW_11 = [(11, 0, 11, 30), (14, 0, 15, 0)]
    BO_WIDE_11 = [(11, 0, 12, 30), (14, 0, 15, 0)]
    BO_11_14_HALF = [(11, 0, 12, 0), (14, 0, 14, 30)]

    rows = []

    print("--- Fine risk ladder: ema=11 BO 11+14 ---")
    for r in [0.00360, 0.00365, 0.00368, 0.00370]:
        rows.append((f"ema=11 BO 11+14 r={r}",
                     run("ema=11 BO 11+14", BO_11_14, {"ema_len": 11}, r)))

    print("\n--- hpb variations on ema=11 BO 11+14 ---")
    for hpb in [1, 2]:
        rows.append((f"ema=11 hpb={hpb} BO 11+14 r=0.0037",
                     run(f"ema=11 hpb={hpb} BO 11+14", BO_11_14,
                         {"ema_len": 11, "hma_pol_bars": hpb}, 0.0037)))

    print("\n--- Blackout variants on ema=11 ---")
    rows.append(("ema=11 BO 11+12+14 r=0.0036",
                 run("ema=11 BO 11+12+14", BO_11_14_12, {"ema_len": 11}, 0.0036)))
    rows.append(("ema=11 BO 11:30 narrow r=0.0036",
                 run("ema=11 BO 11:30 narrow", BO_NARROW_11, {"ema_len": 11}, 0.0036)))
    rows.append(("ema=11 BO 12:30 wide r=0.0036",
                 run("ema=11 BO 12:30 wide", BO_WIDE_11, {"ema_len": 11}, 0.0036)))
    rows.append(("ema=11 BO 11+14:30 half r=0.0036",
                 run("ema=11 BO 11+14:30 half", BO_11_14_HALF, {"ema_len": 11}, 0.0036)))

    print("\n--- max_sl on ema=11 BO 11+14 ---")
    for msl in [200.0, 250.0]:
        rows.append((f"ema=11 BO 11+14 msl={msl} r=0.0036",
                     run("ema=11 msl=" + str(msl), BO_11_14,
                         {"ema_len": 11, "max_sl_points": msl}, 0.0036)))

    print("\n--- sig_extreme variants ---")
    for sx in [35, 45]:
        rows.append((f"ema=11 BO 11+14 sx={sx} r=0.0036",
                     run("ema=11 sx=" + str(sx), BO_11_14,
                         {"ema_len": 11, "sig_extreme": sx}, 0.0036)))

    print("\n=== TOP 20 (passing SAFE target $2,400 first) ===")
    def sortkey(row):
        s = row[1]
        passes_safe = s["max_dd_$"] < C.SAFE_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        passes_hard = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes_safe), -int(passes_hard), -s["net_pnl"])
    rows.sort(key=sortkey)
    for label, s in rows[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        margin = C.TARGET_MAX_DD - s["max_dd_$"]
        mark = "✓✓" if (s["max_dd_$"] < C.SAFE_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN) else (
            "✓ " if (s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN) else "  ")
        print(f"  {mark} {label:<50s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f})  "
              f"N={s['trades']}")


if __name__ == "__main__":
    main()
