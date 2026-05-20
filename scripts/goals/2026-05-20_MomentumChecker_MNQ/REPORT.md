# MomentumChecker MNQ 7 m — campaign report (2026-05-20)

## TL;DR

| | Baseline (saved preset) | Winner | Δ |
|-|-|-|-|
| PnL              | **-$7,727**     | **+$62,262**    | +$69,989 |
| Drawdown ($)      | $22,178         | $2,431          | -$19,747 (-89 %) |
| Drawdown (%)      | 40.2 %          | 4.9 %           | -35.3 pp |
| Trades            | 3,220           | 764             | -76 % |
| Win rate          | 35.9 %          | 40.1 %          | +4.2 pp |
| Profit factor     | 0.98            | 1.53            | +0.55 |
| Avg win / loss     | $366 / -$209    | $586 / -$255    | +60 % / -22 % |
| **P/DD**          | -0.35           | **25.6**        | — |

DD-budget: ≤ $2,500 (strict). The winner sits at $2,431, ~$69 below the cap.

## Insight ladder (where the gains came from)

1. **`min_gap` is the binding entry constraint.** With every module emitting 1 pt and 8 modules, total addressable score range is large; the long/short_threshold only kicks in around 9. The probe showed `long_threshold ≤ 7` was a no-op (identical trade set). `min_gap=9` cut trades 3,220 → 1,009 and gave **+$19,108** PnL by itself. (sweep `01_thresholds_gap.py`)
2. **`rr_tp=2.5`** then added **+$8,616** with no DD penalty — the strategy's WR (~35 %) is right at the break-even point for R:R=2 so any extra R extends the edge. Lower R:R *hurt* (more WR but smaller wins fail to cover commissions).
3. **`tick_buffer=0`** removed slippage padding the strategy adds to its SL — net win because the slight extra hit-rate on SL is more than offset by the smaller realised loss per trade. Tiny PnL gain (~$500) with a meaningful DD cut.
4. **`hw_extreme_filter_on=True`** (with `hw_extreme=20`) was the single biggest single-flag win: **+$10,755** PnL and DD ≈ flat. The filter blocks trades after the HyperWave crossover happened in extreme territory — these are the late "I'm just chasing" entries that pay poorly.
5. **`rob_on=False`** (disable Rob Reversal). At baseline it *helped* (sweep 0c); at the rr2.5/gap9 stack it *hurt* by +$3.6k worth of bad signals. This is a non-monotone interaction — the value of Rob Reversal is conditional on the rest of the filter stack. **Worth re-checking if other levers change.**
6. **Indicator length tweaks** added another ~$9k over the unsmoothed Phase 4 stack:
   - `mf_smooth=5` (was 6) → +$4.4k
   - `st_atr=14` (was 10) → +$1.1k
   - `ema_sec_len=20` (was 9) → +$1.3k
   - `amp_mult=2.5` (was 2.0) → +$1.2k
7. **Per-module point weights** (Phase 7) gave **nothing**: `pts_hw_value` and `pts_sig_extreme` literally don't matter once the gap constraint is binding (every changed-pts sim returned identical trades). All other pts shifts hurt.
8. **Blackouts** on the bad-PnL hours brought the campaign over the DD finish line:
   - Hour-bucket analysis showed -$7,249 lost in eight hours (`01, 09, 13, 17-20`).
   - `BO 17:00-21:00 + 13:00-14:00` cut DD from $3,420 → $2,237 while adding +$2,377 PnL. First DD-valid config.
9. **Adding `09:00-10:00`** as a third blackout window gave another +$3,444 PnL with no DD change.
10. **Risk per trade** is a linear amplifier (same trade set, scaled positions). At 0.6 % we ride right up against the DD cap with PnL=$60,356 on the 3-blackout base.
11. **Daily limits** (`win=800 / loss=700`, after_close) added the final +$1,906 by cutting bad days short while letting normal days play through. `intra_bar` mode produced higher PnL on rare days but at a DD cost — `after_close` was the right call.

## Final-config attribution (additive estimate, holding everything else)

| Lever                                      | PnL impact | DD impact | Stack stage |
|---|---:|---:|---|
| Baseline (saved preset)                    |   -$7,727 |    $22,178 |   |
| `min_gap=9`                                |  +$19,108 |   -$15,332 | Phase 1 |
| `rr_tp=2.5`                                |  +$8,616  |   -$1,577  | Phase 2 |
| `tick_buffer=0`                            |  +$502    |   -$847    | Phase 3 |
| `hw_extreme_filter_on=True`                |  +$10,753 |   -$591    | Phase 3 |
| `rob_on=False`                             |  +$3,514  |   -$615    | Phase 3 |
| `mf_smooth=5`                              |  +$4,425  |   -$561    | Phase 5 |
| `st_atr=14`                                |  +$1,088  |   -$210    | Phase 5 |
| `ema_sec_len=20`                           |  +$1,262  |   -$305    | Phase 5 |
| `amp_mult=2.5`                             |  +$1,240  |   -$146    | Phase 5 |
| Blackout 17-21 + 13-14                     |  +$2,377  |   -$1,183  | Phase 9 |
| + Blackout 9-10                            |  +$3,444  |    +$0     | Phase 10 |
| Risk 0.5 % → 0.6 %                          |  +$10,870 |    +$194   | Phase 10 |
| Daily limits 800/700 AC                    |  +$1,906  |    +$0     | Phase 11 |
| **Total (winner)**                          | **+$62,262** | **$2,431** | |

