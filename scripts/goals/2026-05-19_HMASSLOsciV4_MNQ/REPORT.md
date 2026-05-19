# Campaign Report — `HMASSLOsciV4` on MNQ (7m)

**Period**: 2025-01-06 → 2026-05-15
**Strategy**: `HMASSLOsciV4` (V3-migrated baseline + minor relaxations + new 06–08 blackout)
**Goal**: maximise PnL with **max DD < $2,000 (strict)** — budget ~500 sims.

---

## 1. Result

| Metric           | Winner (canonical replay) | V3 baseline (re-measured) | Δ vs V3        |
|------------------|---------------------------|---------------------------|----------------|
| **Net PnL**      | **$75,236**               | $66,679                   | **+$8,557 (+12.8%)** |
| **Max DD ($)**   | **$1,911**                | $1,617                    | +$294 (+18.2%) |
| **Trades**       | 1,175                     | 1,241                     | −66            |
| **Win rate**     | 49.4%                     | 47.9%                     | +1.5 pp        |
| **Profit factor**| 1.82                      | 1.67                      | +0.15          |
| **P/DD ratio**   | 39.4                      | 41.2                      | −1.8           |

✅ Strict DD budget respected ($1,911 < $2,000).
✅ Beats V3 baseline PnL by **+12.8%** while keeping DD well under cap.

> **Note** — the V3 baseline reference in the mission file is "$68.8k / $1.6k". That figure pre-dates the addition of the $0.50/contract Topstep commission (commit 159731e). Re-measured with the current engine, V3 yields $66,679 / $1,617. Phase 1 sanity confirmed V4 with V3-migrated params + neutral V4 defaults reproduces this exactly (drift $0.28).

> **Float-precision note** — the direct optimisation call returns $75,289 / 1,173 trades. After roundtripping the preset through JSON (riskPerTrade is stored as percent), `0.00495 → 0.495 → 0.004949999…` drifts at the ULP level. This shifts the position size on a single boundary trade, which then propagates through the daily-loss limit to admit/exclude 2 trades on 2025-10-13. The **canonical replay number ($75,236) is what the user sees in the UI** — that is the reported winner.

---

## 2. Winning configuration

### Strategy / period
| | |
|-|-|
| `strategyName`  | `HMASSLOsciV4` |
| `symbol`        | `MNQ` |
| `interval`      | `7m` |
| `startDatetime` | `2025-01-06T00:00` |
| `endDatetime`   | `2026-05-15T00:00` |
| `initialEquity` | `$50,000` |
| `maxContracts`  | `50` |
| **`riskPerTrade`** | **`0.495 %`** |
| `auto_close_hour:minute` | **`22:00`** (FIXED — CME daily close, reference Brussels) |

### Strategy params

V3-migrated baseline with **two** filter relaxations (vs V3 winner preset):

| Param | Baseline V3 | Winner V4 | Source |
|-------|-------------|-----------|--------|
| `hw_extreme_on` | `True` | **`False`** | Phase 2/3 KEEP |
| `sig_extreme_on` | `True` | **`False`** | Phase 2/3 KEEP |
| _all other 36 keys_ | _unchanged_ | _unchanged_ | — |

### 9 V4-new levers — all at neutral defaults

| Param | Value | Verdict |
|-------|-------|---------|
| `reject_entry_at_sl_extreme` | `False` | REJECT |
| `move_to_be_on_fast_hma_cross` | `False` | REJECT (DD blowup) |
| `final_exit_min_rr` | `0.0` | REJECT (any `>0` ruins edge) |
| `move_to_be_on_rejected_exit` | `False` | MIXED (no-op when `final_exit_min_rr=0`) |
| `early_exit_fired_mode` | `"off"` | REJECT (all 3 alternatives hurt DD) |
| `block_entry_if_both_windows` | `False` | REJECT (marginally worse) |
| `tp_mode_fast_hma_hw` | `True` | REJECT to flip |
| `tp_mode_slow_hma_cross` | `False` | REJECT |
| `report_tp_if_mfi_ok` | `False` | REJECT |

→ **None of the 9 V4-new levers improved on the V3 baseline under DD<$2k.**

