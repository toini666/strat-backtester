"""Phase 3 — analyze the worst peak-to-trough sequence on the combined curve.

Find which dates / hours / leg drives the worst DD and try targeted blocks.
"""
import pandas as pd
from collections import defaultdict
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi, INITIAL_EQUITY,
)


def analyze_worst_dd(merged_trades, initial_equity=INITIAL_EQUITY):
    """Walk the combined equity curve and isolate the worst peak-to-trough."""
    active = [t for t in merged_trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])
    equity = initial_equity
    peak = initial_equity
    peak_idx = -1  # index in sorted_t where peak occurred
    max_dd = 0.0
    dd_start_idx = -1  # trade at peak (before the drawdown started)
    dd_end_idx = -1
    for i, t in enumerate(sorted_t):
        equity += t["pnl"]
        if equity > peak:
            peak = equity
            peak_idx = i
        dollar_dd = peak - equity
        if dollar_dd > max_dd:
            max_dd = dollar_dd
            dd_start_idx = peak_idx
            dd_end_idx = i

    if dd_start_idx < 0 or dd_end_idx < 0:
        return None

    dd_trades = sorted_t[dd_start_idx + 1: dd_end_idx + 1]
    start_t = sorted_t[dd_start_idx] if dd_start_idx >= 0 else None
    end_t = sorted_t[dd_end_idx]
    return {
        "max_dd_$": max_dd,
        "peak_equity": peak,
        "start_time": start_t["exit_time"] if start_t else "Start",
        "end_time": end_t["exit_time"],
        "dd_trades": dd_trades,
        "n_dd_trades": len(dd_trades),
    }


def main():
    # Use the best <$2,500 baseline so far
    s = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0050,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0030,
    )
    print(f"Anchor: MGC=0.50% MNQ=0.30% — {fmt_multi(s)}")

    info = analyze_worst_dd(s["_merged"])
    print()
    print(f"Worst DD episode: ${info['max_dd_$']:,.0f}")
    print(f"  Peak at: {info['start_time']} (equity ≈ ${info['peak_equity']:,.0f})")
    print(f"  Trough:  {info['end_time']}")
    print(f"  Trades in drawdown: {info['n_dd_trades']}")

    # Break down DD trades by leg, hour, day
    by_leg = defaultdict(lambda: {"pnl": 0.0, "n": 0, "wins": 0, "losses": 0})
    by_hour = defaultdict(lambda: {"pnl": 0.0, "n": 0})
    by_date = defaultdict(lambda: {"pnl": 0.0, "n": 0, "mgc": 0.0, "mnq": 0.0})

    for t in info["dd_trades"]:
        leg = t.get("_leg", "?")
        ts = pd.Timestamp(t["entry_time"])
        h = ts.tz_convert("Europe/Brussels").hour if ts.tzinfo else ts.hour
        d = str(ts.tz_convert("Europe/Brussels").date()) if ts.tzinfo else str(ts.date())
        pnl = t["pnl"]
        by_leg[leg]["pnl"] += pnl
        by_leg[leg]["n"] += 1
        if pnl > 0:
            by_leg[leg]["wins"] += 1
        else:
            by_leg[leg]["losses"] += 1
        by_hour[h]["pnl"] += pnl
        by_hour[h]["n"] += 1
        by_date[d]["pnl"] += pnl
        by_date[d]["n"] += 1
        if leg == "MGC":
            by_date[d]["mgc"] += pnl
        else:
            by_date[d]["mnq"] += pnl

    print()
    print("=== Breakdown by leg in DD episode ===")
    for leg, st in by_leg.items():
        print(f"  {leg}: pnl=${st['pnl']:+,.0f}  N={st['n']}  W={st['wins']}/L={st['losses']}")

    print()
    print("=== Breakdown by hour in DD episode (sorted by pnl) ===")
    for h, st in sorted(by_hour.items(), key=lambda x: x[1]["pnl"]):
        print(f"  H={h:>2}: pnl=${st['pnl']:+8,.0f}  N={st['n']}")

    print()
    print("=== Worst days in DD episode (sorted by pnl) ===")
    for d, st in sorted(by_date.items(), key=lambda x: x[1]["pnl"])[:15]:
        print(f"  {d}: pnl=${st['pnl']:+8,.0f}  N={st['n']}  MGC=${st['mgc']:+,.0f} MNQ=${st['mnq']:+,.0f}")

    print()
    print("=== Worst 20 trades in DD episode ===")
    for t in sorted(info["dd_trades"], key=lambda x: x["pnl"])[:20]:
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts_str = ts.tz_convert("Europe/Brussels").strftime("%Y-%m-%d %H:%M")
        else:
            ts_str = ts.strftime("%Y-%m-%d %H:%M")
        print(f"  {t.get('_leg','?')} {ts_str} {t.get('direction','?'):<5s} pnl=${t['pnl']:+8,.0f} contracts={t.get('contracts','?')}")


if __name__ == "__main__":
    main()
