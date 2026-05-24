# MomentumCheckerV2 MGC 7m — v4 WR Campaign (2026-05-24)

**Goal**: WR ≥ 50 %, DD ≤ $2,500, max PnL.
**Seed**: `BEST3TOP MGC MomentumCheckerV2 v3 WINNER - MGC 7m`.
**Period**: Full MGC 7m history 2025-01-02 → 2026-05-22.

## Winner shipped

**`BESTWR-MGC MomentumCheckerV2 - MGC 7m v4`** (visible in UI favorites).

| Metric        | Value     |
|---------------|-----------|
| PnL           | $28,162   |
| max_dd_$      | $2,438 ($62 headroom under $2,500 budget) |
| Win rate      | 51.0 %    (95% CI ≈ ±3 pp) |
| Profit factor | 1.29      |
| Trades        | 1,056     |

vs seed: −$33.3k PnL, +$256 DD, **+11.4 pp WR**.

## What changed vs seed (the 4 levers + 2 BOs + risk)

| | Seed | WINNER |
|-|-|-|
| `rr_tp`         | 3.0    | **1.25** |
| `sl_lookback`   | 15     | **14** |
| `tick_buffer`   | 2      | **0** |
| `ut_on`         | True   | **False** |
| `riskPerTrade`  | 0.53 % | **0.42 %** |
| BO 07:00-08:00  | —      | **active** |
| BO 12:00-12:30  | —      | **active** |

Everything else (HMA stack, Alligator, EMA, STC, oscillator filters, point weights,
the 5 seed blackouts, auto-close 22:00, daily limits OFF, max_contracts=20) unchanged.

## Layout

```
2026-05-24_MomentumCheckerV2_MGC_v4_WR/
├─ README.md           (you are here)
├─ REPORT.md           full narrative — phases, decisions, alts, caveats
├─ winner_preset.json  shipped preset (in data/presets.json too)
├─ expected_winner_metrics.json
├─ build_winner_preset.py
├─ verify_preset.py    must print ✅ MATCH
├─ sweeps/
│  ├─ _campaign.py     seed params + helpers
│  ├─ 00_baseline.py   …  17_lb14_squeeze.py
└─ logs/
   └─ 00…17_*.log
```

## Reproduce

```bash
cd /Users/awagon/Documents/dev/nebular-apollo
source venv/bin/activate
python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v4_WR/verify_preset.py
# ✅ MATCH
```

## Sim budget

~540 / 1000 used. The campaign converged at Phase 17 — additional sims would have
explored fine-grain combinations but the structural DD floor (~$2,278 at WR≥50 % on
the ut_off path) made further exploration unproductive.
