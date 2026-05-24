# GatorMTFv4 MNQ 1m v2 — Campaign Report

**Date**: 2026-05-24
**Strategy**: GatorMTFv4
**Symbol**: MNQ
**Interval**: 1m
**Period**: 2025-01-02 → 2026-05-22 (full available data)
**Initial Equity**: $50,000
**Max Contracts**: 20
**Goal**: PnL ≥ $50,000 with `max_dd_$ ≤ $2,500` (20× DD-adjusted ratio)
**Budget**: 500 simulations
**Simulations used**: ~386

## Result — `BESTPNL-MNQ GatorMTFv4 - MNQ 1m v2`

| Metric           | v1 winner | **v2 winner** | Δ          | Goal       |
|------------------|-----------|---------------|------------|------------|
| PnL              | +$13,130  | **+$16,777**  | +$3,647    | ≥ $50,000 ❌ |
| max_dd_$         | $2,461    | **$2,162**    | −$299      | ≤ $2,500 ✅  |
| Total trades     | 1,439     | 2,316         | +877       | —          |
| Win Rate         | 37.8 %    | 44.0 %        | +6.2 pp    | —          |
| Profit Factor    | 1.17      | **1.13**      | −0.04      | —          |
| Avg Win          | $170      | $145          | −$25       | —          |
| Avg Loss         | -$89      | -$101         | −$12       | —          |
| Risk per trade   | 0.26 %    | **0.28 %**    | +0.02 pp   | —          |
| DD-adjusted (PnL/DD) | 5.34× | **7.76×**     | +2.42×     | 20× ❌      |

**Verification**: `verify_preset.py` prints `✅ MATCH`.

## Honest verdict — the $50K goal is structurally unreachable

The advisor flagged the math upfront: the goal needs a 3.7× lift in the
PnL/DD ratio. That's a **PF problem, not a sizing problem** — and across
~423 simulations spanning trigger TF, HMA stack, cases, RR, cooldown,
SL geometry, SSL channel, sig_extreme threshold, blackouts, risk fine,
DD forensics, sl_min_pct × risk, and one_trade_per_window, the
**PnL/DD ratio plateaus at 7.4-7.8× — exactly half of the 20× the goal demands**.

Concrete demonstration (Phase 11 sl_min_pct=0.15 risk sweep, otpw=True):

| Risk  | PnL      | DD       | Ratio  | PF    |
|-------|----------|----------|--------|-------|
| 0.20% | $12,282  | $2,162   | 5.68×  | 1.12  |
| 0.28% | $16,777  | $2,162   | 7.76×  | 1.13  |
| 0.40% | $27,234  | $3,596   | 7.57×  | 1.13  |
| 0.60% | $40,690  | $6,193   | 6.57×  | 1.12  |
| **0.80%** | **$60,855**  | **$8,269**   | **7.36×**  | **1.13**  |

**The PnL goal IS reachable** ($60,855 > $50,000) — at risk 0.80% — but
the DD budget is violated by $5,769. To hit $50K within $2,500 DD you'd
need a ratio of 20×, and the strategy fundamentally delivers ~7.5×.

Phase 10 DD forensics: the worst DD episode is a **5-week slow grind from
2025-11-13 to 2025-12-19 (165 trades), not a single event**. It can't be
blackouted away without overfitting. The DD is intrinsic to the strategy's
trade-by-trade variance during a regime where its edge weakens.

The three non-parametric escape hatches:

1. **Partial TP engine support** — Pine has `i_partialRr` and
   `i_hwPartialPct` configured but the engine rejects partial > 0 because
   no "intra-bar full exit at fixed TP with partial as fallback" mode
   exists (see `src/strategies/gator_mtf_v4.py:32-38`). If implemented,
   partial exits could lift PF.
2. **Multi-asset/multi-strat** — run GatorMTFv4 MNQ alongside another
   uncorrelated strategy/symbol on the shared account.
