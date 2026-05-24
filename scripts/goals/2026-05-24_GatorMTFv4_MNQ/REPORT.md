# GatorMTFv4 MNQ 1m — Campaign Report

**Date**: 2026-05-24
**Strategy**: GatorMTFv4
**Symbol**: MNQ
**Interval**: 1m
**Period**: 2025-01-02 → 2026-05-22 (full available MNQ 1m data)
**Initial Equity**: $50,000
**Max Contracts**: 20
**Goal**: Maximize PnL with `max_dd_$ ≤ $2,500`
**Budget**: 1,000 simulations
**Simulations used**: ~270

## Result — `BESTPNL-MNQ GatorMTFv4 - MNQ 1m v1`

| Metric         | Baseline (seed)     | Winner          | Δ          |
|----------------|---------------------|-----------------|------------|
| PnL            | -$12,766            | **+$13,130**    | +$25,896   |
| max_dd_$       | $20,419             | **$2,461**      | −$17,958   |
| Total trades   | 3,773               | 1,439           | −2,334     |
| Win Rate       | 50.3 %              | 37.8 %          | −12.5 pp   |
| Profit Factor  | 0.97                | **1.17**        | +0.20      |
| Avg Win        | $210                | $170            | −$40       |
| Avg Loss       | -$219               | -$89            | +$130      |
| Risk per trade | 0.50 %              | 0.26 %          | −0.24 pp   |

Note: the seed preset was originally backtested with start 2025-01-08; the
winner uses the full available data (2025-01-02 onwards). The 6 extra calendar
days add 15 trades and shift PnL by only −$26 vs the 2025-01-08 run — DD is
unchanged ($2,461).

**Verification**: `verify_preset.py` prints `✅ MATCH`.

## Winning Configuration

### Strategy params (deltas vs. seed)

| Param          | Seed   | Winner | Reason |
|----------------|--------|--------|--------|
| `final_rr`     | 1.0    | **2.0** | Biggest PnL lever — sweep 1 showed +$42k swing from RR 1→2. |
| `cooldown_bars`| 7      | **90**  | Universal DD reducer in sweep 2 — cooldown 90 dominates 14/30/60/120. |
| `amp_mult`     | 2.0    | **1.0** | Tighter HMA ribbon — fewer marginal entries, smaller DD. |
| `case_c_on`    | True   | **False** | Counter-canal-with-sig-extreme; sweep 3 case bitmask: 1101 strictly Pareto over 1111. |

All other params kept at seed (incl. `ssl_mult=0.2`, `trigger_tf_minutes=7`,
`ema_len=7`, `hma1_len=13`, `hma2_len=21`, `sl_lookback=1`, `sl_min_pct=0.15`,
`tick_buffer=2`, MFI/HW filters at defaults).

### Engine settings

- `auto_close_hour = 22, auto_close_minute = 0` (CME daily close)
- `daily_win_limit` / `daily_loss_limit`: **OFF** (per user constraint)
- **Active blackouts** (reference Brussels time): 10 windows
  | Start | End   | Origin |
  |-------|-------|--------|
  | 06:00 | 07:00 | sweep 5 — losing hour (-$759 cum) |
  | 11:00 | 12:00 | sweep 5 — near-zero PnL |
  | 12:00 | 13:00 | sweep 5 — near-zero PnL |
  | 14:00 | 15:00 | sweep 5 — losing hour (-$3,439 cum) |
  | 16:00 | 17:00 | sweep 5 — losing hour (-$2,319 cum) |
  | 17:00 | 18:00 | sweep 5 — sub-$1k positive |
  | 19:00 | 20:00 | sweep 5 — losing hour (-$1,948 cum) |
  | 21:00 | 22:00 | sweep 5 — near-zero PnL |
  | 22:00 | 23:59 | seed (auto-close adjacent) |
  | 23:00 | 23:59 | sweep 5 — redundant with 22:00-23:59 but kept for clarity |

### Risk

`risk_per_trade = 0.26 %`. Sweep 7 picked the integer-contract sweet spot:
- 0.25% → DD $2,212 (under, leaves PnL on table)
- **0.26% → DD $2,461 / PnL $13,156** ← chosen
- 0.27% → DD $2,832 (over budget)
- 0.30% → DD $3,740 (jump due to contract rounding)

## Campaign Journey

