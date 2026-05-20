"""Phase 9 — Risk fine-tune around both winners.

W_LowDD :  $61,474 / DD=$1,657 / N=835  @  risk=0.60%
W_MaxPnL: $65,245 / DD=$2,143 / N=770  @  risk=0.60%

Can a small risk bump push the LowDD config to higher PnL while staying
under $2k DD? Conversely, can a risk cut on MaxPnL bring it under $2k?
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    ANCHOR_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
)


W_LOWDD = dict(ANCHOR_PARAMS)
W_LOWDD.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
    "be_at_rr": 1.25,
    "sl_max_points": 60.0,
})

W_MAXPNL = dict(ANCHOR_PARAMS)
W_MAXPNL.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
})


def main() -> int:
    print("=" * 110)
    print(f"PHASE 9 — Risk fine-tune  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    RISKS = [0.0040, 0.0050, 0.0055, 0.0060, 0.0065, 0.0070, 0.0080, 0.0090]
    for r in RISKS:
        label = f"W_LOWDD risk={r*100:.2f}%"
        s = bench(label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
            start=START, end="2026-05-15T22:59",
            initial_equity=INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=MAX_CONTRACTS,
            engine_settings=anchor_engine(),
            strategy_params=W_LOWDD,
        )
        results.append((label, s))

    for r in RISKS:
        label = f"W_MAXPNL risk={r*100:.2f}%"
        s = bench(label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
            start=START, end="2026-05-15T22:59",
            initial_equity=INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=MAX_CONTRACTS,
            engine_settings=anchor_engine(),
            strategy_params=W_MAXPNL,
        )
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 20 by PnL with DD ≤ $2,143")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by PnL with DD ≤ $2,000")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