### Blackouts (reference Brussels)

| Window | Status | Source |
|--------|--------|--------|
| 00:00–00:05 | inactive | UI default |
| 09:00–09:05 | inactive | UI default |
| 12:00–14:00 | inactive | UI default |
| 15:30–15:35 | inactive | UI default |
| 16:30–22:00 | inactive | UI default |
| **22:00–23:59** | **active** | UI default (V4 override) |
| **08:00–09:00** | **active** | V3 baseline carry-over |
| **11:00–12:00** | **active** | V3 baseline carry-over |
| **12:00–13:00** | **active** | V3 baseline carry-over |
| **14:00–15:00** | **active** | V3 baseline carry-over |
| **06:00–08:00** | **active** | **NEW — Phase 7 winner** |

### Daily limits
| | |
|-|-|
| `daily_win_limit_enabled` | `False` |
| `daily_loss_limit_enabled` | **`True`** |
| `daily_loss_limit` | **`$700`** |
| `daily_limit_mode` | **`after_close`** |

---

## 3. Top alternatives

| Rank | Config | PnL | DD | N | PF | WR | P/DD | Notes |
|------|--------|-----|----|---|----|----|------|-------|
| **1** | **WINNER: 0.495% + L700 + 06–08 + relax both** | **$75,236** | **$1,911** | **1,175** | **1.82** | **49.4%** | 39.4 | canonical replay |
| 2 | 0.500% + L700 + 06–08 + relax both | $75,055 | $1,911 | 1,172 | 1.81 | 49.4% | 39.3 | trivially safer risk |
| 3 | 0.490% + L700 + 06–08 + relax both | $74,708 | **$1,889** | 1,175 | 1.82 | 49.4% | 39.5 | **lowest DD**, best P/DD |
| 4 | 0.500% (no daily limit) + 06–08 + relax both | $74,718 | $1,911 | 1,178 | 1.80 | 49.4% | 39.1 | simpler — no daily limit |
| 5 | 0.495% + L700 + 06–08, **V3-strict params** | $71,462 | $1,911 | 1,132 | 1.80 | 49.3% | 37.4 | without filter relaxations |

The winner sits in a flat plateau between 0.49–0.51 % risk. Pick **alt 3 (0.490%)** if a slightly tighter DD ($1,889 vs $1,911) is worth $530 in PnL.

---

## 4. Insights

### 4.1 Hierarchy of levers (most → least impactful, all PnL-positive deltas)

| Lever | ΔPnL (additive) | ΔDD | Comment |
|-------|----------------:|-----:|---------|
| **Blackout +H=06–08** | **+$2,179** | +$275 | Strongest single lever; eats the toxic 06:00–07:00 hour (avg −$49, WR 29%). Window extended to 08:00 because the natural 06:00 trade cluster doesn't cleanly end at 07:00. |
| **risk 0.48 % → 0.495 %** | **+$2,917** (cumulative) | +$19 | Inside the non-monotone risk grid where contract-floor quantisation flips favourably. Above 0.515 % DD jumps past $2k. |
| **Filter relax both** (`hw_extreme_on=False`, `sig_extreme_on=False`) | **+$3,514** (cumulative) | $0 | Two redundant extreme-cap filters. Phase 3 also showed `hw_extreme=40` / `sig_extreme=60` reproduce the same effect — both filters effectively never trigger above 20/40. |
| **Daily loss limit $700 (after_close)** | +$239 | $0 | Tiny but free improvement; saves a few bad sessions. |

### 4.2 V4-new lever verdicts (Phase 4 summary)

