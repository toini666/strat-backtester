# V5 — HMASSLOsciV3 / MNQ — 2026-05-17

**Mission**: repartir du preset V4 (PnL $50.8k / DD $2.27k) et trouver, en 200 simulations max,
une config qui maximise le PnL tout en réduisant le **MaxDD sous $2,000**.

**Période**: 2025-01-06 → 2026-05-15 (~17 mois)
**Stratégie**: `HMASSLOsciV3` sur MNQ 7m
**Initial equity**: $50,000 · **Max contracts**: 50

## Résultat — ✅✅ objectifs largement dépassés

| Objectif | Cible | Atteint | Écart |
|----------|-------|---------|-------|
| Profit net | > $50,770 (V4) | **$68,765** | **+$17,995 (+35.4%)** |
| Max drawdown | < $2,000 | **$1,579** | margin **$421** (-21%) |

| Métrique | V4 (baseline) | V5 (winner) | Δ |
|----------|---------------|-------------|---|
| Net PnL | $50,770 | **$68,765** | +$17,995 |
| Max DD $ | $2,268 | **$1,579** | -$689 |
| Profit factor | 1.58 | **1.70** | +0.12 |
| Win rate | 46.1% | **48.3%** | +2.2 pts |
| Trades | 1,389 | 1,241 | -148 |
| Avg win / Avg loss | +$217 / -$118 | +$278 / -$152 | scaled |
| **Profit/DD ratio** | 22.39 | **43.55** | **×1.95** |

## Config gagnante

- Blackouts ajoutés vs V4: **H=08-09 et H=12-13** (en plus de H=11-12 et H=14-15)
- `mf_length`: 25 → **31** (sweep 06 — non-monotone, sweet spot)
- `mf_smooth`: 6 → **7** (sweep 07 — booster compound)
- `risk_per_trade`: 0.0036 → **0.0048** (sweep 09 — DD est non-monotone en r à cause des floor de contrats)

## Reproduction

```bash
python scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/verify_preset.py
```

Doit afficher `✅ MATCH`. Le preset est aussi inséré dans `data/presets.json` (en tête).

## Démarche

200 sims budget. Utilisées: ~188.

| Sweep | Fichier | Résultat clé |
|-------|---------|--------------|
| 01 | `01_baseline_tfs.py` | V4 replay confirmé. Toxic hours H=08, H=12, H=04, H=06 |
| 02 | `02_daily_limits_and_floor.py` | Daily limits non-event (PnL/DD scale ensemble). Floor case r=0.0028 = $41.9k/$1.88k |
| 03 | `03_blackout_expansion.py` | **+H=08+12** → $50,089/$1,962 (ratio 25.53), passe DD<$2k |
| 04 | `04_sl_filters.py` | Tous les filtres SL dégradent — défauts V4 lockés |
| 05 | `05_risk_and_strategy_combos.py` | **mf_length non-monotone** — mf=20 et mf=30 battent V4 défaut (mf=25) |
| 06 | `06_mf_finetune_and_combos.py` | **BASE_B mf=30 r=0.004 = $55,766/$1,660** (margin $340) |
| 07 | `07_micro_finetune.py` | mf=31 et ms=7 sont des boosters 1-D — combo à tester |
| 08 | `08_final_compound.py` | **mf=31 × ms=7 r=0.0042 = $61,102/$1,457** ratio 41.93 |
| 09 | `09_risk_push.py` | **r=0.0048 = $68,765/$1,579** ratio 43.55 — winner |
| 10 | `10_build_preset.py` | Preset écrit + replay match |

Voir `REPORT.md` pour l'analyse détaillée.
