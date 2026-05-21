"""Phase 02 — DD episode breakdown.

Identify which leg drives the worst peak-to-trough $ DD episode and the
trades involved.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd  # noqa: E402

from _campaign import INITIAL_EQUITY, run_multi  # noqa: E402


def _ts(x):
    return pd.Timestamp(x)


def trace_dd(s):
    merged = sorted(s["_merged"], key=lambda t: t["entry_time"])
    eq = INITIAL_EQUITY
    peak = INITIAL_EQUITY
    peak_t = None
    cur_peak_t = None
    worst_dd = 0.0
    worst_peak_t = None
    worst_trough_t = None
    for t in merged:
        eq += t["pnl"]
        if eq > peak:
            peak = eq
            cur_peak_t = t["entry_time"]
        dd = peak - eq
        if dd > worst_dd:
            worst_dd = dd
            worst_peak_t = cur_peak_t
            worst_trough_t = t["entry_time"]
    return worst_dd, worst_peak_t, worst_trough_t


if __name__ == "__main__":
    s = run_multi()
    dd, p_t, t_t = trace_dd(s)
    print(f"Worst DD=${dd:,.0f} from {p_t} to {t_t}")

    pad = timedelta(days=1)
    p_ts = _ts(p_t) - pad
    t_ts = _ts(t_t) + pad

    merged = sorted(s["_merged"], key=lambda t: _ts(t["entry_time"]))
    episode = [t for t in merged if p_ts <= _ts(t["entry_time"]) <= t_ts]
    print(f"\n{len(episode)} trades in episode window:\n")
    mgc_pnl = 0.0
    mnq_pnl = 0.0
    for t in episode:
        if t.get("excluded"):
            continue
        leg = t["_leg"]
        pnl = t["pnl"]
        if leg == "MGC":
            mgc_pnl += pnl
        else:
            mnq_pnl += pnl
        marker = "L" if pnl < 0 else " "
        print(f"  {leg}  {t['entry_time']}  pnl=${pnl:>+8,.0f}  {marker}  side={t.get('side','?')}  contracts={t.get('contracts','?')}")
    print(f"\nEpisode PnL: MGC=${mgc_pnl:,.0f}  MNQ=${mnq_pnl:,.0f}")
