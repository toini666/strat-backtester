"""Phase 15 — Crystallize the WINNER.

Phase 14 found:
  ut_off rr=1.25 lb=13 risk=0.40% + BO 12-12:30
  → PnL=$26,284 DD=$2,500.00 WR=50.7% N=1113 ✅

Goal:
1. Confirm exact DD (might be $2,499.xx or $2,500.xx).
2. Find Pareto-improving small tweaks (DD ↓ or PnL ↑).
3. Also generate ALT_PNL (slightly higher DD, more PnL) and
   ALT_SAFE (more DD headroom) candidates.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


BASE = {"rr_tp": 1.25, "ut_on": False, "sl_lookback": 13}
BO_1230 = list(SEED_BLACKOUTS_ACTIVE) + [(12, 0, 12, 30)]


def bench(label, params=None, risk=0.0040, max_contracts=20, bos=BO_1230):
    p = dict(BASE)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    kw["risk_per_trade"] = risk
    kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<62s} | {fmt_summary(s)}  (raw DD=${r['metrics']['max_drawdown_dollars']:.4f})")
    return s


def main():
    print("--- WINNER candidate ---")
    w = bench("WINNER candidate")

    print("\n--- Tweaks to find DD < $2,500 strictly ---")
    rows = []

    # Sub-pct risk tweaks
    for r_pct in [0.390, 0.395, 0.398, 0.400, 0.402, 0.405]:
        rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- tick_buffer variations ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"tb={tb}", params={"tick_buffer": tb}))

    print("\n--- 2nd BO additions on top ---")
    additions = [
        ("+ BO 7-8",      [(7, 0, 8, 0)]),
        ("+ BO 11-12",    [(11, 0, 12, 0)]),
        ("+ BO 1-2",      [(1, 0, 2, 0)]),
        ("+ BO 12-12:30 → 11:30-12:30 wider", "REPLACE_1230"),
    ]
    for label, addn in additions:
        if addn == "REPLACE_1230":
            bos = [bo for bo in BO_1230 if bo != (12, 0, 12, 30)]
            bos.append((11, 30, 12, 30))
        else:
            bos = BO_1230 + list(addn)
        rows.append(bench(label, bos=bos))

    # ALT_SAFE — more DD headroom
    print("\n--- ALT_SAFE (lower risk, more DD margin) ---")
    rows.append(bench("ALT_SAFE risk=0.36%", risk=0.0036))
    rows.append(bench("ALT_SAFE risk=0.35%", risk=0.0035))

    # ALT_PNL — slightly more DD if user accepts
    print("\n--- ALT_PNL (higher risk, more PnL — slight DD overshoot) ---")
    rows.append(bench("ALT_PNL risk=0.42%", risk=0.0042))
    rows.append(bench("ALT_PNL risk=0.45%", risk=0.0045))

    # Other anchors briefly
    print("\n--- Other ut_off rr_tp variants ---")
    for rr in [1.2, 1.3]:
        rows.append(bench(f"rr={rr} (other tweaks same)", params={"rr_tp": rr}))

    print(f"\nWINNER: PnL=${w['net_pnl']:,.0f}  DD=${w['max_dd_$']:,.0f}  WR={w['win_rate']:.1f}%  N={w['trades']}")
    print("\n--- ✅ All WR>=50% sorted by PnL ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good[:10]:
            print(f"  ✅ {r['label']:<54s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")


if __name__ == "__main__":
    main()
