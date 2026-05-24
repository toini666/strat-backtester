"""Phase 7 — daily-loss limit + tick_buffer + fine sl_lookback at rr=1.25/lb=15.

Phase 6 showed DD floor ~$2,900 at WR>=50% with single levers — risk crawl is
flat (rounding-cell), single BOs help PnL but barely move DD.

This phase tries:
A) Daily loss limit (intra_bar mode first) — caps DD per day.
B) Daily loss + win combo.
C) Fine sl_lookback {13, 14, 16, 17, 18} at rr=1.25.
D) tick_buffer {0, 1, 3} at rr=1.25/lb=15.
E) Combo: BO 11-12 + tick_buffer + risk crawl.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.25, "sl_lookback": 15}


def bench(label, params=None, risk=None, bos=None,
          dly_loss_on=False, dly_loss=700, dly_win_on=False, dly_win=500,
          dly_mode="intra_bar"):
    p = dict(ANCHOR)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p)
    if risk is not None:
        kw["risk_per_trade"] = risk
    use_bos = bos if bos is not None else SEED_BLACKOUTS_ACTIVE
    es = build_engine_settings(use_bos)
    es.daily_loss_limit_enabled = dly_loss_on
    es.daily_loss_limit = float(dly_loss)
    es.daily_win_limit_enabled = dly_win_on
    es.daily_win_limit = float(dly_win)
    es.daily_limit_mode = dly_mode
    kw["engine_settings"] = es
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} | {fmt_summary(s)}")
    return s


def main():
    print("--- ANCHOR rr=1.25 lb=15 ---")
    anchor = bench("anchor")

    print("\n--- A) Daily loss limit (intra_bar mode) ---")
    rows = []
    for loss in [500, 600, 700, 800, 1000, 1200]:
        rows.append(bench(f"dl={loss} intra_bar",
                          dly_loss_on=True, dly_loss=loss, dly_mode="intra_bar"))

    print("\n--- A2) Daily loss limit (after_close mode) ---")
    for loss in [500, 700, 1000]:
        rows.append(bench(f"dl={loss} after_close",
                          dly_loss_on=True, dly_loss=loss, dly_mode="after_close"))

    print("\n--- B) Daily loss + win combos ---")
    for loss, win in [(700, 500), (700, 800), (1000, 1000), (500, 500)]:
        rows.append(bench(f"dl={loss} dw={win} intra_bar",
                          dly_loss_on=True, dly_loss=loss,
                          dly_win_on=True, dly_win=win, dly_mode="intra_bar"))

    print("\n--- C) Fine sl_lookback at rr=1.25 ---")
    for lb in [13, 14, 16, 17, 18, 20]:
        rows.append(bench(f"lb={lb}", params={"sl_lookback": lb}))

    print("\n--- D) tick_buffer at rr=1.25 ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"tb={tb}", params={"tick_buffer": tb}))

    print("\n--- E) BO 11-12 + tick_buffer combos ---")
    bos = list(SEED_BLACKOUTS_ACTIVE) + [(11, 0, 12, 0)]
    for tb in [1, 2, 3]:
        rows.append(bench(f"+ BO 11-12 + tb={tb}", params={"tick_buffer": tb}, bos=bos))

    # Pareto report
    print(f"\nANCHOR: PnL=${anchor['net_pnl']:,.0f}  DD=${anchor['max_dd_$']:,.0f}  WR={anchor['win_rate']:.1f}%")
    print("\n--- ✅ Candidates with WR>=50% AND DD<=2500 ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good:
            print(f"  ✅ {r['label']:<48s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")
    else:
        print("  (none)")
        # Top 5 closest
        print("\n--- Top 5 closest to budget (WR>=50%) ---")
        close = [r for r in rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:5]:
            print(f"  ❌ {r['label']:<48s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
