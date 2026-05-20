"""Phase 19 — average / min / max duration of PASS and FAIL evaluations.

For each daily eval started:
  start_time = first trade's entry_time
  end_time   = exit_time of the trade that resolves it (pass or fail)
  duration   = end_time − start_time
"""
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _campaign import (  # noqa: E402
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    MGC_BLACKOUTS_BASE, MNQ_BLACKOUTS_BASE,
    run_multi,
)


START_EQUITY = 50_000.0
DD_LIMIT = 2_000.0
PROFIT_LOCK = 2_000.0


def run_one_eval_with_times(trades_from):
    equity = START_EQUITY
    peak = START_EQUITY
    start_time = pd.Timestamp(trades_from[0]["entry_time"])
    for k, t in enumerate(trades_from, start=1):
        equity += t["pnl"]
        if equity > peak:
            peak = equity
        end_time = pd.Timestamp(t.get("exit_time") or t["entry_time"])
        if peak >= START_EQUITY + PROFIT_LOCK:
            return ("pass", k, end_time - start_time, start_time, end_time)
        if peak - equity >= DD_LIMIT:
            return ("fail", k, end_time - start_time, start_time, end_time)
    return ("pending", len(trades_from), None, start_time, None)


def simulate_daily_evals(trades):
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])
    first_idx_for_date = {}
    for i, t in enumerate(sorted_t):
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts = ts.tz_convert("Europe/Brussels")
        d = ts.date()
        if d not in first_idx_for_date:
            first_idx_for_date[d] = i
    results = []
    for d, idx in sorted(first_idx_for_date.items()):
        outcome, n, dur, st, et = run_one_eval_with_times(sorted_t[idx:])
        results.append({
            "date": str(d), "outcome": outcome, "n_trades": n,
            "duration": dur, "start_time": st, "end_time": et,
        })
    return results


def _fmt(td: pd.Timedelta):
    if td is None:
        return "—"
    total = td.total_seconds()
    days = int(total // 86400)
    hours = int((total % 86400) // 3600)
    minutes = int((total % 3600) // 60)
    if days > 0:
        return f"{days}j {hours:02d}h{minutes:02d}"
    return f"{hours}h{minutes:02d}"


def stats(durations):
    if not durations:
        return None
    arr = sorted(durations)
    n = len(arr)
    mean = sum(arr, pd.Timedelta(0)) / n
    median = arr[n // 2]
    return {"n": n, "min": arr[0], "max": arr[-1], "mean": mean, "median": median}


def print_outcome(label, results, outcome):
    items = [r for r in results if r["outcome"] == outcome]
    durs = [r["duration"] for r in items]
    s = stats(durs)
    if not s:
        print(f"  {label}: aucun")
        return
    print(f"  {label} (n={s['n']})")
    print(f"    moyenne : {_fmt(s['mean'])}")
    print(f"    médiane : {_fmt(s['median'])}")
    print(f"    plus rapide : {_fmt(s['min'])}")
    print(f"    plus lente  : {_fmt(s['max'])}")
    fastest = min(items, key=lambda r: r["duration"])
    slowest = max(items, key=lambda r: r["duration"])
    print(f"    └ plus rapide : début {fastest['start_time'].strftime('%Y-%m-%d %H:%M')} "
          f"→ fin {fastest['end_time'].strftime('%Y-%m-%d %H:%M')}  ({fastest['n_trades']} trades)")
    print(f"    └ plus lente  : début {slowest['start_time'].strftime('%Y-%m-%d %H:%M')} "
          f"→ fin {slowest['end_time'].strftime('%Y-%m-%d %H:%M')}  ({slowest['n_trades']} trades)")


def main():
    print("Replaying WINNER...")
    mgc_params = dict(MGC_PARAMS_BASE)
    mgc_params["sl_max_points"] = 80
    mgc_params["max_candle_pct"] = 0.26
    mgc_params["be_at_rr"] = 2.0
    mnq_params = dict(MNQ_PARAMS_BASE)
    mnq_params["be_at_rr"] = 2.4
    s_winner = run_multi(
        mgc_params=mgc_params, mgc_risk=0.0053,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=mnq_params, mnq_risk=0.00345,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )

    res = simulate_daily_evals(s_winner["_merged"])
    print()
    print("=== WINNER preset — durée des évaluations ===")
    print_outcome("PASS ✅", res, "pass")
    print()
    print_outcome("FAIL ❌", res, "fail")

    print()
    print("─" * 70)
    print()
    print("Replaying BASELINE for comparison...")
    s_base = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    res_b = simulate_daily_evals(s_base["_merged"])
    print()
    print("=== BASELINE preset — durée des évaluations ===")
    print_outcome("PASS ✅", res_b, "pass")
    print()
    print_outcome("FAIL ❌", res_b, "fail")


if __name__ == "__main__":
    main()
