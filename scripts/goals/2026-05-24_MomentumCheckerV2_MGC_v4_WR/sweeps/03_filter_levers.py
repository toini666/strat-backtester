"""Phase 3 — Filter levers at new anchor (rr=1.55, sl_lookback=12).

Goal: push WR from 47.1% to >= 50% while keeping DD <= $2,500 and PnL > $30k.

Levers tested:
- sig_range_reject + sig_level (helped on MNQ v5; rejected on MGC v3 at rr=3)
- sig_extreme_filter_on + sig_extreme
- hw_filter_on / hw_level
- be_at_rr (low values — at rr=1.55 the seed's be_at_rr=2 never fires)
- tick_buffer
- max_candle_pct
- min_gap
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


ANCHOR_PARAMS = {"rr_tp": 1.55, "sl_lookback": 12}


def bench(label, extra_params):
    p = dict(ANCHOR_PARAMS)
    p.update(extra_params)
    r = run_backtest(**seed_kwargs(params=p))
    s = summarize(r)
    s["label"] = label
    print(f"{label:<46s} | {fmt_summary(s)}")
    return s


def main():
    print("--- ANCHOR: rr=1.55, sl_lookback=12 ---")
    rows = [bench("anchor", {})]

    print("\n--- sig_range_reject ---")
    for lvl in [1, 2, 3, 5, 8, 10, 15]:
        rows.append(bench(f"sig_range_reject lvl={lvl}",
                          {"sig_range_reject": True, "sig_level": float(lvl)}))

    print("\n--- sig_extreme_filter_on toggle / level ---")
    rows.append(bench("sig_extreme OFF", {"sig_extreme_filter_on": False}))
    for sx in [10, 12, 18, 20]:
        rows.append(bench(f"sig_extreme={sx}", {"sig_extreme": sx}))

    print("\n--- hw filter ---")
    rows.append(bench("hw_filter OFF", {"hw_filter_on": False}))
    for hl in [10, 12, 20, 24]:
        rows.append(bench(f"hw_level={hl}", {"hw_level": hl}))
    rows.append(bench("hw_extreme ON",
                      {"hw_extreme_filter_on": True, "hw_extreme": 15}))

    print("\n--- be_at_rr (at rr=1.55, BE=2 never fires; test smaller) ---")
    for be in [0, 0.5, 1.0, 1.3]:
        rows.append(bench(f"be_at_rr={be}", {"be_at_rr": be}))

    print("\n--- tick_buffer ---")
    for tb in [0, 1, 3, 4]:
        rows.append(bench(f"tick_buffer={tb}", {"tick_buffer": tb}))

    print("\n--- max_candle_pct ---")
    for mcp in [0.15, 0.20, 0.30, 0.35]:
        rows.append(bench(f"max_candle_pct={mcp}", {"max_candle_pct": mcp}))

    print("\n--- min_gap ---")
    for mg in [5, 6, 7, 9, 10, 11, 12]:
        rows.append(bench(f"min_gap={mg}", {"min_gap": mg}))

    # Top candidates that PRESERVE DD<=2500 and IMPROVE on anchor
    anchor = rows[0]
    print(f"\nANCHOR: PnL=${anchor['net_pnl']:,.0f}  DD=${anchor['max_dd_$']:,.0f}  WR={anchor['win_rate']:.1f}%")

    print("\n--- IMPROVES (WR_delta or PnL or DD reduce) within DD<=2500 ---")
    safe = [r for r in rows[1:] if r["max_dd_$"] <= 2500.0]
    safe.sort(key=lambda r: (r["win_rate"], r["net_pnl"]), reverse=True)
    for r in safe[:12]:
        d_wr = r["win_rate"] - anchor["win_rate"]
        d_pnl = r["net_pnl"] - anchor["net_pnl"]
        d_dd = r["max_dd_$"] - anchor["max_dd_$"]
        print(f"  {r['label']:<40s}  WR={r['win_rate']:.1f}% ({d_wr:+.1f}pp)  "
              f"PnL=${r['net_pnl']:,.0f} ({d_pnl:+,.0f})  DD=${r['max_dd_$']:,.0f} ({d_dd:+,.0f})")


if __name__ == "__main__":
    main()
