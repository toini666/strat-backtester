# 2026-05-17 — HMASSLOsciV3 MNQ+MGC v2

**Objectif** : passer le DD combiné multi-asset MNQ+MGC **sous $2 000** tout en gardant PnL > **$100 000**.

**Période** : 2025-01-06 → 2026-05-15 · TF 7m · initial equity $50k · max_contracts 50

**Point de départ** : preset favori `Multi-Asset — MNQ/MGC - NEW` (params MNQ avec mf=31/smooth=7, params MGC avec mf=29/smooth=5/cloud_on, risk 0.48 / 0.52 %).

**Auto-close** : 22:00 reference Brussels — FIXE.

## Méthode

1. `01_baseline.py` — replay baseline du preset NEW
2. `02_risk_split.py` — sweep 1-D risk MNQ et MGC
3. `03_hour_analysis.py` — bucket trades hour & DOW
4. `04_blackout_singles.py` — toggle blackout 1-h sur chaque leg
5. `05_daily_limits.py` — intra_bar puis after_close
6. `06_combo_blackouts.py` — combos blackouts validés
7. `07_finetune.py` — risk × blackouts fin
8. `08_final_validation.py` — winner + alternatives

## Reproduction

```bash
python scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_MGC_v2/verify_preset.py
```
