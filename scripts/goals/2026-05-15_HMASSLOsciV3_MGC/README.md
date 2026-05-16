# Campagne — HMASSLOsciV3 / MGC

**Période** : 2025-01-06 → 2026-05-15 (~17 mois — segments G26 → J26 → M26 + historique antérieur via le contrat M26 stocké comme single-file).
**Stratégie** : `HMASSLOsciV3`
**Symbole** : MGC (Micro Gold)

## Objectifs

- Profit net total > **30 000 $**
- Max drawdown < **2 500 $**

## Contrainte spécifique

> **Les daily win/loss limits sont laissées désactivées sur toute la campagne** (instruction utilisateur — pas de sweep daily limits).

## Invariants

- `auto_close_hour = 22`, `auto_close_minute = 0` (CME close, reference Brussels)
- Tous les backtests via `scripts/goals/_shared/harness.py::run_backtest` (UI defaults via `ui_default_engine_settings("HMASSLOsciV3")`)

## Reproduction

```bash
source venv/bin/activate
python scripts/goals/2026-05-15_HMASSLOsciV3_MGC/sweeps/08_final_validation.py
python scripts/goals/2026-05-15_HMASSLOsciV3_MGC/verify_preset.py
```

Le preset gagnant est chargeable depuis l'UI (favorites) après insertion dans `data/presets.json`.
