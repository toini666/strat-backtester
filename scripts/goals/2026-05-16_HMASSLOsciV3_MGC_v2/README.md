# Campagne HMASSLOsciV3 / MGC — v2

**Date** : 2026-05-16
**Stratégie** : `HMASSLOsciV3`
**Symbole** : MGC (micro-futures Gold)
**Période** : 2025-01-06 → 2026-05-15 (~17 mois)
**Initial equity** : 50 000 $ — `max_contracts` = 50
**Statut** : ✅ Objectifs atteints

## Objectifs

- PnL net > **30 000 $** → atteint **$44 711** (+$14 711)
- Max DD < **2 500 $** → atteint **$2 378** (-$122)

## Configuration gagnante

- TF = 7 m
- `risk_per_trade = 0.47 %`
- Overrides stratégie : `hma2_len=34`, `hma1_len=9`, `hw_range_on=True`,
  `block_loss_exit_before_partial=True`, `max_sl_points=100`, `tick_buffer=1`
- Blackouts actifs (Brussels ref) : 03-04, 06-07, 07-08, 09-10, 11-12, 22-23:59
- `auto_close = 22:00:00` (UI default)
- Daily limits : désactivées

## Reproduction

```bash
# verify (doit afficher ✅ MATCH)
python scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/verify_preset.py

# rebuild preset depuis zéro
python scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/build_winner.py
```

Voir [`REPORT.md`](REPORT.md) pour la démarche complète, les insights, les
alternatives et les risques.

## Démarche

Cette campagne v2 part du **preset gagnant de la v1** (`2026-05-15_HMASSLOsciV3_MGC`)
mais **retire les blackouts ajoutés** (sauf 22-23:59 — UI default) avant
ré-exploration des paramètres. Les sweeps sont numérotés `01_` à `08_` dans
[`sweeps/`](sweeps/), avec un log par sweep dans [`logs/`](logs/).

Versus la v1 :
- v1 : PnL=$32 821 / DD=$3 230 / P/DD=10.16 — DD au-dessus de la cible
- v2 : PnL=$44 711 / DD=$2 378 / P/DD=18.80 — **les deux objectifs atteints**
