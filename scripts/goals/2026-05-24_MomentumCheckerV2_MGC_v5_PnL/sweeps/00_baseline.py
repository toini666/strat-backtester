"""Phase 0 - Reproduce the v4 WR WINNER baseline through the shared harness.

Expected (from v4 expected_winner_metrics.json):
    PnL  = $28,161.82
    DD$  = $2,438.44
    N    = 1,056
    WR   = 51.0 %
    PF   = 1.29
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _campaign import seed_kwargs  # noqa: E402  (campaign-local)


def main() -> None:
    print("Phase 0 - baseline reproduction of v4 WR WINNER")
    print("-" * 80)
    s = bench("v4 WR WINNER (seed)", **seed_kwargs())
    print()
    expected = dict(net_pnl=28161.82, max_dd=2438.44, trades=1056, wr=51.0)
    ok_pnl = abs(s["net_pnl"] - expected["net_pnl"]) < 5
    ok_dd  = abs(s["max_dd_$"] - expected["max_dd"]) < 5
    ok_n   = s["trades"] == expected["trades"]
    ok_wr  = abs(s["win_rate"] - expected["wr"]) < 0.1
    print(f"PnL match: {ok_pnl}  DD match: {ok_dd}  N match: {ok_n}  WR match: {ok_wr}")


if __name__ == "__main__":
    main()