Note: individual lever impacts are best-estimate (each was measured by 1-D sweep at its phase's stack, then re-checked in combo). Real combined effect is super-additive in PnL (1+1>2) because filters reinforce each other.

## Things tried that didn't help

- **All seven non-`min_gap` threshold/gap sweeps** in Phase 1 (long_threshold ≤ 7, short_threshold any, max_candle_pct except 0.4) — `min_gap` dominates so other levers are no-ops.
- **`pts_*` sweeps** (Phase 7) — same reason; the gap constraint is binding.
- **Disabling other modules** (`alligator_off`, `osc_off`, `ema_off`, etc.) — these crater the trade count because the modules each contribute the scoring points the gap relies on. Once `pts_*` are weighted equally, killing a module removes its addressable scoring contribution.
- **`use_heikin_ashi=True`** — strict regression (-$6k PnL).
- **`signal_length`, `hyper_wave_length`, `hma1_len`, `hma2_len`, `stc_length`, `stc_fast_len`, `st_mult`** — within the tested grids these did not improve P/DD at the Phase 4 stack.
- **Intra-bar daily limits** (`intra_bar` mode) — they cap dollar risk per day strictly but kill the PF (the limit fires mid-trend on bad luck days and the strategy can't recover within the same session).

## Risks / known limitations

1. **`mf_length=35` left untouched.** User memory flags `mf_length` as historically non-monotone. The Phase 5 sweep showed `mf_length=33` was marginally better (P/DD 8.73 vs base 9.13 — actually worse on P/DD ratio, so skipped). Re-sweep if migrating to other symbols.
2. **`rob_on=False` is condition-sensitive.** The Rob Reversal module *helped* at the baseline stack and *hurt* at the tightened-gap stack. Any future change to the filter stack should re-test it.
3. **DD margin is tight ($69 below the $2,500 cap).** A change of upstream data or any small param drift could nudge it over.
4. **Most trades are concentrated outside the four blackout windows**, which is consistent with the strategy expectations. Real-time deployment should keep these windows active (and reconfirm they remain bad windows after each DST transition; campaign times are reference-Brussels).
5. **The hour-9 blackout's value is small (+$3.4k).** If the user removes the 9-10 window after deployment, expected PnL is closer to $58k with DD still ~$2.4k.

## Top-5 alternatives (in case the user wants different tradeoffs)

| Rank | Config | PnL | DD | P/DD | Comment |
|-:|-|-:|-:|-:|-|
| 1 | **Winner** — +9-10 + DW=800/DL=700 AC + r0.6 | **$62,262** | **$2,431** | 25.6 | Best PnL within DD budget |
| 2 | +9-10 + risk=0.60 % (no daily limits) | $60,356 | $2,431 | 24.8 | Simpler — drops daily limits |
| 3 | +9-10 + DW=800/DL=700 AC + r0.55 % | $55,928 | $2,213 | 25.3 | More DD headroom |
| 4 | basic (no +9-10) + DW=800/DL=700 + r0.6 % | $56,764 | $2,439 | 23.3 | If user doesn't want the 9-10 window |
| 5 | +9-10 + DW=1000/DL=700 IB + r0.5 % | $48,806 | $1,889 | 25.8 | Lowest DD ($1.9k) — bigger safety margin |

## Sim budget accounting

| Phase | Sims | Cumulative | Note |
|-|-:|-:|-|
| 0 baseline + 0b/0c probes | 22 | 22 | confirmed strategy salvageable |
| 1 thresholds/gap | 31 | 53 | found min_gap=9 |
| 2 risk geometry | 36 | 89 | found rr_tp=2.5 |
| 3 combo + module triage | 24 | 113 | hw_ext, rob_off emerge |
| 4 filter combos | 30 | 143 | $34k baseline forming |
| 5 indicator lengths | 101 | 244 | biggest sweep |
| 6 indicator combos | 25 | 269 | $43.7k locked |
| 7 pts weights | 37 | 306 | no improvement |
| 8 hour analysis | 1 | 307 | bucketing only |
| 9 blackouts | 25 | 332 | first DD-valid configs |
| 10 fine-tune | 37 | 369 | risk 0.6 % crowned |
| 11 final combo | 23 | 392 | **WINNER** $62.3k/$2.43k |
| Total | **392** | | well under 500 budget |