| Param | Verdict | Why |
|-------|---------|-----|
| `reject_entry_at_sl_extreme` | ❌ REJECT | −$12,640 PnL, +$1,321 DD. Filters out profitable entries. |
| `move_to_be_on_fast_hma_cross` | ❌ REJECT (DD) | +$2,082 PnL — but DD jumps to $3,152. Promising elsewhere, killed by the strict DD cap. |
| `final_exit_min_rr` (0.5 / 1.0 / 1.5 / 2.0) | ❌ REJECT | Any non-zero value: −$13k–$25k PnL, DD blows past $11k. The strategy depends on quick HW-cycle exits — RR-gating breaks that. |
| `move_to_be_on_rejected_exit` alone | ≈ MIXED | No-op when `final_exit_min_rr=0`. Useless. |
| `early_exit_fired_mode` (`hw_rr` / `canal_inverse` / `next_slow_cross`) | ❌ REJECT | Each adds ~$1k DD, costs $1k–$2k PnL. Edge cases that fire rarely but always hurt. |
| `block_entry_if_both_windows` | ❌ REJECT | −$765 PnL, +$39 DD. Marginally worse. |
| `tp_mode_fast_hma_hw=False + tp_mode_slow_hma_cross=True` | ❌ REJECT (DD) | −$9k PnL, DD $3,703. Slow-cross alone is too rare. |
| `tp_mode_slow_hma_cross=True` (alone, fast still on) | ❌ REJECT (DD) | DD $3,700. Premature exits. |
| `report_tp_if_mfi_ok` | ❌ REJECT | WR jumps to 52% but PnL drops $9k — too many missed exits. |

**Take-away** — the V4-new exit machinery (RR-gating, mode-switched TPs, early-fired handling) is interesting in concept but **net-harmful on this MNQ 7m baseline**. The V3 exit logic (`canal_exit_mode='v4_hw_rr'` with `final_exit_min_rr=0`) is already locally optimal under the strict DD cap. Most V4 levers add edge cases that increase tail risk faster than they add return.

### 4.3 Hour & DOW analysis (Phase 6, on V3-migrated baseline tape)

**Toxic hours** (Brussels):
| H | n | total | avg | WR | Status |
|---|---|------:|----:|---:|--------|
| 06 | 49 | −$2,382 | −$49 | 29% | ✅ now blackouted (06–08 window) |
| 04 | 53 | −$793 | −$15 | 42% | Tested blackout extension; not net positive |
| 23 | 8  | −$166 | −$21 | 50% | Noise (already blackouted via 22:00–23:59) |

**Strongest hours**:
| H | n | total | avg | WR |
|---|---|------:|----:|---:|
| 01 | 67 | **+$19,477** | +$291 | 42% |
| 22 | 11 | +$7,326 | +$666 | 36% |
| 15 | 118 | +$6,807 | +$58 | 48% |

**Day-of-week**:
| Day | n | total | avg | WR |
|-----|---|------:|----:|---:|
| Mon | 237 | −$584 | −$2 | 46% |
| Tue | 262 | **+$19,903** | +$76 | 50% |
| Wed | 244 | +$7,371 | +$30 | 48% |
| Thu | 254 | +$16,586 | +$65 | 48% |
| Fri | 243 | **+$23,360** | +$96 | 47% |
| Sun | 1 | +$43 | +$43 | 100% |

Monday is the weakest day (nearly breakeven) — not toxic enough to blackout but worth flagging for a follow-up campaign.

### 4.4 Counter-intuitive findings

- **`hma_pol_bars=0`** is best (default `3` in V4 PineScript). Phase 3 shows `pol=5` gives +$1.1k PnL but +$2.2k DD — strictly worse P/DD. The V3 winner's choice of `pol=0` is robust.
- **`ssl_mult` is inert** in this configuration. Five values [0.1, 0.15, 0.2, 0.25, 0.3] all produce identical results — likely because no entry rule depends on the SSL keltner mult under these params.
- **Risk non-monotonicity**: at 0.40 % DD = $2,420, at 0.44 % DD = $1,575, at 0.48 % DD = $1,617, at 0.52 % DD = $3,314, at 0.60 % DD = $2,008. The DD curve has multiple dips driven by integer contract sizing (`int(raw)`).

### 4.5 Non-load-bearing baseline blackouts? — no, all 4 are load-bearing
Phase 7 dropped each of the 4 baseline V3 blackouts individually. Every drop either (a) hurt PnL ≥$1.6k or (b) blew DD past $2k. Confirmed: the V3-winning blackout set transfers cleanly to V4.

---

## 5. Procedure summary (9 phases, ~210 sims)

