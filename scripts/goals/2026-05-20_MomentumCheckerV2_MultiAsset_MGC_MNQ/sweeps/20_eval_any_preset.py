"""Phase 20 — Run the prop-firm eval analyses (failure count + duration)
on ANY multi-asset preset loaded by name from data/presets.json.

Usage:
    python 20_eval_any_preset.py "0,5 0,5% - Multi-Asset — MNQ/MGC"
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from scripts.goals._shared.harness import run_backtest  # noqa: E402


PRESETS_FILE = ROOT / "data" / "presets.json"
START_EQUITY_DEFAULT = 50_000.0
DD_LIMIT = 2_000.0
PROFIT_LOCK = 2_000.0


def load_preset(name: str) -> dict:
    data = json.loads(PRESETS_FILE.read_text())
    for p in data:
        if isinstance(p, dict) and p.get("name") == name:
            return p
    raise SystemExit(f"Preset '{name}' not found in {PRESETS_FILE}")


def engine_from_dict(d: dict) -> BacktestEngineSettings:
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


def run_preset_multi(preset: dict) -> tuple[list, dict]:
    """Run a multi-asset preset; return merged trade list + summary."""
    merged = []
    leg_summary = {}
    for cfg in preset["configs"]:
        params = {k: v for k, v in cfg["params"].items() if k != "tick_size"}
        r = run_backtest(
            strategy_name=cfg["strategyName"],
            symbol=cfg["symbol"],
            interval=cfg["interval"],
            start=preset["startDatetime"],
            end=preset["endDatetime"],
            strategy_params=params,
            initial_equity=preset["initialEquity"],
            risk_per_trade=cfg["riskPerTrade"] / 100.0,
            max_contracts=cfg["maxContracts"],
            engine_settings=engine_from_dict(cfg["engineSettings"]),
        )
        trades = r.get("trades", [])
        for t in trades:
            t["_leg"] = cfg["symbol"]
        merged.extend(trades)
        active = [t for t in trades if not t.get("excluded", False)]
        leg_summary[cfg["symbol"]] = {
            "trades": len(active),
            "pnl": round(sum(t["pnl"] for t in active), 2),
        }
    return merged, leg_summary


def combined_metrics(initial_equity: float, trades: list) -> dict:
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_active = sorted(active, key=lambda t: t["entry_time"])
    equity = initial_equity
    peak = initial_equity
    max_dd_pct = 0.0
    max_dd_dollars = 0.0
    for trade in sorted_active:
        equity += trade["pnl"]
        if equity > peak:
            peak = equity
        dd_d = peak - equity
        dd_p = dd_d / peak if peak > 0 else 0.0
        if dd_p > max_dd_pct:
            max_dd_pct = dd_p
        if dd_d > max_dd_dollars:
            max_dd_dollars = dd_d
    return {
        "net_pnl": round(equity - initial_equity, 2),
        "trades": len(active),
        "max_dd_$": round(max_dd_dollars, 2),
        "max_dd_%": round(max_dd_pct * 100, 2),
    }


# ─── Eval simulators (same as phases 17/18/19) ───────────────────────────

def _walk_one_eval(trades_from, start_equity):
    equity = start_equity
    peak = start_equity
    start_time = pd.Timestamp(trades_from[0]["entry_time"])
    for k, t in enumerate(trades_from, start=1):
        equity += t["pnl"]
        if equity > peak:
            peak = equity
        end_time = pd.Timestamp(t.get("exit_time") or t["entry_time"])
        if peak >= start_equity + PROFIT_LOCK:
            return ("pass", k, end_time - start_time, start_time, end_time, peak, equity)
        if peak - equity >= DD_LIMIT:
            return ("fail", k, end_time - start_time, start_time, end_time, peak, equity)
    return ("pending", len(trades_from), None, start_time, None, peak, equity)


def simulate_daily(trades, start_equity):
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])
    first_idx = {}
    for i, t in enumerate(sorted_t):
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts = ts.tz_convert("Europe/Brussels")
        d = ts.date()
        if d not in first_idx:
            first_idx[d] = i
    res = []
    for d, idx in sorted(first_idx.items()):
        out, n, dur, st, et, pk, eq = _walk_one_eval(sorted_t[idx:], start_equity)
        res.append({
            "date": str(d), "outcome": out, "n_trades": n,
            "duration": dur, "start_time": st, "end_time": et,
            "peak": pk, "trough_or_end": eq,
            "drop": (pk - eq) if out == "fail" else None,
        })
    return res


def simulate_sequential(trades, start_equity):
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_t = sorted(active, key=lambda t: t["entry_time"])
    fails = []
    passes = []
    i = 0
    in_progress = None
    while i < len(sorted_t):
        equity = start_equity
        peak = start_equity
        attempt_start_idx = i
        attempt_start_time = sorted_t[i]["entry_time"]
        resolved = False
        while i < len(sorted_t):
            t = sorted_t[i]
            equity += t["pnl"]
            if equity > peak:
                peak = equity
            if peak >= start_equity + PROFIT_LOCK:
                passes.append({"n": i - attempt_start_idx + 1,
                               "start_time": attempt_start_time,
                               "pass_time": t.get("exit_time") or t["entry_time"]})
                i += 1
                resolved = True
                break
            if peak - equity >= DD_LIMIT:
                fails.append({"n": i - attempt_start_idx + 1,
                              "start_time": attempt_start_time,
                              "fail_time": t.get("exit_time") or t["entry_time"],
                              "peak": peak, "trough": equity,
                              "drop": peak - equity})
                i += 1
                resolved = True
                break
            i += 1
        if not resolved:
            in_progress = {"start_time": attempt_start_time,
                           "n": len(sorted_t) - attempt_start_idx,
                           "equity": equity, "peak": peak}
            break
    return {"fails": fails, "passes": passes, "in_progress": in_progress}


def _fmt_td(td):
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
    return {"n": n, "min": arr[0], "max": arr[-1],
            "mean": sum(arr, pd.Timedelta(0)) / n,
            "median": arr[n // 2]}


def print_daily_report(label, res):
    print(f"=== {label} — Daily evaluations ===")
    n = len(res)
    by = Counter(r["outcome"] for r in res)
    print(f"  Total            : {n}")
    print(f"  ✅ PASS    : {by.get('pass', 0):>4}  ({by.get('pass', 0)/n*100:.1f}%)")
    print(f"  ❌ FAIL    : {by.get('fail', 0):>4}  ({by.get('fail', 0)/n*100:.1f}%)")
    print(f"  ⏳ PENDING : {by.get('pending', 0):>4}  ({by.get('pending', 0)/n*100:.1f}%)")
    print()

    for outcome, sym in (("pass", "✅"), ("fail", "❌")):
        items = [r for r in res if r["outcome"] == outcome]
        durs = [r["duration"] for r in items]
        s = _stats(durs)
        if not s:
            continue
        print(f"  {sym} {outcome.upper()} duration stats (n={s['n']}):")
        print(f"    moyenne     : {_fmt_td(s['mean'])}")
        print(f"    médiane     : {_fmt_td(s['median'])}")
        print(f"    plus rapide : {_fmt_td(s['min'])}")
        print(f"    plus lente  : {_fmt_td(s['max'])}")
        fast = min(items, key=lambda r: r["duration"])
        slow = max(items, key=lambda r: r["duration"])
        print(f"    └ fast : {fast['start_time'].strftime('%Y-%m-%d %H:%M')} → "
              f"{fast['end_time'].strftime('%Y-%m-%d %H:%M')}  ({fast['n_trades']} tr)")
        print(f"    └ slow : {slow['start_time'].strftime('%Y-%m-%d %H:%M')} → "
              f"{slow['end_time'].strftime('%Y-%m-%d %H:%M')}  ({slow['n_trades']} tr)")
        print()


def print_sequential_report(label, res):
    fails = res["fails"]
    passes = res["passes"]
    n = len(fails) + len(passes) + (1 if res["in_progress"] else 0)
    print(f"=== {label} — Sequential evaluations (restart on result) ===")
    print(f"  Passes  : {len(passes)}")
    print(f"  Fails   : {len(fails)}")
    print(f"  Total   : {n}  (fail rate {len(fails)/n*100 if n else 0:.1f}%)")
    if fails:
        print(f"  Détail des échecs ({len(fails)}):")
        for k, f in enumerate(fails, 1):
            print(f"    #{k}  {f['start_time'][:16]} → {f['fail_time'][:16]}  "
                  f"(n={f['n']:>3})  peak=${f['peak']:>7,.0f}  trough=${f['trough']:>7,.0f}  "
                  f"drop=${f['drop']:>5,.0f}")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "0,5 0,5% - Multi-Asset — MNQ/MGC"
    preset = load_preset(name)
    print(f"Preset: {preset['name']}")
    print(f"Period: {preset['startDatetime']} → {preset['endDatetime']}")
    print(f"Mode: {preset['mode']}  Initial equity: ${preset['initialEquity']:,.0f}")
    for cfg in preset["configs"]:
        print(f"  Leg: {cfg['symbol']} {cfg['interval']} {cfg['strategyName']} "
              f"risk={cfg['riskPerTrade']}% maxC={cfg['maxContracts']}")
    print()

    print("Running both legs...")
    merged, leg_summary = run_preset_multi(preset)
    metrics = combined_metrics(preset["initialEquity"], merged)
    print(f"  Combined: PnL=${metrics['net_pnl']:,.0f}  DD=${metrics['max_dd_$']:,.0f}  "
          f"DD%={metrics['max_dd_%']:.2f}  N={metrics['trades']}")
    for sym, st in leg_summary.items():
        print(f"  {sym}: trades={st['trades']}, pnl=${st['pnl']:,.0f}")
    print()

    res_seq = simulate_sequential(merged, preset["initialEquity"])
    print_sequential_report(preset["name"], res_seq)
    print()
    res_daily = simulate_daily(merged, preset["initialEquity"])
    print_daily_report(preset["name"], res_daily)


if __name__ == "__main__":
    main()