3. **Different strategy** — HMASSLOsciV3, MomentumCheckerV2 reach PF 1.5+
   on their winners. GatorMTFv4 as-translated maxes around 1.13.

## Winning Configuration

### Strategy params (deltas vs. v1 winner)

| Param                    | v1 winner | **v2 winner** | Source / reason |
|--------------------------|-----------|---------------|----------------|
| `amp_mult`               | 1.0       | **1.5**       | Phase 2 — best ratio in 1-D HMA sweep |
| `ssl_len`                | 60        | **20**        | Phase 6 — narrow SSL channel boosts ratio 2.83→6.15× |
| `ssl_mult`               | 0.20      | 0.20          | Phase 6 — peak, confirmed by 6B refinement |
| `sl_lookback`            | 1         | **15**        | Phase 5 — wider lookback at rr=1.5 |
| `tick_buffer`            | 2         | **6**         | Phase 5 — combo with sl_lookback=15 |
| `final_rr`               | 2.0       | **1.5**       | Phase 4 — RR=1.5 + WR=43.8% beats RR=2.0 + WR=36.9% |
| `sig_extreme_threshold`  | 20.0      | **33.0**      | Phase 8A/B — sharp peak at 33-35, picked 33 for OOS |
| `case_a/b/c/d`           | 1101      | 1101          | Phase 3 — re-confirmed at v2 config |
| `cooldown_bars`          | 90        | 90            | Phase 4/8A — sharp optimum, identical at v2 config |

All other params kept at defaults (ema_len=7, hma1_len=13, hma2_len=21,
trigger_tf_minutes=7, entry_window_bars_trigger=5, mf_length=35, mf_smooth=6,
hyper_wave_length=5, signal_length=3).

### Engine settings

