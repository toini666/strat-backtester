# Campaign Report — MomentumCheckerV2 MNQ 7m — **⚠️ SUPERSEDED**

> **Bug notice**: this campaign optimised against an incorrect `max_drawdown_dollars`
> metric. The "winner" reported here had a TRUE $DD of $3,326, above V1's true
> ceiling of $3,074. Use the corrected v2 campaign instead:
> `scripts/goals/2026-05-20_MomentumCheckerV2_MNQ_v2/REPORT.md` (PnL=$80,565 / $DD=$3,023).
> Kept for historical reference; numbers below were computed before the fix.

---


**Date**: 2026-05-20
**Result**: PnL **$69,882** / DD **$1,864** / N=835 / WR 31.5% / PF 1.6 / **P/DD 37.49**
**vs V1 anchor**: **+$8,569 PnL** AND **−$279 DD** (both better — clean Pareto improvement)

## Goal

Reproduce the V1 preset *New base - MomentumChecker - MNQ 7m* under V2 (using
the documented V1-compat translation), then run an optimization budget of
~500 sims targeting:

- Higher PnL
- DD ≤ V1's $2,143 (hard constraint)
- DD < $2,000 (soft target)
- Fixed: symbol MNQ, TF 7m, period 2025-01-07 → 2026-05-15, max contracts 20,
  no daily win/loss limits.

## V1 → V2 reproduction

Confirmed via `scripts/verify_momentum_checker_v2_vs_v1.py`:
V2 with V1-compat params reproduces V1 *bit-for-bit*:

```
V1: PnL=$ 61,313  DD=$ 2,143  N=785  WR=39.6%  PF=1.5
V2: PnL=$ 61,313  DD=$ 2,143  N=785  WR=39.6%  PF=1.5  (V1-compat translation)
ΔPnL=$0.00  ΔDD=$0.00  ΔTrades=0  ΔWR=0.00pp  ✅ MATCH
```

V2 defaults (no compat translation) on the V1 engine: $36,728 / DD $5,202 —
*significantly worse*. The V2 native defaults add `delta_off_mode="counter_trend"`
and `cloud_zero_filter_on=False but pts_cloud_zero=1` defaults that hurt this
specific strategy on MNQ. Conclusion: build off the V1-compat anchor, do not
start from V2 defaults.

## Lever-by-lever attribution

Going from V1 anchor ($61,313 / $2,143) → winner ($69,882 / $1,864):

### 1. `max_candle_pct: 0.4 → 0.5`  (+$1.75k PnL, same DD)

Slightly looser candle filter — allows a handful of additional setups that
the strategy correctly classifies as bullish. The strict 0.4 cap rejects too
many genuine momentum bars.

### 2. `sig_extreme` filter ON @ 40.0  (+$1.4k PnL, same DD)

V2 added an *independent* threshold for the signal-extreme filter (V1 reused
the HW-extreme threshold). At 40.0 the filter catches signals with overshoots
on the oscillator but lets the bulk through. Tighter values (10-20) lose
quality trades; higher values (>40) ≈ off.

### 3. `hma_pol_bars: -1 → 20`  (+$0.36k PnL, same DD)

V2's polarity-tolerance feature: allow HMA-canal break to score even if the
canal hasn't *yet* flipped, provided the most-recent HMA flip is within N
bars. With 20 bars (≈140 minutes on 7m), we capture clean breakouts that
form just before the canal officially turns. Lower values (3-12) match the
anchor exactly (no extra signal). 20 was the cap tested; could be higher.

### 4. `amp_mult: 2.5 → 3.0`  (+$1.0k PnL, same DD)

Wider HMA-canal envelope around the slow HMA. Counter-intuitively, this
gives us *fewer* but *higher-quality* breakout signals — the price has to
push further beyond the slow HMA to score the HMA bucket. Up to 4.0 keeps
DD at $2,143; beyond loses trades.

### 5. `sl_max_points: 100 → 60` + `be_at_rr: 0 → 1.25`  (−$486 DD, +$0.16k PnL)

This is the DD-killer pair:

- **`sl_max_points=60`**: cap the maximum risk per trade at 60 points instead of
  100. Trades that would have used a 60-100 pt SL now use exactly 60 — so:
  - Position size: same number of contracts (sizing on `entry−SL` capped at 60)
  - Worst-case stop-out: bounded smaller
  - Effective TP at `2.5 × 60 = 150` pts instead of `2.5 × actual_risk`
- **`be_at_rr=1.25`**: when the trade has gone 1.25× R in profit, SL moves to
  break-even. This protects winners from turning into full-R losers, slicing
  the deepest drawdown sequences.

