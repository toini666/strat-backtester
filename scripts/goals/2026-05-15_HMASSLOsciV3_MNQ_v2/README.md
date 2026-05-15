# Campagne 2026-05-15 — HMASSLOsciV3 / MNQ (full-history v2)

Objectif: trouver une configuration de `HMASSLOsciV3` sur MNQ qui atteint:
- Profit net **> 30 000 $**
- Max drawdown **< 2 500 $**

Sur la période **2025-01-06 → 2026-05-13** (≈ 17 mois, contrats H25 → M26).

## Différences avec la campagne précédente
La campagne `2026-05-15_HMASSLOsciV3_MNQ/` portait sur 4,5 mois et utilisait `auto_close=21` (legacy backend default). Cette itération:
- Période complète ~17 mois → vrai stress-test out-of-sample.
- `auto_close=22` strictement (UI default, CME close en reference Brussels time).
- Daily limits testés **d'abord en mode `intra_bar`**, fallback `after_close`.

## Structure
```
sweeps/      01..08_*.py + _campaign.py
logs/        un .log par sweep
winner_preset.json
verify_preset.py
REPORT.md
```

## Reproduire
```bash
source venv/bin/activate
python scripts/goals/2026-05-15_HMASSLOsciV3_MNQ_v2/verify_preset.py
# → ✅ MATCH
```

## Méthode (8 étapes)
1. `01_baseline_tfs.py` — baseline params UI defaults, tous les TF
2. `02_filter_activation.py` — toggle des filtres optionnels
3. `03_strategy_params.py` — sweep 1-D des hyperparamètres
4. `04_risk_and_daily_limits.py` — risk + daily limits (intra_bar prio)
5. `05_hour_analysis.py` — bucket trades hour-of-day + DOW
6. `06_blackout_sweep.py` — activation blackouts ciblés
7. `07_finetune.py` — combo des meilleurs leviers
8. `08_final_validation.py` — winner + alternatives sur la période complète
