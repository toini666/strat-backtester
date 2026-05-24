"""Phase 4c — Targeted BO sweep at anchor (rr=1.55, lb=12).

Anchor diagnostic (Phase 4):
  H=11 N=41 WR=31.7% Total=-$1,775   ← big NEG, biggest BO win
  H=07 N=49 WR=38.8% Total=+$307     ← LO WR
  H=23 N=13 WR=23.1% Total=-$1,387   ← DST-bug, hard to kill
  H=12 N=22 WR=40.9% Total=+$99      ← LO WR
Strong WR clusters NOT to touch:
  H=04 (55.4%), H=05 (59.6%), H=21 (60%), H=15 (52%), H=18/20 (53.8%)
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.55, "sl_lookback": 12, "tick_buffer": 2}


def bench(label, blackouts):
    es = build_engine_settings(blackouts)
    r = run_backtest(**seed_kwargs(params=ANCHOR, engine_settings=es))
    s = summarize(r)
    s["label"] = label
    s["bos"] = blackouts
    print(f"{label:<46s} | {fmt_summary(s)}")
    return s


def main():
    anchor = bench("anchor (seed BOs)", SEED_BLACKOUTS_ACTIVE)

    print("\n--- single BO additions targeting LO clusters ---")
    rows = []
    additions = [
        ("+ BO 7-8",     [(7, 0, 8, 0)]),
        ("+ BO 11-12",   [(11, 0, 12, 0)]),
        ("+ BO 11:30-12", [(11, 30, 12, 0)]),
        ("+ BO 12-12:30", [(12, 0, 12, 30)]),
        ("+ BO 11-12 & 12-12:30 (lunch widen)", [(11, 0, 12, 30)]),
        # H=23 DST workaround — try BO 0-1 to catch transition-shifted entries
        ("+ BO 0-1 (DST-23 workaround)", [(0, 0, 1, 0)]),
    ]
    for label, addn in additions:
        bos = list(SEED_BLACKOUTS_ACTIVE) + list(addn)
        rows.append(bench(label, bos))

    print("\n--- 2-BO combos on best single ---")
    # Try combo BO 11-12 + each other
    combo_base = (11, 0, 12, 0)
    for label, addn in additions[:1] + additions[2:]:  # skip duplicate
        bos = list(SEED_BLACKOUTS_ACTIVE) + [combo_base] + list(addn)
        rows.append(bench(f"+ BO 11-12 {label}", bos))

    print("\n--- Single-window REPLACE candidates (drop one seed BO, add new) ---")
    # Could the seed's BOs themselves be suboptimal? Test dropping each and adding 11-12.
    for drop_idx in range(len(SEED_BLACKOUTS_ACTIVE)):
        bos = [bo for i, bo in enumerate(SEED_BLACKOUTS_ACTIVE) if i != drop_idx]
        bos.append((11, 0, 12, 0))
        dropped = SEED_BLACKOUTS_ACTIVE[drop_idx]
        rows.append(bench(f"drop {dropped[:2]}-{dropped[2:]} + BO 11-12", bos))

    # Ranking
    print(f"\nANCHOR: PnL=${anchor['net_pnl']:,.0f}  DD=${anchor['max_dd_$']:,.0f}  WR={anchor['win_rate']:.1f}%")
    print("\n--- Sorted by WR (DD<=2500 only) ---")
    safe = [r for r in rows if r["max_dd_$"] <= 2500.0]
    safe.sort(key=lambda r: (r["win_rate"], r["net_pnl"]), reverse=True)
    for r in safe[:10]:
        d_wr = r["win_rate"] - anchor["win_rate"]
        d_pnl = r["net_pnl"] - anchor["net_pnl"]
        d_dd = r["max_dd_$"] - anchor["max_dd_$"]
        print(f"  {r['label']:<46s} WR={r['win_rate']:.1f}% ({d_wr:+.1f}pp)  "
              f"PnL=${r['net_pnl']:,.0f} ({d_pnl:+,.0f})  DD=${r['max_dd_$']:,.0f} ({d_dd:+,.0f})")


if __name__ == "__main__":
    main()