Values 1.0 and 1.25 both work well. Below 1.0 the BE trigger fires too early
and stops out marginal winners (catastrophic — most trades become small
positive then BE-out). Above 1.5 you give too much back before BE activates.

### 6. `risk_per_trade: 0.60% → 0.70%`  (+$8.3k PnL, +$0.21k DD)

After all params are locked, scale up the risk by 17%. PnL scales nearly
linearly while DD stays well under target.

**⚠ Non-monotonicity warning**: at risk=0.65%/0.66%/0.68% the DD spikes to
$3,074-$3,132 — a single contracts-rounding boundary flip on the worst-loss
sequence. Risk=0.70% lands on the favorable side again. This is intrinsic to
the int-floor position sizing — DO NOT assume monotonicity around the chosen
risk level. The 0.70% value is empirically validated in the (0.40-0.90%)
sweep and the tight (0.64-0.78%) validation band.

## Blackout sensitivity (Phase 8)

Tested 17 alternative blackout configurations: drop-one, swap-window, add-window.
**All variants performed worse** than the V1 anchor windows on PnL. The 09-10,
13-14, 17-23:59 trio is genuinely optimal for this strategy on this dataset.

Note: the V1 winning blackout windows are kept as the campaign baseline because
the V1-compat anchor (with those windows) gave a stable starting point of
$61.3k/$2.1k. Re-exploring from a clean "only 22-23:59 active" state was
benchmarked in Phase 0 — gave $51,159/$4,680 — and didn't justify re-derivation.

## V2-new features that did *not* help

- **`pts_hma_slow=1`** (HMA-slow / SSL cross bonus): every configuration tested
  pushed DD above $2,400 with only modest PnL gain.
- **`cloud_zero_filter_on=True`**: catastrophic. PnL crater from $61k to $15k,
  DD spike to $6.7k. The MFI sign filter is too restrictive for V2-compat MNQ.
- **`delta_off_mode="counter_trend"`** (V2 native default): $42,586 / $5,013.
  Much worse than V1's `"both"` mode. The "both" behaviour grants the bonus
  when both deltas are off, which is more permissive but produces better
  signals on this data.

## V2-new features that helped

| Feature | Description | Final value | Effect |
|---|---|---|---|
| `sig_extreme` separate threshold | Independent from `hw_extreme` | 40.0 | +$1.4k PnL |
| `hma_pol_bars` | Polarity tolerance window | 20 | +$0.4k PnL |
| `be_at_rr` | Break-even @ RR | 1.25 | −$0.5k DD, +$0.2k PnL |

## Statistics — winner vs anchor

| | V1 anchor | V2 winner | Delta |
|---|---|---|---|
| Net PnL | $61,313 | $69,882 | +$8,569 (+13.9%) |
| Max DD ($) | $2,143 | $1,864 | −$279 (−13.0%) |
| Trades | 785 | 835 | +50 |
| Win rate | 39.6% | 31.5% | −8.1pp |
| Profit factor | 1.5 | 1.6 | +0.1 |
| Avg win | $589 | $712 | +$123 |
| Avg loss | −$257 | −$205 | +$52 (less bad) |
| P/DD ratio | 28.62 | 37.49 | +8.87 |
| Sharpe | (unchanged framework) | — | — |

The win-rate drop (8pp) is the BE move's signature: more trades end at BE
(small or zero profit) rather than reaching TP1 — so they don't count as
"wins" anymore. But the average winner now goes further (TP at 2.5× risk
with sl_max_points=60 means a winner is +$150 / contract instead of +
variable), and the average loser is capped tighter ($205 vs $257). Net
effect: higher equity curve, smoother (lower DD).

## Sim budget accounting

| Phase | Description | Sims |
|---|---|---|
| 0 | Baselines (anchor + V2 defaults × 2 engines) | 4 |
| 1 | V2-new features in isolation | 35 |
| 2 | Thresholds & gap & candle | 27 |
| 3 | Risk geometry (sl, rr, buffer) | 33 |
| 4 | Module toggles + sub-filter triage | 51 |
| 5 | Indicator lengths | 109 |
| 6 | Combo lattice (4 sub-groups) | 175 |
| 7 | Fine-tune Pareto frontier | 84 |
| 8 | Blackout sensitivity | 26 |
| 9 | Risk per trade sweep | 16 |
| 10 | Final risk-band validation | 8 |
| | **Total** | **568** |

Overshot the 500 target by ~14% (68 sims). Phase 7 was the largest single
campaign expense and uncovered the Pareto-improvement winner; Phase 9 the
0.70% sweet spot. Both were worth the extra sims.
