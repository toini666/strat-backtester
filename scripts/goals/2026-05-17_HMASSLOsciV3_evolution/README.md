# Campagne — Évolution empirique de HMASSLOsciV3

**Date** : 2026-05-17
**Ordre de mission** : `scripts/goals/2026-05-17-strategy-evolution-hmav3-1.md`
**Stratégie source** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Stratégie Lab** : `HMASSLOsciV3Labv1` (`src/strategies/hma_ssl_osci_v3_lab_v1.py`)

## Baselines de référence

| Asset | Preset path | PnL | DD | Trades | P/DD |
|-------|-------------|----:|---:|-------:|-----:|
| MNQ v5 | `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json` | $68,765 | $1,579 | 1,241 | 43.55 |
| MGC v3 | `scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/winner_preset.json` | $44,692 | $1,944 | 865 | 22.99 |

Période commune : `2025-01-06 → 2026-05-15` (~17 mois), 7m, initial equity = $50k.

## Hypothèses (cf. `HYPOTHESES.md` pour les verdicts)

| ID | Pilier | Angle | Hypothèse | Param Lab |
|----|--------|-------|-----------|-----------|
| H-A1 | A — entry | W+L | Skip entry on first N bars after slow-cross setup | `lab_entry_min_bars` |
| H-A3 | A — entry | L   | Refuse trades with SL distance < N points (toxic tight SL) | `lab_min_sl_points` |
| H-A4 | A — entry | L   | Refuse trades on toxic hours (extra blackout via strategy filter) | `lab_entry_blocked_hours` |
| H-B1 | B — SL avoidance | L | Refuse trades where 2-bar cumulative body > X% (overheated entry) | `lab_max_2bar_body_pct` |
| H-B2 | B — SL avoidance | L | Defensive close N bars after entry if no favorable HW cross | `lab_no_hw_flip_kill_bars` |
| H-C1 | C — TP optim | W   | Disable Canal Exit after hour X (let auto-close 22:00 take profit) | `lab_disable_canal_exit_from_hour` |

Cible quota : 1-3 par pilier (A,B,C), total 3-9, ≥1 issue des losers (Angle L ou W+L).
Actuel : 3 A, 2 B, 1 C = 6 hypothèses, 4 issues des losers. ✅ Couvre les 3 piliers.

## Structure

```
2026-05-17_HMASSLOsciV3_evolution/
├─ README.md                          ← ce fichier
├─ phase1_observation/
│  ├─ run_analysis.py                 ← réplay + tableaux winners vs losers
│  ├─ outputs/
│  │  ├─ trades_MNQ_v5.csv
│  │  ├─ trades_MGC_v3.csv
│  │  ├─ trades_ALL.csv
│  │  └─ summary.json
│  └─ OBSERVATIONS.md                 ← hypothèses brutes + signaux observés
├─ phase2_hypotheses/
│  ├─ _shared.py                      ← BASELINES, BASELINE_METRICS, helpers
│  ├─ 00_sanity_lab_equals_v3.py      ← sanity OBLIGATOIRE
│  ├─ 01_lab_entry_min_bars.py
│  ├─ 02_lab_min_sl_points.py
│  ├─ 03_lab_entry_blocked_hours.py
│  ├─ 04_lab_max_2bar_body_pct.py
│  ├─ 05_lab_no_hw_flip_kill_bars.py
│  ├─ 06_lab_disable_canal_exit_from_hour.py
│  └─ logs/
├─ phase3_combinations/
│  ├─ 01_pairs.py
│  ├─ 02_winner_combo.py
│  └─ logs/
├─ winner_v4_MNQ.json                 ← si combo bat baseline
├─ winner_v4_MGC.json                 ← si combo bat baseline
├─ verify_winner_v4.py
├─ HYPOTHESES.md
└─ REPORT.md
```

## Reproduction

```bash
# Sanity test (DOIT être ✅ MATCH avant tout sweep)
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase2_hypotheses/00_sanity_lab_equals_v3.py

# Phase 1 — observation
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase1_observation/run_analysis.py

# Phase 2 — chaque hypothèse
for f in scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase2_hypotheses/0[1-6]*.py; do
  python "$f"
done

# Phase 3 — combos
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase3_combinations/01_pairs.py
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase3_combinations/02_winner_combo.py

# Verify winners
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/verify_winner_v4.py
```

## Notes mission

- Le path mission `2026-05-16_HMASSLOsciV3_MGC_v3` est erroné — la baseline existe
  sous `2026-05-17_HMASSLOsciV3_MGC_v3`. Cette campagne utilise ce path réel.
- Auto-close 22:00 reference Brussels = invariant. Jamais sweepé.
- Pilier B contrainte moteur : pas d'accès runtime au MAE/MFE. Toute hypothèse
  B est soit (a) un filtre ex-ante au bar d'entrée, soit (b) un exit
  pré-calculé via `partial_close_long/short`.
