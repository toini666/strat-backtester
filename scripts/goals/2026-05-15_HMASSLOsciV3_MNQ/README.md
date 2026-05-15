# Campaign: HMASSLOsciV3 / MNQ — 2026-05-15

**Objectifs**: PnL > $30 000 — Max DD < $2 500
**Période**: 2026-01-06 → 2026-05-13 (≈ 4.5 mois, contrats H26 puis M26)
**Statut**: ✅ Atteint — PnL=$33,699 / DD=$2,319 (PF 1.78)

## Structure

- `sweeps/` — un script numéroté par étape (baseline → filtres → osc → risk → blackouts → fine-tune → validation)
- `logs/` — outputs des sweeps
- `winner_preset.json` — config finale au format UI
- `verify_preset.py` — rejoue le preset et compare au gagnant attendu (`✅ MATCH` ou `❌ MISMATCH`)
- `REPORT.md` — rapport complet (voir aussi `REPORT_HMA_SSL_OSCI_V3_MNQ.md` à la racine pour la version historique)

## Reproduire

Depuis la racine du dépôt:

```bash
source venv/bin/activate
python scripts/goals/2026-05-15_HMASSLOsciV3_MNQ/verify_preset.py
```

Sortie attendue:

```
PRESET REPLAY: PnL=$33,699 | DD=$ 2,319 | N= 368 | WR= 45.9% | PF=1.78 …
Expected:      PnL=$33,699 DD=$2,319 N=368 WR=45.9% PF=1.78
✅ MATCH
```

Le preset est aussi inséré dans `data/presets.json` — disponible directement dans les favoris UI.

## Lancer un sweep

```bash
python scripts/goals/2026-05-15_HMASSLOsciV3_MNQ/sweeps/01_baseline_tfs.py | tee scripts/goals/2026-05-15_HMASSLOsciV3_MNQ/logs/01_baseline_tfs.log
```
