# Campaign 2026-05-16 — HMASSLOsciV3 MNQ v4

## Objectif
Maximiser le PnL avec **MaxDD < $2,500**, en partant du gagnant v3 (`cd=3, sx=40, r=0.0032`).

- PnL cible : > $35,000 (max possible en 250 sims)
- MaxDD cible : < $2,500 (effectif < $2,400 par sécurité)
- Période : 2025-01-06 → 2026-05-15 (~17 mois)
- Symbole / TF : MNQ / 7m
- Initial equity : $50,000
- Auto-close : **22:00 reference Brussels (FIXÉ)**

## Différence avec v3
La campagne v3 interdisait les blackouts horaires. Ici on les ré-active comme levier
principal (signalé dans le REPORT v3 §8 comme la prochaine itération naturelle).

## Statut
En cours — voir `sweeps/` et `logs/`.

## Reproduction
```bash
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/verify_preset.py
```