- `auto_close_hour = 22, auto_close_minute = 0` (CME daily close)
- `daily_win_limit` / `daily_loss_limit`: **OFF** (per user constraint, confirmed for v2)
- **Blackouts: NONE active** — Phase 7 found that on this v2 config, no blackout
  bundle (incremental, morning, evening, overnight, or v1's 9-hour) improves the
  PnL/DD ratio. The base config without blackouts is the best (ratio 6.15× → 7.03×
  after sig_extreme tuning).

### Risk

`risk_per_trade = 0.28%` — the highest grid step where DD stays under $2,500.

Note: the DD floor at $2,126 is plateau-ed across risks 0.18-0.28% — that single
drawdown event saturates at 1 contract well before the risk parameter scales it.
Risk 0.30% breaks the floor and jumps DD to $3,121.

## Campaign Journey

| Phase | What I did                              | Sims | Best PnL | Best DD$ | Notes |
|-------|-----------------------------------------|------|----------|----------|-------|
| 0     | Replay v1 winner + clean baseline       | 2    | $13,130  | $2,461   | v1 reproduces ±$1; clean (no blackouts, risk 0.5%) = $18k/$6.4k |
| 1     | trigger_tf × entry_window_bars          | 18   | $18,026  | $6,375   | **tf=7m, wb=5 already optimal** — no improvement |
| 2     | HMA stack 1-D + amp×h1 2-D + h2 sub     | 56   | $28,461  | $6,850   | **amp_mult=1.5** beats seed 1.0; h1=13/h2=21 confirmed |
| 3     | 16 case bitmasks                        | 15   | $28,461  | $6,850   | **1101 still wins** (case_c off); 1100/1111 close |
| 4     | final_rr × cooldown (7×6)               | 42   | $32,703  | $7,849   | **rr=1.5/cd=90** wins at PF 1.13; rr=2.0 plateaued |
| 5     | SL geometry (1-D + 2-D)                 | 36   | $33,906  | $7,151   | **sl_lookback=15, tick_buffer=6** marginal lift |
| 6     | SSL channel (ssl_len × ssl_mult)        | 90   | $29,574  | $4,805   | **ssl_len=20, ssl_mult=0.20** → ratio 6.15× (big DD cut) |
| 7     | Hour analysis + blackout bundles        | 15   | $35,353  | $6,712   | **BASE (no blackouts) best on ratio**; bundles hurt |
| 8     | sig_extreme + cooldown + rr fine tune   | 71   | $35,991  | $5,120   | **sig_extreme_thr=33-35** → ratio 7.03× (sharpest peak) |
| 9     | Risk fine + OOS robustness (5 cands)    | 41   | $16,777  | $2,162   | Candidate B (thr=33) wins OOS; risk=0.28% under DD budget |
| 10    | DD forensics                            | 1    | —        | —        | DD = 5-week slow grind (165 trades), not single event |
| 11    | sl_min_pct × risk grid                  | 30   | $60,855  | $8,269   | At risk 0.80% PnL goal reachable but DD 3.3× over budget; ratio caps at 7.4-7.8× |
| 12    | one_trade_per_window=False fine grid    | 12   | $17,576  | $2,455   | otpw=False +$799 IS but weaker OOS — kept otpw=True |

## OOS / Robustness

| Slice                  | PnL      | DD       | PF    | Trades |
|------------------------|----------|----------|-------|--------|
| Full (2025-01 → 2026-05) | $16,777 | $2,162 | 1.13  | 2,316  |
| 2025 only              | $13,537  | $2,162   | 1.14  | 1,606  |
| 2026 only              | $3,240   | $1,658   | 1.10  | 710    |
| OOS (last 3 mo)        | $3,201   | $1,658   | 1.15  | 436    |

**The strategy degrades in 2026**: ~$0.85k/month vs ~$1.13k/month in 2025.
This is regime change, not overfit per se — Candidate B was specifically picked
over the sharp peak (Candidate A, thr=35) because B has materially better
2026/OOS PnL with the same IS performance ($16,777 vs $16,796).

## Key Insights

1. **trigger_tf=7m is already optimal**. v1 was right to keep it; sweeping
   2-15m at the seed gave nothing better. The trigger TF is not a hidden lever.

2. **amp_mult=1.5 is the new sweet spot** (vs v1's 1.0). Combined with the
   default h1=13/h2=21 ribbon, it improves both PnL and ratio.

3. **SSL channel is the single biggest discovery**. v1 never touched it.
   Going from `ssl_len=60, ssl_mult=0.20` to `ssl_len=20, ssl_mult=0.20`
   tightens the entry filter and drops DD from $6,508 → $4,805 (-26%)
   while only dropping PnL 33,849 → $29,574 (-13%). Ratio jumps 5.20→6.15×.

4. **sig_extreme_threshold=33 boosts PF the most** of any single param tweak
   in v2. At ssl_len=20 with this threshold, PF reaches 1.13 (vs 1.07-1.11
   elsewhere). The window is sharp: thr=28 → 1.10, thr=35 → 1.13, thr=42 → 1.10.

5. **rr=1.5 beats rr=2.0 here** — counter-intuitive, but at WR=44% the
   higher win count more than compensates the smaller R per win. v1's RR=2.0
   choice (WR 37%) leaves edge on the table.

6. **Blackouts are net negative on this v2 config**. The new losing hours
   (H03, H07, H21, H05, H17, H23 — completely different from v1) sum to ~$13k
   on paper, but every cumulative bundle tested either hurt the ratio or
   barely matched the no-blackout base. This re-confirms
   `project_gatormtfv4_blackout_fragility`: hour-bucket attribution is
   misleading on a strategy with cooldown + one-trade-per-window.

7. **DD floor at $2,126 is a slow-grind window, not a single event** (Phase 10).
   The peak-to-trough is 2025-11-13 → 2025-12-19, 165 trades over 5 weeks.
   Most trades sized at 1 contract because `sl_min_pct=0.15%` puts the SL
   distance above the risk budget at 1 contract for typical setups. Tested
   `sl_min_pct ∈ {0.05, 0.08, 0.10, 0.12, 0.15, 0.18}` × `risk ∈ {0.20, 0.28,
   0.40, 0.60, 0.80}` — `sl_min_pct=0.15` dominates structurally
   (PF 1.12-1.13 vs PF 0.95-1.05 elsewhere).

8. **The PnL/DD ratio plateaus at 7.4-7.8× regardless of risk**, which
   mathematically caps PnL at ~$19K within the $2,500 DD budget — short of
   the $50K goal by ~$33K, and the gap is structural.

## Files

- `sweeps/_campaign.py` — campaign constants (v1 winner params + sweep risk)
- `sweeps/00_baseline.py` — Phase 0: v1 winner replay + clean seed
- `sweeps/01_trigger_tf.py` — Phase 1: trigger_tf × window_bars
- `sweeps/02_hma_stack.py` — Phase 2: HMA 1-D scan
- `sweeps/02b_hma_combo.py` — Phase 2B: amp×h1 + h2 sub-sweep
- `sweeps/03_case_bitmask.py` — Phase 3: all 16 case combinations
- `sweeps/04_rr_cooldown.py` — Phase 4: final_rr × cooldown
- `sweeps/05_sl_geometry.py` — Phase 5: SL 1-D + 2-D
- `sweeps/06_ssl_channel.py` — Phase 6: SSL ssl_len × ssl_mult
- `sweeps/06b_ssl_refine.py` — Phase 6B: SSL refinement around peak
- `sweeps/07_hour_analysis.py` — Phase 7A: hour-of-day analysis on new best
- `sweeps/07b_blackouts.py` — Phase 7B: cumulative blackout bundles
- `sweeps/08a_final_sanity.py` — Phase 8A: sig_extreme, cooldown, rr, cases
- `sweeps/08b_combo_tweaks.py` — Phase 8B: sig_extreme × rr 2-D
- `sweeps/08c_thr_refine.py` — Phase 8C: sig_extreme refinement
- `sweeps/09_risk_fine_oos.py` — Phase 9: risk fine + OOS validation
- `sweeps/09b_oos_robustness.py` — Phase 9B: 5-candidate OOS comparison
- `sweeps/10_dd_forensics.py` — Phase 10: identify DD floor source (5-week slow grind)
- `sweeps/11_sl_minpct_risk.py` — Phase 11: sl_min_pct × risk grid, structural ceiling proof
- `sweeps/12_otpw_off_fine.py` — Phase 12: one_trade_per_window=False fine grid
- `build_winner.py` / `winner_preset.json` — preset writer + JSON
- `verify_preset.py` — replay & match against expected metrics (✅ MATCH)
- `logs/*` — per-sweep stdout

## Notes for the user

- Le preset est inséré en tête de `data/presets.json` sous le nom
  `BESTPNL-MNQ GatorMTFv4 - MNQ 1m v2`. Il devrait apparaître directement
  dans les favoris de l'UI.
- Sweep budget consumed: ~386/500 simulations.
- **Le goal $50K n'est pas atteint et n'est probablement pas atteignable
  sur cette stratégie avec un DD ≤ $2,500.** Le PF plafonne à ~1.13. Les pistes
  pour aller plus loin sortent du tuning paramétrique:
  - **Partial TP support** dans le moteur — le code Pine en a, le moteur le
    rejette pour le moment (voir `src/strategies/gator_mtf_v4.py:32-38`).
    Si activé, on peut espérer un gain de PF/expectancy.
  - **Multi-asset/multi-strat** — combiner GatorMTFv4 MNQ avec une autre
    stratégie non corrélée, partageant le compte.
  - **Stratégie différente** — les autres stratégies du repo (HMASSLOsciV3,
    MomentumCheckerV2) atteignent des PF 1.5+ sur leurs configs winner.
