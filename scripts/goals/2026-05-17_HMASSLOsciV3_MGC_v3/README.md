# Campagne V3 — HMASSLOsciV3 / MGC — DD < $2,000

## Objectif

Repartir du winner V2 (PnL $44,711 / DD $2,378) et **réduire le DD sous $2,000** tout
en maximisant le PnL, en 200 simulations max.

## Statut : ✅ ✅

| Objectif | Cible | Atteint |
|----------|-------|---------|
| PnL | maximiser sous contrainte DD | **$44,692** (-$19 vs V2, négligeable) |
| Max DD | < $2,000 | **$1,944** (margin $56) |

**Profit/DD = 22.99** (vs V2 = 18.80, +22 %).

## Configuration

Voir `winner_preset.json`. Reprend V2 + active `cloud_on=True` + tune `mf_length=29`
et `mf_smooth=5` + push `risk_per_trade` de 0.47 % à 0.52 %.

## Reproduction

```bash
# Vérifier le preset
python scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/verify_preset.py
# ✅ MATCH

# Re-builder depuis zéro
python scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/sweeps/08_build_preset.py
```

Le preset est inséré en tête de `data/presets.json` et visible dans la page Favoris UI.

## Démarche

| Sweep | Sims | Highlight |
|-------|------|-----------|
| 01 — Baseline | 1 | V2 winner replay ✅ |
| 02 — mf + cloud sanity | 16 | **`cloud_on=True` mf=30 ms=5 → DD $1,845** (no-op confirmé sur cloud=F) |
| 03 — Cloud fine grid | 20 | mf=29 ms=5 lift à DD $1,813 |
| 04 — Strategy params 1D | 55 | `entry_window_bars=3` DD-reducer (-$248) |
| 05 — Combos + blackouts | 22 | Combos non-additifs ; BO 21-22 marginal |
| 06 — Risk fine sweep | 48 | **r=0.0052 sweet spot** → PnL $44.7k / DD $1.94k |
| 07 — Push beyond | 16 | A+BO21 redondant ; daily limits dégradent ; r=0.0053 fait basculer DD |
| 07b — Probe combo + risk | 8 | ew3+hwe18 ne compound pas avec risk push |
| 07c — Probe strict-beat V2 | 11 | barrière DD $2,000 dure — A r=0.0052 = optimum |
| 08 — Build preset | 2 | Preset + verify ✅ MATCH |
| **Total** | **199** | |

Réserve ~1 sim non utilisée sur 200.