| Step | What I did | Best PnL | Best DD$ | Notes |
|------|------------|----------|----------|-------|
| 0    | Baseline replay | -$12,766 | $20,419 | Verified ±$1 vs preset; harness bug found and fixed (missing `one_trade_per_window_mtf` in SimulatorConfig). |
| 1    | 1-D scan of ~17 params | +$29,756 | $5,939 | `final_rr=2.0` alone hits $29.7k; `cooldown=120` cuts DD to $5.9k. MFI/tick_buffer/sl_lookback ineffective. |
| 2    | `final_rr × cooldown × amp_mult` (60 sims) | +$23,616 | $5,935 | `rr=2.0/cd=90/amp=1.0` best PnL+DD balance. Cooldown=90 universally wins. |
| 3    | Cases × SL × ssl_mult (43 sims) | +$23,540 | $5,935 | **ABCD=1101** (case C off) strictly improves on 1111. Other levers neutral. |
| 4    | Hour-of-day analysis | — | — | Losing hours: H14 (-$3,439), H16 (-$2,319), H19 (-$1,948), H23, H06. Mon as a day was also losing but blackouts can't gate by DoW. |
| 5    | Blackout combos (22 sims) | +$29,329 | $5,740 | **9-hour aggressive blackout** wins. Counter-intuitive: single-hour blocks of H14/H16 *hurt* (likely cooldown / one-trade-per-window slot interaction), but 9-hour combo +$5,789 PnL gain. |
| 6    | Risk sweep 0.20–1.0 % | +$60,711 | $13,125 | Linear-ish PnL scaling. risk=0.25% → DD $2,212 (under budget!). |
| 7    | Risk fine 0.24-0.32 % | **+$13,156** | **$2,461** | risk=0.26% — max risk that keeps DD under $2,500. Contract rounding creates a sharp jump at 0.27→0.29. |

## Key Insights

1. **`final_rr=1.0` was actively destructive**. At WR ≈ 50%, RR=1 is a pure
   coinflip; commissions consistently dragged PnL negative. Doubling RR to 2.0
   dropped WR to 37% but flipped expectancy strongly positive (PF 0.97 → 1.10+).

2. **`cooldown_bars=90` is a tight global optimum**, not monotone. Sweep 1
   showed 14, 60, 120 all worse than 90; sweep 2 confirmed across every RR/amp
   combo. Likely a structural fit to MNQ M7 trigger spacing.

3. **Case C (counter-canal + osc bearish for long)** carries near-zero edge
   but adds variance. Turning it off gives +$2,300 PnL and similar DD.

4. **Hour-blackout interactions are non-trivial**. Single losing-hour blocks
   often *worsen* PnL because the one-trade-per-window slot stays free and gets
   filled by a worse setup later in the same window. The aggressive 9-hour
   blackout works because it removes enough setup territory that the slots
   genuinely don't refill on the same day.

5. **MFI parameters are inert**. `mf_length` and `mf_smooth` produced identical
   metrics across all values. The strategy uses MFI sign to label cases A vs B
   (or C vs D) but, with all four cases on, the union covers both signs — so
   MFI doesn't filter any bars. Worth removing from the Pine if confirmed.

6. **Contract-rounding creates discrete risk steps**. Sweeping risk 0.20-0.32%
   showed DD plateaus then jumps as integer contract counts shift. The 0.26%
   sweet spot maximizes PnL inside the $2,500 DD budget.

## Files

- `sweeps/_campaign.py` — constants
- `sweeps/00_baseline.py` — baseline replay
- `sweeps/01_one_d_scan.py` — 17-param 1-D scan
- `sweeps/02_combo_top_levers.py` — `rr × cd × amp` combo
- `sweeps/03_cases_and_sl.py` — case bitmask + SL/ssl_mult tuning
- `sweeps/04_hour_analysis.py` — H+DoW bucket analysis
- `sweeps/05_blackouts.py` — blackout combo sweep
- `sweeps/06_risk_and_final.py` — risk 0.20-1.0 % + final fine-tuning
- `sweeps/07_risk_fine.py` — fine risk grid 0.24-0.32 %
- `build_winner.py` / `winner_preset.json` — preset writer + JSON
- `verify_preset.py` — replay & match against expected metrics (✅ MATCH)
- `logs/*` — per-sweep stdout

## Notes for the user

- Le preset est inséré en tête de `data/presets.json` sous le nom
  `BESTPNL-MNQ GatorMTFv4 - MNQ 1m v1`. Il devrait apparaître directement
  dans les favoris de l'UI.
- Toutes les contraintes immutables ont été respectées: symbol MNQ, interval
  1m, max contracts 20, daily win/loss limits OFF, période complète.
- `auto_close_hour=22` conformément à la règle des goal campaigns.
- Sweep budget consumed: ~270/1000 simulations. Plenty of head-room if you
  want to try other strategy axes (e.g. a non-default `tp_mode`, alternate
  `trigger_tf`, or partial TP support once the engine supports it).
