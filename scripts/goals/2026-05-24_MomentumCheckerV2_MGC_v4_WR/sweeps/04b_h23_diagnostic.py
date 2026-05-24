"""Phase 4b — diagnose H=23 entries that pass through BO 22-23:59.

At anchor (rr=1.55, lb=12), H=23 cluster: 13 trades, 23.1% WR, -$1,387.
Seed BO 22-23:59 is supposed to block them but doesn't. Investigate.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.55, "sl_lookback": 12, "tick_buffer": 2}


def main():
    # Anchor with seed BOs
    r = run_backtest(**seed_kwargs(params=ANCHOR,
                                   engine_settings=build_engine_settings(SEED_BLACKOUTS_ACTIVE)))
    h23 = [t for t in r["trades"]
           if not t.get("excluded", False)
           and pd.to_datetime(t["entry_time"]).hour == 23]
    print(f"H=23 trades: {len(h23)}")
    for t in h23[:6]:
        print(f"  entry_time={t['entry_time']}  exit_time={t.get('exit_time')}  "
              f"side={t.get('side')}  status={t.get('status', '?')}  "
              f"entry_price={t.get('entry_price'):.2f}  pnl=${t.get('pnl', 0):.2f}")

    print()
    print("--- Try BO 21:00-23:59 (replaces both 20-21 and 22-23:59) ---")
    bos = [bo for bo in SEED_BLACKOUTS_ACTIVE
           if bo not in [(20, 0, 21, 0), (22, 0, 23, 59)]]
    bos.append((21, 0, 23, 59))
    r2 = run_backtest(**seed_kwargs(params=ANCHOR,
                                    engine_settings=build_engine_settings(bos)))
    s = summarize(r2)
    s["label"] = "BO 21-23:59 (kill all evening)"
    print(s["label"], fmt_summary(s))
    h23_2 = [t for t in r2["trades"]
             if not t.get("excluded", False)
             and pd.to_datetime(t["entry_time"]).hour == 23]
    h22_2 = [t for t in r2["trades"]
             if not t.get("excluded", False)
             and pd.to_datetime(t["entry_time"]).hour == 22]
    print(f"  after: H=22={len(h22_2)} trades, H=23={len(h23_2)} trades")

    print()
    print("--- Try BO 17:00-23:59 (kill big evening window) ---")
    bos = [bo for bo in SEED_BLACKOUTS_ACTIVE
           if bo not in [(18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)]]
    bos.append((17, 0, 23, 59))
    r3 = run_backtest(**seed_kwargs(params=ANCHOR,
                                    engine_settings=build_engine_settings(bos)))
    s = summarize(r3)
    s["label"] = "BO 17-23:59 (kill all PM)"
    print(s["label"], fmt_summary(s))
    h23_3 = [t for t in r3["trades"]
             if not t.get("excluded", False)
             and pd.to_datetime(t["entry_time"]).hour == 23]
    print(f"  after: H=23={len(h23_3)} trades")


if __name__ == "__main__":
    main()
