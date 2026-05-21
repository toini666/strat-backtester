"""Phase 8 (v3) — Compile best stack + fine risk-band sweep.

P6 anchor (the new best at risk=0.66%):
  sl_max=40, tb=2, pts_ema_align=2, min_gap=10
  → PnL=$87,448 / DD=$2,933 / P/DD=29.82

Step 1: compile additional deltas on top of P6
Step 2: fine risk-band sweep at 0.005% increments
  - to find non-monotonic sweet spots
  - to identify the highest risk that keeps DD < $2,500
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, build_engine, seed_engine,
)

# P6 anchor — best so far at risk=0.66%
P6_ANCHOR = dict(BASELINE_PARAMS)
P6_ANCHOR.update({
    "sl_max_points": 40.0,
    "tick_buffer": 2,
    "pts_ema_align": 2,
    "min_gap": 10,
})

# Seed engine (with 13-14:30 lunch ext)
SEED_BLACKOUTS = [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]
# Try blackout: + 01-02
P7_BLACKOUTS = [(1, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]


def _common(engine, risk=None):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=(risk if risk is not None else RISK_PER_TRADE),
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
    )


def _override(**kw):
    p = dict(P6_ANCHOR)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 8 (v3) — Compile + fine risk-band")
    print("P6 anchor: sl_max=40, tb=2, pts_ema_align=2, min_gap=10")
    print("Target: PnL ≥ $80,565 AND DD < $2,500")
    print("=" * 110)

    results = []
    t0 = time.time()

    # ---------- STEP 1: stack additional small deltas on P6 -----------
    print("\n--- compile additional deltas on P6 ---")

    # P6 baseline at seed blackouts
    s = bench("[P6 anchor seed-bo]", strategy_params=P6_ANCHOR,
              **_common(seed_engine()))
    results.append(("[P6 anchor seed-bo]", s))

    # P6 + add 01-02 blackout
    eng_p7 = build_engine(P7_BLACKOUTS)
    s = bench("P6 + add 01-02", strategy_params=P6_ANCHOR, **_common(eng_p7))
    results.append(("P6 + add 01-02", s))

    # P6 + pts_sig_extreme=2 + sig_extreme=50  (P5 finding)
    s = bench("P6 + pts_sig_extreme=2 sig_ext=50",
              strategy_params=_override(pts_sig_extreme=2, sig_extreme=50.0),
              **_common(seed_engine()))
    results.append(("P6 + pts_sig_extreme=2 sig_ext=50", s))

    # P6 + sl_lookback=7  (P1 finding standalone)
    s = bench("P6 + sl_lookback=7", strategy_params=_override(sl_lookback=7),
              **_common(seed_engine()))
    results.append(("P6 + sl_lookback=7", s))

    # P6 + mcp=0.35
    s = bench("P6 + mcp=0.35", strategy_params=_override(max_candle_pct=0.35),
              **_common(seed_engine()))
    results.append(("P6 + mcp=0.35", s))

    # P6 + add 01-02 + pts_sig_extreme=2
    s = bench("P6 + 01-02 + pts_sig_extreme=2",
              strategy_params=_override(pts_sig_extreme=2, sig_extreme=50.0),
              **_common(eng_p7))
    results.append(("P6 + 01-02 + pts_sig_extreme=2", s))

    # P6 + add 01-02 + sl_lookback=7
    s = bench("P6 + 01-02 + sl_lookback=7",
              strategy_params=_override(sl_lookback=7),
              **_common(eng_p7))
    results.append(("P6 + 01-02 + sl_lookback=7", s))

    # P6 + add 01-02 + mcp=0.35
    s = bench("P6 + 01-02 + mcp=0.35",
              strategy_params=_override(max_candle_pct=0.35),
              **_common(eng_p7))
    results.append(("P6 + 01-02 + mcp=0.35", s))

    # ---------- STEP 2: choose best compiled stack as RISK_ANCHOR ----------
    valid_stack = [(l, s) for l, s in results]
    # Best by PnL with DD ≤ $2,933
    cands = [x for x in valid_stack if x[1]["max_dd_$"] <= 2933]
    if not cands:
        cands = valid_stack
    best_lbl, best_summary = sorted(cands, key=lambda x: -x[1]["net_pnl"])[0]
    print(f"\n  Best compiled stack: {best_lbl}")
    print(f"    PnL=${best_summary['net_pnl']:,.0f} / $DD=${best_summary['max_dd_$']:,.0f}")

    # Apply selected stack's params and engine
    if "01-02" in best_lbl:
        risk_engine = eng_p7
    else:
        risk_engine = seed_engine()

    # Re-derive params for the selected stack
    if "pts_sig_extreme=2" in best_lbl:
        risk_params = _override(pts_sig_extreme=2, sig_extreme=50.0)
    elif "sl_lookback=7" in best_lbl:
        risk_params = _override(sl_lookback=7)
    elif "mcp=0.35" in best_lbl:
        risk_params = _override(max_candle_pct=0.35)
    else:
        risk_params = dict(P6_ANCHOR)

    # ---------- STEP 3: fine risk-band sweep -----------
    print(f"\n--- fine risk-band sweep on best stack ({best_lbl}) ---")
    risk_results = []
    risk_values = [0.0040, 0.0045, 0.0048, 0.0050, 0.0052, 0.0054, 0.0055,
                   0.0056, 0.0057, 0.0058, 0.0059, 0.0060, 0.0061, 0.0062,
                   0.0063, 0.0064, 0.0065, 0.0066, 0.0067, 0.0068, 0.0070,
                   0.0072, 0.0075]
    for r in risk_values:
        label = f"risk={r*100:.2f}%  {best_lbl}"
        s = bench(label, strategy_params=risk_params, **_common(risk_engine, risk=r))
        risk_results.append((label, s, r))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    # Reports
    for cap, lbl in [(2933, "P6 DD"), (2500, "HARD CAP"), (2000, "stretch")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 20 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        if not valid:
            print("  (no candidates)")
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
                  f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    # Specifically the risk sweep
    print()
    print("=" * 110)
    print("Risk-band sweep (best stack), ordered by risk")
    print("=" * 110)
    for l, s, r in risk_results:
        warn = ""
        if s["net_pnl"] >= 80565 and s["max_dd_$"] <= 2500:
            warn = "  ★★★ HITS BOTH TARGETS"
        elif s["net_pnl"] >= 80565:
            warn = "  ✓ PnL target"
        elif s["max_dd_$"] <= 2500:
            warn = "  ◇ DD target"
        print(f"  r={r*100:.2f}%  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}{warn}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
