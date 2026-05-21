#!/usr/bin/env python3
"""Prop-firm evaluation simulator on a saved preset.

Given a preset name (from data/presets.json), runs the backtest and then
walks the resulting trade stream through repeated prop-firm evaluation
attempts to estimate pass / fail rates and durations.

Rules (default — Topstep-style $50k Combine):
  • PASS condition  : cumulative PnL >= $3,000
  • Trailing DD     : $2,000 max drawdown from running peak.
        floor = min(start_equity, peak - 2,000)
    The floor follows the peak up until peak hits start + $2,000, then
    locks at start_equity ($0 PnL) permanently.
  • Daily PnL cap   : $1,500 max PROFIT realized per Brussels calendar
    day. When a trade close pushes the day's PnL above the cap, that
    trade's effective contribution is truncated to bring the day to
    exactly $1,500 and all subsequent trades that day are skipped
    (you stop trading for the day).

Two analyses are produced:
  A) Daily-start  — one fresh evaluation starts at the first trade of
     every Brussels date that has at least one trade. Each eval walks
     forward independently until pass / fail / end-of-data.
  B) Sequential   — one eval starts at the first trade; on pass or fail
     the next eval starts at the very next trade.

Usage:
    python scripts/propfirm_eval.py "Preset Name"
    python scripts/propfirm_eval.py "Preset Name" --mode daily
    python scripts/propfirm_eval.py "Preset" --target 5000 --dd-limit 2500 --daily-cap 0
    python scripts/propfirm_eval.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from scripts.goals._shared.harness import run_backtest  # noqa: E402


PRESETS_FILE = ROOT / "data" / "presets.json"

DEFAULT_TARGET = 3_000.0
DEFAULT_DD_LIMIT = 2_000.0
DEFAULT_DAILY_CAP = 1_500.0


# ─── Preset loading & running ─────────────────────────────────────────────

def _engine_from_dict(d: dict) -> BacktestEngineSettings:
    return BacktestEngineSettings(
        auto_close_enabled=d["auto_close_enabled"],
        auto_close_hour=d["auto_close_hour"],
        auto_close_minute=d["auto_close_minute"],
        blackout_windows=[BlackoutWindowSettings(**w) for w in d["blackout_windows"]],
        debug=d.get("debug", False),
        daily_win_limit_enabled=d["daily_win_limit_enabled"],
        daily_win_limit=d["daily_win_limit"],
        daily_loss_limit_enabled=d["daily_loss_limit_enabled"],
        daily_loss_limit=d["daily_loss_limit"],
        daily_limit_mode=d["daily_limit_mode"],
    )


def load_preset(name: str) -> dict:
    data = json.loads(PRESETS_FILE.read_text())
    exact = [p for p in data if isinstance(p, dict) and p.get("name") == name]
    if exact:
        return exact[0]
    needle = name.lower()
    fuzzy = [p for p in data
             if isinstance(p, dict) and needle in (p.get("name") or "").lower()]
    if len(fuzzy) == 1:
        print(f"  (fuzzy match → '{fuzzy[0]['name']}')\n")
        return fuzzy[0]
    if len(fuzzy) > 1:
        print(f"\nMultiple matches for '{name}':")
        for m in fuzzy:
            print(f"  • {m['name']}")
        raise SystemExit("Disambiguate the preset name.")
    raise SystemExit(f"Preset '{name}' not found in {PRESETS_FILE}")


def list_presets() -> None:
    data = json.loads(PRESETS_FILE.read_text())
    print(f"Available presets ({len(data)}):\n")
    for p in data:
        mode = p.get("mode", "?")
        if mode == "single":
            tag = f"[{mode}] {p.get('symbol', '?')} {p.get('strategyName', '?')}"
        else:
            syms = "+".join(c.get("symbol", "?") for c in p.get("configs", []))
            tag = f"[{mode}] {syms}"
        print(f"  • {p.get('name')}   {tag}")


def run_preset(preset: dict) -> tuple[list, dict]:
    """Run any preset (single / multi_asset / multi_strat) and return merged
    trades (sorted by entry_time) plus a per-leg summary."""
    mode = preset.get("mode", "single")
    merged: list = []
    leg_summary: dict = {}

    def _run_leg(*, strategy_name, symbol, interval, params, risk, max_c,
                 engine_settings, leg_label=None):
        r = run_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            interval=interval,
            start=preset["startDatetime"],
            end=preset["endDatetime"],
            strategy_params=params,
            initial_equity=preset["initialEquity"],
            risk_per_trade=risk,
            max_contracts=max_c,
            engine_settings=engine_settings,
        )
        trades = r.get("trades", [])
        for t in trades:
            t["_leg"] = leg_label or symbol
        return trades

    if mode == "single":
        params = {k: v for k, v in preset["params"].items() if k != "tick_size"}
        trades = _run_leg(
            strategy_name=preset["strategyName"],
            symbol=preset["symbol"],
            interval=preset["interval"],
            params=params,
            risk=preset["riskPerTrade"] / 100.0,
            max_c=preset["maxContracts"],
            engine_settings=_engine_from_dict(preset["engineSettings"]),
        )
        merged.extend(trades)
        active = [t for t in trades if not t.get("excluded", False)]
        leg_summary[preset["symbol"]] = {
            "trades": len(active),
            "pnl": round(sum(t["pnl"] for t in active), 2),
        }
    else:
        for cfg in preset["configs"]:
            params = {k: v for k, v in cfg["params"].items() if k != "tick_size"}
            trades = _run_leg(
                strategy_name=cfg["strategyName"],
                symbol=cfg["symbol"],
                interval=cfg["interval"],
                params=params,
                risk=cfg["riskPerTrade"] / 100.0,
                max_c=cfg["maxContracts"],
                engine_settings=_engine_from_dict(cfg["engineSettings"]),
            )
            merged.extend(trades)
            active = [t for t in trades if not t.get("excluded", False)]
            leg_summary[cfg["symbol"]] = {
                "trades": len(active),
                "pnl": round(sum(t["pnl"] for t in active), 2),
            }

    return merged, leg_summary


# ─── Eval rule engine ─────────────────────────────────────────────────────

def _to_brussels(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        return ts.tz_localize("Europe/Brussels")
    return ts.tz_convert("Europe/Brussels")


def _walk(trades: list, *, start_equity: float, target: float,
          dd_limit: float, daily_cap: float | None) -> dict | None:
    """Walk one eval forward. Returns outcome dict or None if `trades` empty.

    Trailing DD floor: min(start_equity, peak - dd_limit). Once peak hits
    start_equity + dd_limit, the floor locks at start_equity permanently.

    Daily cap: PnL realized per Brussels calendar day is capped at
    `daily_cap` (PROFIT side only). When the cap is hit on a trade, that
    trade's contribution is truncated to bring the day to exactly the cap,
    and all subsequent same-day trades are skipped.
    """
    if not trades:
        return None

    equity = start_equity
    peak = start_equity
    start_ts = _to_brussels(pd.Timestamp(trades[0]["entry_time"]))
    last_day = None
    day_pnl = 0.0
    days_used: set = set()
    last_exit_ts = None

    for k, t in enumerate(trades, start=1):
        exit_ts = _to_brussels(pd.Timestamp(t.get("exit_time") or t["entry_time"]))
        day = exit_ts.date()
        last_exit_ts = exit_ts

        if last_day is None or day != last_day:
            day_pnl = 0.0
            last_day = day

        if daily_cap is not None and day_pnl >= daily_cap:
            continue

        pnl = t["pnl"]
        if daily_cap is not None and day_pnl + pnl > daily_cap:
            effective_pnl = daily_cap - day_pnl
            day_pnl = daily_cap
        else:
            effective_pnl = pnl
            day_pnl += pnl

        equity += effective_pnl
        days_used.add(day)
        if equity > peak:
            peak = equity

        if equity >= start_equity + target:
            return _outcome("pass", k, exit_ts - start_ts, start_ts, exit_ts,
                            peak - start_equity, equity - start_equity,
                            len(days_used))

        floor = min(start_equity, peak - dd_limit)
        if equity <= floor:
            return _outcome("fail", k, exit_ts - start_ts, start_ts, exit_ts,
                            peak - start_equity, equity - start_equity,
                            len(days_used))

    return _outcome("pending", len(trades), None, start_ts, last_exit_ts,
                    peak - start_equity, equity - start_equity, len(days_used))


def _outcome(outcome, n, dur, start, end, peak_pnl, final_pnl, days):
    return {
        "outcome": outcome,
        "n_trades": n,
        "duration": dur,
        "start": start,
        "end": end,
        "peak_pnl": peak_pnl,
        "final_pnl": final_pnl,
        "days": days,
    }


def simulate_daily_start(trades, **kw) -> list:
    active = sorted([t for t in trades if not t.get("excluded", False)],
                    key=lambda t: t["entry_time"])
    first_idx: dict = {}
    for i, t in enumerate(active):
        d = _to_brussels(pd.Timestamp(t["entry_time"])).date()
        if d not in first_idx:
            first_idx[d] = i
    results = []
    for d, idx in sorted(first_idx.items()):
        r = _walk(active[idx:], **kw)
        if r is not None:
            r["start_date"] = str(d)
            results.append(r)
    return results


def simulate_sequential(trades, **kw) -> list:
    active = sorted([t for t in trades if not t.get("excluded", False)],
                    key=lambda t: t["entry_time"])
    results = []
    i = 0
    while i < len(active):
        r = _walk(active[i:], **kw)
        if r is None:
            break
        r["start_date"] = str(_to_brussels(pd.Timestamp(active[i]["entry_time"])).date())
        results.append(r)
        if r["outcome"] == "pending":
            break
        i += r["n_trades"]
    return results


# ─── Reporting ────────────────────────────────────────────────────────────

def _fmt_td(td) -> str:
    if td is None:
        return "—"
    total = td.total_seconds()
    days = int(total // 86400)
    hours = int((total % 86400) // 3600)
    minutes = int((total % 3600) // 60)
    if days > 0:
        return f"{days}j {hours:02d}h{minutes:02d}"
    return f"{hours}h{minutes:02d}"


def _stats(durations):
    if not durations:
        return None
    arr = sorted(durations)
    n = len(arr)
    return {
        "n": n,
        "min": arr[0],
        "max": arr[-1],
        "mean": sum(arr, pd.Timedelta(0)) / n,
        "median": arr[n // 2],
    }


def _print_outcome_block(items, label, symbol):
    if not items:
        return
    durs = [r["duration"] for r in items if r.get("duration") is not None]
    s = _stats(durs)
    print(f"  {symbol} {label} stats (n={len(items)}):")
    if s:
        print(f"    durée moyenne     : {_fmt_td(s['mean'])}")
        print(f"    durée médiane     : {_fmt_td(s['median'])}")
        print(f"    plus rapide       : {_fmt_td(s['min'])}")
        print(f"    plus lente        : {_fmt_td(s['max'])}")
    days_used = [r["days"] for r in items]
    if days_used:
        print(f"    jours actifs moy. : {sum(days_used)/len(days_used):.1f}")
    n_trades = [r["n_trades"] for r in items]
    if n_trades:
        print(f"    trades moyens     : {sum(n_trades)/len(n_trades):.1f}")
    fastest = min(items, key=lambda r: r.get("duration") or pd.Timedelta.max)
    slowest = max(items, key=lambda r: r.get("duration") or pd.Timedelta(0))
    if fastest.get("duration") is not None:
        print(f"    └ fast: {fastest['start'].strftime('%Y-%m-%d %H:%M')} → "
              f"{fastest['end'].strftime('%Y-%m-%d %H:%M')}  "
              f"({fastest['n_trades']} trades, {fastest['days']} jours)")
    if slowest.get("duration") is not None and slowest is not fastest:
        print(f"    └ slow: {slowest['start'].strftime('%Y-%m-%d %H:%M')} → "
              f"{slowest['end'].strftime('%Y-%m-%d %H:%M')}  "
              f"({slowest['n_trades']} trades, {slowest['days']} jours)")
    print()


def _print_summary(label, res, title):
    n = len(res)
    by = Counter(r["outcome"] for r in res)
    p, f, w = by.get("pass", 0), by.get("fail", 0), by.get("pending", 0)
    print(f"=== {label} — {title} ===")
    print(f"  Total évaluations : {n}")
    if n:
        print(f"  ✅ PASS    : {p:>4}  ({p/n*100:.1f}%)")
        print(f"  ❌ FAIL    : {f:>4}  ({f/n*100:.1f}%)")
        print(f"  ⏳ PENDING : {w:>4}  ({w/n*100:.1f}%)")
    decided = p + f
    if decided > 0:
        print(f"  Taux de réussite (hors PENDING) : {p/decided*100:.1f}%")
    print()
    _print_outcome_block([r for r in res if r["outcome"] == "pass"], "PASS", "✅")
    _print_outcome_block([r for r in res if r["outcome"] == "fail"], "FAIL", "❌")


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset_name", nargs="?",
                    help="Preset name (exact, or unique fuzzy substring)")
    ap.add_argument("--target", type=float, default=DEFAULT_TARGET,
                    help=f"Profit target in $ (default {DEFAULT_TARGET:.0f})")
    ap.add_argument("--dd-limit", type=float, default=DEFAULT_DD_LIMIT,
                    help=f"Trailing DD limit in $ (default {DEFAULT_DD_LIMIT:.0f})")
    ap.add_argument("--daily-cap", type=float, default=DEFAULT_DAILY_CAP,
                    help=f"Daily PnL cap in $ (default {DEFAULT_DAILY_CAP:.0f}; "
                         "set 0 to disable)")
    ap.add_argument("--mode", choices=["daily", "sequential", "both"],
                    default="both", help="Which analysis to run (default both)")
    ap.add_argument("--list", action="store_true", help="List available presets")
    args = ap.parse_args()

    if args.list:
        list_presets()
        return

    if not args.preset_name:
        ap.error("preset_name is required (or use --list)")

    daily_cap = args.daily_cap if args.daily_cap > 0 else None

    print(f"Loading preset: {args.preset_name}")
    preset = load_preset(args.preset_name)
    print(f"  Name   : {preset['name']}")
    print(f"  Mode   : {preset.get('mode', 'single')}")
    print(f"  Period : {preset['startDatetime']} → {preset['endDatetime']}")
    print(f"  Equity : ${preset['initialEquity']:,.0f}")
    print(f"  Rules  : target=${args.target:,.0f}  trailing DD=${args.dd_limit:,.0f}  "
          f"daily cap={('$%.0f' % daily_cap) if daily_cap else 'OFF'}")
    print()

    print("Running backtest...")
    merged, leg_summary = run_preset(preset)
    active = [t for t in merged if not t.get("excluded", False)]
    total_pnl = sum(t["pnl"] for t in active)
    print(f"  Trades produced : {len(active)}  Net PnL: ${total_pnl:,.0f}")
    for sym, st in leg_summary.items():
        print(f"    • {sym}: {st['trades']} trades, PnL ${st['pnl']:,.0f}")
    print()

    label = preset["name"]
    kw = dict(start_equity=preset["initialEquity"],
              target=args.target, dd_limit=args.dd_limit, daily_cap=daily_cap)

    if args.mode in ("daily", "both"):
        res = simulate_daily_start(merged, **kw)
        _print_summary(label, res, "Daily-start evaluations (one fresh eval per day)")
        if args.mode == "both":
            print("─" * 70)
            print()

    if args.mode in ("sequential", "both"):
        res = simulate_sequential(merged, **kw)
        _print_summary(label, res, "Sequential evaluations (restart on result)")


if __name__ == "__main__":
    main()
