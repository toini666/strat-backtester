# HMASSLOsciV3 — Multi-asset MNQ + MGC

**Période** : 2025-01-06 → 2026-05-15 (~17 mois)
**Stratégie** : `HMASSLOsciV3` sur MNQ et MGC simultanément (mode `multi_asset`)
**TF** : 7m
**Initial equity** : $50,000 (compte partagé)
**Max contracts** : 50 par leg
**Auto-close** : 22:00 reference Brussels (CME daily close — FIXE)

## Objectifs

- Profit net > **$100,000** sur la période
- Max drawdown combiné < **$2,500**
- Budget : 250 simulations

## Point de départ — baseline

Preset `HMA-SSL-V3 - MNQ/MGC - Best` : combine le winner MNQ v4 ($50.8k / $2.27k) et le winner MGC v2 ($44.7k / $2.38k) avec leurs blackouts respectifs.

**Replay baseline** :
- PnL combiné : $95,481 ($50,770 MNQ + $44,711 MGC)
- DD combiné : **$3,045** ❌ (dépasse $2,500 de $545)
- Ratio P/DD : 31.35

Les DDs des deux legs se chevauchent temporellement → DD combiné > somme par leg.

## Reproduction

```bash
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/verify_preset.py
```

doit afficher `✅ MATCH`.
