"""Phase 10 — Final risk-band validation around 0.70%.

W_LOWDD risk=0.65% had unexpected DD spike to $3,074 — likely a single
unlucky sequence. Confirm the 0.66-0.74% band is smooth and lock the
final winner.
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


def main() -> int:
    print("=" * 110)
    print(f"PHASE 10 — Final risk-band validation  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    # Fill the gap between 0.65 and 0.80
    RISKS = [0.0064, 0.0066, 0.0068, 0.0070, 0.0072, 0.0074, 0.0076, 0.0078]
    for r in RISKS:
        label = f"W_LOWDD risk={r*100:.2f}%"
        s = bench(label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
            start=START, end=END,
            initial_equity=INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=MAX_CONTRACTS,
            engine_settings=anchor_engine(),
            strategy_params=W_LOWDD,
        )
        results.append((label, s, r))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 110)
    print("Risk band — DD ≤ $2,000 only")
    print("=" * 110)
    sub2k = [(l, s, r) for l, s, r in results if s["max_dd_$"] <= 2000.0]
    for l, s, r in sorted(sub2k, key=lambda x: -x[1]["net_pnl"]):
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("Full risk band:")
    for l, s, r in sorted(results, key=lambda x: x[2]):
        flag = "✅" if s["max_dd_$"] <= 2000.0 else "⚠"
        print(f"  {flag} risk={r*100:.2f}%: PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
