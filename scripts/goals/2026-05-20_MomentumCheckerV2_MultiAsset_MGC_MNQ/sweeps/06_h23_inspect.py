"""Phase 6 — list the MGC H=23 trades. Why aren't they blocked by 22-23:59?"""
import pandas as pd
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi,
)


def main():
    mgc_p = dict(MGC_PARAMS_BASE)
    mgc_p["sl_max_points"] = 80
    s = run_multi(
        mgc_params=mgc_p, mgc_risk=0.0050,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0030,
    )
    mgc_trades = [t for t in s["_merged"] if t.get("_leg") == "MGC"]

    print("=== MGC trades with entry hour=23 (Brussels wall-clock) ===")
    for t in mgc_trades:
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts = ts.tz_convert("Europe/Brussels")
        if ts.hour == 23:
            month = ts.month
            dst = "summer (CEST)" if 4 <= month <= 9 else "winter/transition (CET)"
            print(f"  {ts.strftime('%Y-%m-%d %H:%M')} ({dst}) {t.get('direction','?')} pnl=${t['pnl']:+,.0f}")

    print()
    print("=== MGC trades with entry hour=12 (Brussels wall-clock) ===")
    for t in mgc_trades:
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts = ts.tz_convert("Europe/Brussels")
        if ts.hour == 12:
            month = ts.month
            dst = "summer" if 4 <= month <= 9 else "winter"
            print(f"  {ts.strftime('%Y-%m-%d %H:%M')} ({dst}) {t.get('direction','?')} pnl=${t['pnl']:+,.0f}")


if __name__ == "__main__":
    main()
