"""Build winner_preset.json from the campaign's best config and insert into data/presets.json.

Run after sweep 08 confirms the final winner.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import fmt_summary, run_backtest, summarize  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402


# Winner config — filled in once sweeps converge.
STRATEGY = "HMASSLOsciV3"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

# Winner config (best effort — see REPORT.md for why both targets are not
# simultaneously satisfied). Highest Profit/DD ratio (10.16) AND PnL target
# satisfied (>$30k) across all >150 explored configurations on MGC. Only DD
# misses target by $730.
WINNER_PARAMS: dict = {
    "hw_range_on": True,
    "hma2_len": 34,
}
WINNER_RISK = 0.0052

# Blackouts added on top of the UI defaults (which are already 22:00-23:59 active
# for HMASSLOsciV3; all others inactive but kept in the preset for clarity).
EXTRA_BLACKOUTS = [
    (11, 0, 12, 0),
    (8, 0, 9, 0),
    (3, 0, 4, 0),
]


def main():
    es = make_engine_settings(
        STRATEGY,
        extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                               "end_hour": eh, "end_minute": em}
                              for (sh, sm, eh, em) in EXTRA_BLACKOUTS],
    )

    # Sanity-check the metrics
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"WINNER REPLAY: {fmt_summary(s)}")

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=es,
        metrics_summary=s,
        name=f"[Auto] {STRATEGY} — {SYMBOL} {INTERVAL} — best-effort MGC campaign",
    )
    out = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, out, insert_into_presets_json=True)
    print(f"[wrote] {out}")
    print("[inserted] data/presets.json")

    return s


if __name__ == "__main__":
    summary = main()
    # Echo the EXPECTED block to paste into verify_preset.py
    print("\n=== Paste into verify_preset.py EXPECTED ===")
    print(json.dumps({
        "net_pnl": summary["net_pnl"],
        "max_dd_$": summary["max_dd_$"],
        "trades": summary["trades"],
        "win_rate": summary["win_rate"],
        "profit_factor": summary["profit_factor"],
    }, indent=2))
