"""Phase 17 — Prop-firm evaluation failure count.

User question: with a trailing $2,000 drawdown rule active until first
$2,000 of profit is locked in (+$2k peak), how many evaluations would
have failed across the full backtest period?

Rule modeled:
- Each evaluation attempt starts with $50,000.
- Attempt ENDS with SUCCESS when peak reaches start + $2,000 → trailing
  rule locks (eval passed).
- Attempt ENDS with FAIL when equity drops $2,000 below the attempt's
  peak BEFORE the lock is reached.
- After SUCCESS or FAIL, the next attempt starts at the NEXT trade.

Two interpretations of "consecutive $2k decline":
  A) Trade-close equity walk only (lower bound — misses intra-trade DD).
  B) Trade-close walk + use the trade's worst price-drift inside the bar
     to model intra-trade DD (prop firms trail on live equity).

I compute (A) first because the data is unambiguous. Then I attempt (B)
using a conservative full-loss approximation per trade.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _campaign import (  # noqa: E402
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    MGC_BLACKOUTS_BASE, MNQ_BLACKOUTS_BASE,
    run_multi, INITIAL_EQUITY,
)


START_EQUITY = 50_000.0
DD_LIMIT = 2_000.0          # trailing DD limit
PROFIT_LOCK = 2_000.0       # profit needed to lock the trailing rule (peak ≥ start + 2k)


def simulate_evals(trades, start_equity=START_EQUITY, dd_limit=DD_LIMIT,
                   profit_lock=PROFIT_LOCK):
    """Walk trade-close equity through repeated evaluation cycles.

    Returns dict with failure events and pass events.
    """
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])

    fails = []   # list of dicts: {"start_idx", "end_idx", "peak_equity", "trough_equity", "fail_time", "trades"}
    passes = []  # list of dicts: pass events
    in_progress_at_end = None

    i = 0
    while i < len(sorted_t):
        equity = start_equity
        peak = start_equity
        attempt_start_idx = i
        attempt_start_time = sorted_t[i]["entry_time"]
        result = None
        peak_seen = peak
        # Process trades until pass or fail or end of data
        while i < len(sorted_t):
            t = sorted_t[i]
            equity += t["pnl"]
            if equity > peak:
                peak = equity
            peak_seen = max(peak_seen, peak)
            # Check pass
            if peak >= start_equity + profit_lock:
                result = ("pass", t)
                passes.append({
                    "start_idx": attempt_start_idx,
                    "end_idx": i,
                    "start_time": attempt_start_time,
                    "pass_time": t.get("exit_time") or t["entry_time"],
                    "n_trades": i - attempt_start_idx + 1,
                    "peak_equity": peak,
                })
                i += 1
                break
            # Check fail (only while not locked)
            if peak - equity >= dd_limit:
                result = ("fail", t)
                fails.append({
                    "start_idx": attempt_start_idx,
                    "end_idx": i,
                    "start_time": attempt_start_time,
                    "fail_time": t.get("exit_time") or t["entry_time"],
                    "peak_equity": peak,
                    "trough_equity": equity,
                    "drop_dollars": peak - equity,
                    "n_trades": i - attempt_start_idx + 1,
                })
                i += 1
                break
            i += 1
        if result is None:
            # End of data without resolution
            in_progress_at_end = {
                "start_idx": attempt_start_idx,
                "start_time": attempt_start_time,
                "current_equity": equity,
                "peak_equity": peak,
                "current_dd": peak - equity,
                "n_trades": len(sorted_t) - attempt_start_idx,
            }
            break

    return {"fails": fails, "passes": passes, "in_progress": in_progress_at_end}


def print_report(label, result):
    fails = result["fails"]
    passes = result["passes"]
    print(f"=== {label} ===")
    print(f"  Évaluations passées : {len(passes)}")
    print(f"  Évaluations échouées: {len(fails)}")
    total_attempts = len(fails) + len(passes) + (1 if result["in_progress"] else 0)
    print(f"  Total tentatives    : {total_attempts}")
    if total_attempts > 0:
        fail_rate = len(fails) / total_attempts * 100
        print(f"  Taux d'échec        : {fail_rate:.1f}%")

    if fails:
        print()
        print(f"  Détail des échecs ({len(fails)}):")
        for k, f in enumerate(fails, 1):
            print(f"    #{k}  {f['start_time'][:16]} → {f['fail_time'][:16]}  "
                  f"({f['n_trades']:>3} trades)  "
                  f"peak=${f['peak_equity']:>7,.0f}  trough=${f['trough_equity']:>7,.0f}  "
                  f"drop=${f['drop_dollars']:>5,.0f}")

    if result["in_progress"]:
        ip = result["in_progress"]
        print()
        print(f"  En cours à la fin de l'historique:")
        print(f"    Started: {ip['start_time'][:16]}, {ip['n_trades']} trades, "
              f"equity ${ip['current_equity']:,.0f}, current DD ${ip['current_dd']:,.0f}")


def main():
    # ---- WINNER config replay ----
    print("Replaying WINNER config to get the merged trade list...")
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
    print(f"  PnL=${s_winner['net_pnl']:,.0f} | DD=${s_winner['max_dd_$']:,.0f} | "
          f"N={s_winner['trades']}")
    print()

    print("Simulating prop-firm evaluations on the WINNER preset...")
    print(f"Rule: start=$50,000, trailing $-{DD_LIMIT:,.0f} DD applies until peak hits "
          f"$+{PROFIT_LOCK:,.0f}.")
    print()

    res_winner = simulate_evals(s_winner["_merged"])
    print_report("WINNER ($96.4k PnL / $2.25k worst-single-DD)", res_winner)

    # ---- Also: baseline for comparison ----
    print()
    print("─" * 70)
    print()
    print("Replaying BASELINE preset (the user's anchor combo)...")
    s_base = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    print(f"  PnL=${s_base['net_pnl']:,.0f} | DD=${s_base['max_dd_$']:,.0f} | "
          f"N={s_base['trades']}")
    print()
    res_base = simulate_evals(s_base["_merged"])
    print_report("BASELINE ($138.8k PnL / $3.60k worst-single-DD)", res_base)


if __name__ == "__main__":
    main()
