"""Phase 8 (v2) — Fine-tune the Pareto frontier.

After P7:
  Max PnL under V1 ceiling: D_hma_slow @ 0.60% → $75,497 / $3,012
  Best $DD < $2k:           A_amp35_only @ 0.40% → $45,445 / $1,863

Gaps to fill:
  - $DD ∈ ($1,900-$2,300]: only $44-50k — can we push past $55k?
  - $DD ∈ ($2,300-$2,700]: gap — can we hit $55-70k?
  - $DD ∈ ($2,700-$3,074]: $72-75k — can we squeeze more?

Strategy:
  1. Fine risk sweep on the top 4 configs (0.40 to 0.65% in tight steps)
  2. Add be_at_rr to D_hma_slow @ ~0.50% (might compress DD while keeping PnL)
  3. Test pts_hma_slow with ssl=80 (was promising in P1)
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
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, anchor_engine,
)


# Promote D_hma_slow as the leader to fine-tune around
LEADER = {
    "amp_mult": 3.5,
    "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5,
}

# Other strong candidates
A_AMP35 = {"amp_mult": 3.5}
A_HS_STA10 = {"amp_mult": 3.5,
              "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5,
              "st_atr": 10, "tick_buffer": 2}
C_STC65_TB2 = {"amp_mult": 3.5, "tick_buffer": 2, "stc_slow_len": 65}

LEAD = {
    "D_amp35_hma_slow":   LEADER,
    "A_amp35_only":       A_AMP35,
    "C_amp35_tb2_stc65":  C_STC65_TB2,
    "Combo_amp35_full":   A_HS_STA10,
}


def _common(risk):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=anchor_engine(),
    )


def _override(**kw):
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 8 (v2) — Pareto frontier fine-tune")
    print("=" * 110)

    results = []
    t0 = time.time()

    # ---- Section 1: fine risk sweep on all leading configs ----
    print("\n--- Section 1: fine risk sweep on 4 leading configs ---")
    RISKS = [0.0036, 0.0038, 0.0040, 0.0042, 0.0044, 0.0046, 0.0048, 0.0050,
             0.0052, 0.0054, 0.0056, 0.0058, 0.0060, 0.0062, 0.0064]
    for cfg_name, cfg in LEAD.items():
        for r in RISKS:
            label = f"{cfg_name} risk={r*100:.2f}%"
            s = bench(label, strategy_params=_override(**cfg), **_common(risk=r))
            results.append((label, s))

    # ---- Section 2: be_at_rr × D_hma_slow at risk 0.50-0.60% ----
    print("\n--- Section 2: be_at_rr × D_hma_slow ---")
    for be in [1.0, 1.25, 1.5, 1.75]:
        for r in [0.0050, 0.0055, 0.0060]:
            label = f"D_hma_slow be={be} risk={r*100:.2f}%"
            params = dict(LEADER); params["be_at_rr"] = be
            s = bench(label, strategy_params=_override(**params), **_common(risk=r))
            results.append((label, s))

    # ---- Section 3: pts_hma_slow with ssl=80 (P1 alternative) ----
    print("\n--- Section 3: pts_hma_slow ssl=80 hw=5 (P1's other top combo) ---")
    for r in [0.0045, 0.0050, 0.0055, 0.0060]:
        params = {"amp_mult": 3.5,
                  "pts_hma_slow": 1, "ssl_len": 80, "hma_window_bars": 5}
        label = f"amp=3.5 hma_slow_ssl80 risk={r*100:.2f}%"
        s = bench(label, strategy_params=_override(**params), **_common(risk=r))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(3074, "V1 ceiling"), (2500, "moderate"), (2000, "TARGET")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 25 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
            print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("Pareto frontier (refined)")
    print("=" * 110)
    buckets = [(0, 1400), (1400, 1600), (1600, 1800), (1800, 2000), (2000, 2200),
               (2200, 2400), (2400, 2600), (2600, 2800), (2800, 3074)]
    for lo, hi in buckets:
        configs_in = [(l, s) for l, s in results if lo < s["max_dd_$"] <= hi]
        if configs_in:
            best = max(configs_in, key=lambda x: x[1]["net_pnl"])
            l, s = best
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  PnL=${s['net_pnl']:>7,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")
        else:
            print(f"  $DD ∈ ({lo:>4},{hi:>4}]:  (no configs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
