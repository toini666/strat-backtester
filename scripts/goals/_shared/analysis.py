"""Trade-level analysis helpers (hour buckets, day-of-week, contract segments)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable

import pandas as pd


def _active_trades(trades: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [t for t in trades if not t.get("excluded", False)]


def bucket_by_hour(trades: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    by_hour: Dict[int, list] = defaultdict(list)
    for t in _active_trades(trades):
        h = pd.to_datetime(t["entry_time"]).hour
        by_hour[h].append(t["pnl"])
    return {
        h: {
            "n": len(pnls),
            "total": sum(pnls),
            "avg": sum(pnls) / len(pnls),
            "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
        }
        for h, pnls in by_hour.items()
    }


def bucket_by_dow(trades: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    by_dow: Dict[int, list] = defaultdict(list)
    for t in _active_trades(trades):
        d = pd.to_datetime(t["entry_time"]).dayofweek
        by_dow[d].append(t["pnl"])
    return {
        d: {
            "n": len(pnls),
            "total": sum(pnls),
            "avg": sum(pnls) / len(pnls),
            "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
        }
        for d, pnls in by_dow.items()
    }


def print_hour_table(by_hour: Dict[int, Dict[str, float]]) -> None:
    print(f"{'Hour':<6}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for h in sorted(by_hour):
        d = by_hour[h]
        print(f"H={h:02d}  {d['n']:>5}  ${d['total']:>10,.0f}  ${d['avg']:>7,.0f}  {d['win_rate']:>5.0f}%")


def print_dow_table(by_dow: Dict[int, Dict[str, float]]) -> None:
    names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    print(f"{'Day':<6}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for d in sorted(by_dow):
        v = by_dow[d]
        print(f"{names.get(d, str(d)):<6}{v['n']:>5}  ${v['total']:>10,.0f}  ${v['avg']:>7,.0f}  {v['win_rate']:>5.0f}%")