| # | Phase | Sims | Outcome |
|--:|-------|-----:|---------|
| 1 | V3→V4 sanity (`01_baseline_tfs.py`) | 3 | ✅ V4(neutral defaults) = V3 baseline at $0.28 drift |
| 2 | Filter activation (`02_filter_activation.py`) | 9 | KEEPs: `hw_extreme_on=False`, `sig_extreme_on=False` |
| 3 | Core strategy 1-D (`03_strategy_params.py`) | 107 | V3-tuned baseline near-optimal; small refinements to extremes confirm Phase 2 |
| 4 | V4-new levers (`04_v4_exit_params.py`) | 16 | **All 9 V4-new params REJECT** under DD<$2k |
| 5 | Risk + daily limits (`05_risk_and_daily_limits.py`) | 22 | After_close L=$700 small KEEP; risk non-monotone confirmed |
| 6 | Hour/DOW analysis (`06_hour_analysis.py`) | 1 | H=06 toxic; Tue/Fri very strong |
| 7 | Blackout sweep (`07_blackout_sweep.py`) | 13 | **+H=06-08** STRONG KEEP; all baseline drops hurt |
| 8 | Combine (`08_finetune.py` + `08b_finetune_risk.py`) | 24 | Winner: 0.495 % + relax-both + 06-08 + L700 |
| 9 | Final validation (`09_final_validation.py`) | 7 | ✅ Preset reproduces; verify_preset prints `✅ MATCH` |

Total: ~202 sims (well under the 500 budget).

---

## 6. Risks & ideas for the next iteration

### Risks
- **Sample size**: ~1,175 trades across 16 months on a single MNQ contract series (M26). Edge could be regime-specific. Walk-forward or rolling-window cross-validation would harden the claim.
- **Float-precision artifact**: replay vs direct drift is $53 / 2 trades — tiny but a reminder that "boundary-of-floor" trades can flip with subpercent risk changes. Anyone tweaking `riskPerTrade` in the UI by ±0.001 % should expect ±50 in PnL noise.
- **Daily-loss limit dependency**: `after_close L=$700` only contributes +$239. Drop it for an even simpler "no daily limit" preset (Alt 4) if the user prefers to remove moving parts.
- **Period concentration**: Tue/Fri carry the vast majority of P/L. A market regime shift that weakens those two days would disproportionately hurt the strategy.

### Ideas for follow-up
1. **MGC port** — try the same V3→V4 migration + relax-both + 06–08 blackout on gold; could a different commodity behave differently with V4 levers?
2. **`move_to_be_on_fast_hma_cross` rescue** — it adds +$2k PnL at $3.1k DD on the V3 baseline. Can we pair it with a tighter `max_sl_points` or a partial-position reduction to keep DD below $2k?
3. **Risk auto-scaling** — the DD curve has 3 local minima. A small Bayesian sweep around the 0.55–0.65 % zone could find a higher PnL config under DD<$2k that the linear sweep missed.
4. **Monday filter** — Mon avg is −$2. Try blocking all Monday entries (or just Monday morning) as a tail-risk insurance, accept the −$500 expected PnL hit for a cleaner equity curve.
5. **MIXED V4 levers** — `move_to_be_on_rejected_exit` was MIXED only because the gate is `final_exit_min_rr>0`. Re-explore by setting `final_exit_min_rr=0.5` AND `move_to_be_on_rejected_exit=True` AND `max_sl_points=200`: this might neutralise the DD blowup of `min_rr=0.5` alone.

---

## 7. Reproduction

```bash
# Activate venv
source venv/bin/activate

# 1. The winner preset is already inserted into data/presets.json by Phase 9.
#    Open the UI, go to Favorites — it appears as
#    "[WIN MNQ V4] HMASSLOsciV4 — MNQ 7m — V4 (PnL $75.2k / DD $1.91k)"

# 2. Programmatic verification — must print ✅ MATCH
python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/verify_preset.py

# 3. Re-run any sweep
python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/sweeps/01_baseline_tfs.py
# … through 09_final_validation.py
```

Each sweep's full log is in `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/logs/`.
