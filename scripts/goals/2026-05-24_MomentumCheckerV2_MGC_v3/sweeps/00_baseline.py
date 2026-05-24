"""Phase 0 — Reproduce BEST2 MGC seed + diagnostics on THIS preset's open hours."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CAMPAIGN))

from scripts.goals._shared.analysis import bucket_by_hour, print_hour_table
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import seed_kwargs


def main() -> None:
    print("=" * 72)
    print("Phase 0 — BEST2 MGC MomentumCheckerV2 v3 — seed reproduction")
    print("=" * 72)

    r = run_backtest(**seed_kwargs())
    s = summarize(r)
    print("\nSEED  " + fmt_summary(s))

    # Hour bucket — against THIS preset's open hours
    print("\nHour-of-day breakdown (active trades only):")
    by_h = bucket_by_hour(r["trades"])
    print_hour_table(by_h)

    # Worst losers — to test "SL trop éloigné" on this preset
    active = [t for t in r["trades"] if not t.get("excluded", False)]
    losers = sorted(active, key=lambda t: t["pnl"])[:12]
    print("\n12 worst losers:")
    print(f"{'pnl':>10}  {'entry':>10}  {'exit':>10}  {'Δprice':>8}  {'sz':>3}  "
          f"{'status':<22}  {'side':<6}")
    for t in losers:
        entry = t.get("entry_price") or 0
        legs = t.get("legs", []) or []
        exit_ = (legs[-1].get("exit_price") if legs else 0) or 0
        dp = exit_ - entry if entry else 0
        size = sum(int(l.get("contracts", 0)) for l in legs)
        status = legs[-1].get("status", "") if legs else ""
        print(f"{t['pnl']:>10,.1f}  {entry:>10,.2f}  {exit_:>10,.2f}  "
              f"{dp:>+8,.2f}  {size:>3d}  {status:<22}  {t['side']:<6}")

    # Status histogram (final-leg)
    final_statuses: Counter = Counter()
    for t in active:
        legs = t.get("legs", []) or []
        if legs:
            final_statuses[legs[-1].get("status", "")] += 1
    print("\nFinal-status histogram:")
    for k, v in final_statuses.most_common():
        pct = v / len(active) * 100 if active else 0
        print(f"  {k:<22} {v:>5}  ({pct:>5.1f}%)")

    # SIG-on-loss distribution — addresses user's hypothesis directly
    debug = r.get("debug_data")
    if debug is None:
        # not exported by simulator result by default — recompute via signals frame
        pass
    print("\nDone.")


if __name__ == "__main__":
    main()
