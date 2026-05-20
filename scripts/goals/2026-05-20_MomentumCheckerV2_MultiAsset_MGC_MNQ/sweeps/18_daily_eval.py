"""Phase 18 — Daily prop-firm evaluation start.

User question: if I start a new evaluation EVERY DAY during the backtest
period, how many of those evaluations would pass vs fail?

Each calendar day (Brussels) on which a trade occurs spawns one fresh
evaluation that starts at $50k and walks forward through every
subsequent trade until either:
  PASS  — peak reaches start + $2,000 (locks the trailing rule)
  FAIL  — equity drops $2,000 below peak before lock
  PENDING — neither happened before end of data

Note: 'each day' = each unique calendar date that has at least one trade.
Weekends / market holidays are naturally skipped (no trades to seed an
eval). If the user prefers strict calendar-day inclusion (incl. days
without trades), the count is the same: an eval started on Sat night
just inherits Sunday-night's first trade.
"""
import pandas as pd
from collections import Counter
from pathlib import Path
import sys

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


def run_one_eval(trades_from_idx, start_equity=START_EQUITY,
                 dd_limit=DD_LIMIT, profit_lock=PROFIT_LOCK):
    """Walk an evaluation from a given starting trade index forward.

    Returns ('pass'|'fail'|'pending', n_trades_processed, drop_at_fail_or_None)
    """
    equity = start_equity
    peak = start_equity
    for k, t in enumerate(trades_from_idx, start=1):
        equity += t["pnl"]
        if equity > peak:
            peak = equity
        if peak >= start_equity + profit_lock:
            return ("pass", k, None)
        if peak - equity >= dd_limit:
            return ("fail", k, peak - equity)
    return ("pending", len(trades_from_idx), None)


def simulate_daily_evals(trades):
    """For each unique calendar day (Brussels) with ≥1 trade, run an eval
    that starts at that day's first trade.

    Returns DataFrame of per-eval result.
    """
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])

    # Group: for each Brussels date, find the index of the first trade
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
        outcome, n_trades, drop = run_one_eval(sorted_t[idx:])
        results.append({
            "start_date": str(d),
            "outcome": outcome,
            "n_trades_until_resolve": n_trades,
            "drop_at_fail": drop,
        })
    return results, sorted_t


def print_report(label, results):
    n = len(results)
    by_outcome = Counter(r["outcome"] for r in results)
    print(f"=== {label} ===")
    print(f"  Évaluations totales (= jours actifs avec ≥1 trade) : {n}")
    print(f"  ✅ PASS    : {by_outcome.get('pass', 0):>4}  ({by_outcome.get('pass', 0)/n*100:.1f}%)")
    print(f"  ❌ FAIL    : {by_outcome.get('fail', 0):>4}  ({by_outcome.get('fail', 0)/n*100:.1f}%)")
    print(f"  ⏳ PENDING : {by_outcome.get('pending', 0):>4}  ({by_outcome.get('pending', 0)/n*100:.1f}%)")
    print(f"  (PENDING = évals encore en cours en fin d'historique)")

    fails = [r for r in results if r["outcome"] == "fail"]
    if fails:
        print()
        avg_trades_to_fail = sum(r["n_trades_until_resolve"] for r in fails) / len(fails)
        print(f"  Moyenne trades avant FAIL : {avg_trades_to_fail:.1f}")
        avg_drop = sum(r["drop_at_fail"] for r in fails) / len(fails)
        print(f"  Drop moyen au FAIL        : ${avg_drop:,.0f}")
        # Distribution
        print()
        print(f"  Quelques exemples d'échecs (10 premiers) :")
        for r in fails[:10]:
            print(f"    {r['start_date']}  → FAIL après {r['n_trades_until_resolve']:>3} trades, "
                  f"drop=${r['drop_at_fail']:>5,.0f}")

    pendings = [r for r in results if r["outcome"] == "pending"]
    if pendings:
        print()
        print(f"  Les {len(pendings)} évals PENDING (proches de la fin de l'historique) :")
        for r in pendings:
            print(f"    {r['start_date']}  → encore en cours après {r['n_trades_until_resolve']} trades")


def main():
    # WINNER
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
    print(f"  Trades: {s_winner['trades']}  PnL ${s_winner['net_pnl']:,.0f}  DD ${s_winner['max_dd_$']:,.0f}")
    print()

    res_w, _ = simulate_daily_evals(s_winner["_merged"])
    print_report("WINNER preset — daily eval start", res_w)

    # BASELINE comparison
    print()
    print("─" * 70)
    print()
    print("Replaying BASELINE...")
    s_base = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    res_b, _ = simulate_daily_evals(s_base["_merged"])
    print_report("BASELINE preset — daily eval start", res_b)


if __name__ == "__main__":
    main()
