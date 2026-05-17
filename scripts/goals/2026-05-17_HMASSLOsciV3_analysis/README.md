# HMASSLOsciV3 — analyse post-mortem (2026-05-17)

Analyse instrumentée des 3 winners HMASSLOsciV3 (`MNQ_v4`, `MGC_v2`, `MNQ_MGC`) pour identifier des pistes d'évolution (entrées, sorties, SL).

## Contenu

* **`run_analysis.py`** — script qui replay les 3 presets, capture chaque trade et joint l'état des indicateurs à l'entrée/sortie. PnL match exact des rapports publiés.
* **`outputs/trades_{MNQ_v4,MGC_v2,MNQ_MGC,ALL}.csv`** — données trade-par-trade (38 colonnes : OHLC, MAE/MFE en R, canal slope/width, HW timing, side, status…).
* **`outputs/summary.json`** — tous les aggregates (status, hour, slope, width, SL distance, HW speed, bars-since-setup, side split, etc.).
* **`outputs/run.log`** — sortie du dernier run.
* **`REPORT.md`** — **9 insights actionnables + 4 hypothèses prioritaires pour une `HMASSLOsciV4`**. Lire ça en priorité.

## Reproduction

```bash
source venv/bin/activate
python scripts/goals/2026-05-17_HMASSLOsciV3_analysis/run_analysis.py
```

Lit les presets in-place dans `scripts/goals/2026-05-16_HMASSLOsciV3_*/winner_preset.json`. Aucune modification du repo, lecture seule.

## Garde-fous

* `src/strategies/hma_ssl_osci_v3.py` n'a PAS été modifié. Les propositions sont des hypothèses pour une **nouvelle classe** future (`HMASSLOsciV4`) qui n'existe pas encore.
* Toutes les pistes restent à valider en walk-forward et out-of-sample.
