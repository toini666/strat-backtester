"""Phase 4 — Blackouts at new anchor (rr=1.55, sl_lookback=12, tick_buffer=2).

Strategy:
1. Re-bucket trades by hour at the new anchor (might differ from Phase 0 seed).
2. Score each candidate BO by:
   - WR gain if we BO that hour
   - PnL loss / DD loss
3. Test individual BO extensions (1 at a time first, then combos).

Seed BOs (kept active throughout):
  (12,30,14,0), (15,30,17,0), (18,0,19,0), (20,0,21,0), (22,0,23,59)

Candidate add-ons:
  Extend 12-12:30 (lunch widen), trim mornings, kill H=23 with pre-22 bar safety,
  test BO 1-2 (low-WR), BO 3-4 (low-WR).
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.analysis import bucket_by_hour
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR_PARAMS = {"rr_tp": 1.55, "sl_lookback": 12, "tick_buffer": 2}


def bench(label, blackouts):
    es = build_engine_settings(blackouts)
    r = run_backtest(**seed_kwargs(params=ANCHOR_PARAMS, engine_settings=es))
    s = summarize(r)
    s["label"] = label
    print(f"{label:<50s} | {fmt_summary(s)}")
    return r, s


def diag_buckets(r):
    h = bucket_by_hour(r["trades"])
    print(f"\n{'H':>3}  {'N':>4}  {'WR%':>6}  {'AvgPnL':>9}  {'Total':>10}")
    for hr in sorted(h):
        b = h[hr]
        marker = "  *LO*" if b['win_rate'] < 40 else ("  *NEG*" if b['total'] < 0 else "")
        print(f"{hr:>3}  {b['n']:>4}  {b['win_rate']:>6.1f}  {b['avg']:>9.2f}  {b['total']:>10.2f}{marker}")


def main():
    print("--- ANCHOR + seed BOs (5 active) ---")
    r0, s0 = bench("anchor seed-BOs", SEED_BLACKOUTS_ACTIVE)
    diag_buckets(r0)

    print("\n--- SINGLE BO ADDITIONS ---")
    # Each addition keeps seed's 5 BOs and adds one.
    additions = [
        ("+ BO 0-1",      [(0, 0, 1, 0)]),
        ("+ BO 1-2",      [(1, 0, 2, 0)]),
        ("+ BO 3-4",      [(3, 0, 4, 0)]),
        ("+ BO 12-12:30", [(12, 0, 12, 30)]),  # extend lunch left
        ("+ BO 14-15",    [(14, 0, 15, 0)]),
        ("+ BO 21-22",    [(21, 0, 22, 0)]),   # kill 21h overlap
        # H=23 cluster — current BO 22-23:59 lets 7m bars opening 21:53+ through
        ("+ BO 21:53-23:59 (replaces 22-23:59)", "REPLACE_22"),
    ]
    rows = []
    for label, addn in additions:
        if addn == "REPLACE_22":
            bos = [bo for bo in SEED_BLACKOUTS_ACTIVE if bo != (22, 0, 23, 59)]
            bos.append((21, 53, 23, 59))
        else:
            bos = list(SEED_BLACKOUTS_ACTIVE) + list(addn)
        r, s = bench(label, bos)
        s["bos"] = bos
        rows.append(s)

    # Also test full kill of H=23 cluster via wider window
    print("\n--- aggressive H=23 kill ---")
    bos = [bo for bo in SEED_BLACKOUTS_ACTIVE if bo != (22, 0, 23, 59)]
    bos.append((21, 0, 23, 59))  # full 21-23:59
    r, s = bench("(21-23:59) replaces 22-23:59 AND 20-21", bos)
    rows.append(s)

    print(f"\nANCHOR: PnL=${s0['net_pnl']:,.0f}  DD=${s0['max_dd_$']:,.0f}  WR={s0['win_rate']:.1f}%")
    print("\n--- Sorted by WR (DD<=2500 only) ---")
    safe = [r for r in rows if r["max_dd_$"] <= 2500.0]
    safe.sort(key=lambda r: r["win_rate"], reverse=True)
    for r in safe[:8]:
        d_wr = r["win_rate"] - s0["win_rate"]
        d_pnl = r["net_pnl"] - s0["net_pnl"]
        d_dd = r["max_dd_$"] - s0["max_dd_$"]
        print(f"  {r['label']:<45s} WR={r['win_rate']:.1f}% ({d_wr:+.1f}pp)  "
              f"PnL=${r['net_pnl']:,.0f} ({d_pnl:+,.0f})  DD=${r['max_dd_$']:,.0f} ({d_dd:+,.0f})")


if __name__ == "__main__":
    main()
