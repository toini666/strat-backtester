# Goal — Recherche de configuration optimale pour une stratégie

Ton objectif est de trouver une configuration de **paramètres optimaux** pour la stratégie sélectionnée, qui atteint les objectifs chiffrés ci-dessous, dans le respect des contraintes du dépôt.

---

## 🎯 Variables à remplir avant de lancer

> Remplis cette section AVANT d'invoquer le prompt. Supprime les options non retenues, garde-en une par variable. Tout le reste s'adapte.

- **Stratégie** *(garder une seule ligne)* :
  - `EMABreakOsc`
  - `EMA9Scalp`
  - `UTBotAlligatorST`
  - `HMAOsci`
  - `HMASSLOsci`
  - `HMASSLOsciV2`
  - `HMASSLOsciV3`
  - `EMABreakHMASSLOsc`
  - `RobReversal`
  - `GatorHMAEpure`

- **Symbole / Ticker** *(garder un seul)* :
  - `MNQ` · `MES` · `MYM` · `MGC` · `M2K` · `MBT` · `MCL`

- **Période de backtest**: `2025-01-06T00:00` → `2026-05-13T18:39` *(= tout l'historique MNQ disponible — adapter selon le symbole)*

- **Initial equity**: `50 000 $`

- **Max contracts**: `50`

- **Timeframes prioritaires à explorer**: `3m, 5m, 7m, 10m` *(tester aussi 2m / 15m si pertinent)*

- **Preset de départ (optionnel)**: `<chemin vers un preset JSON OU nom d'un preset existant dans data/presets.json — laisser vide pour partir des default_params natifs>`

- **Auto-close**: **22:00 reference Brussels — FIXE, NE JAMAIS MODIFIER** (clôture officielle CME)

**Objectifs chiffrés** (les deux doivent être atteints) :
- Profit net total **> 30 000 $**
- Max drawdown **< 2 500 $**

---

## 🗂️ Organisation des fichiers (obligatoire — pour éviter le chaos)

Tout le travail d'une campagne vit sous `scripts/goals/`. Aucun fichier de campagne à la racine de `scripts/` ni du dépôt.

```
scripts/
└─ goals/
   ├─ _shared/                                    ← code RÉUTILISABLE entre campagnes
   │  ├─ harness.py            run_backtest, summarize, fmt_summary, bench
   │  ├─ engine_settings.py    ui_default_engine_settings / make_engine_settings
   │  ├─ preset.py             build_preset, write_preset, verify_preset
   │  └─ analysis.py           bucket_by_hour, bucket_by_dow, print tables
   └─ <YYYY-MM-DD>_<Strategy>_<Symbol>/           ← UNE campagne = UN dossier
      ├─ README.md             objectifs, période, statut, comment reproduire
      ├─ sweeps/
      │  ├─ _campaign.py       constantes locales (STRATEGY, SYMBOL, PERIOD, BEST_PARAMS)
      │  ├─ 01_baseline_tfs.py
      │  ├─ 02_filter_activation.py
      │  ├─ 03_strategy_params.py
      │  └─ …
      ├─ logs/                 sortie texte des sweeps (un .log par script)
      ├─ winner_preset.json    preset gagnant au format UI
      ├─ verify_preset.py      rejoue le preset, doit afficher ✅ MATCH
      └─ REPORT.md             rapport final
```

Règles strictes :

1. **Ne JAMAIS écrire un script de campagne en dehors de `scripts/goals/<slug>/`**. Pas de scripts à plat dans `scripts/` (ceux-ci sont réservés aux outils opérationnels : `contract_switch_*`, `update_market_data`, etc.).
2. **Mettre dans `_shared/` uniquement ce qui est ré-utilisable** entre stratégies/symboles. Si un helper est spécifique à une campagne, il reste dans le dossier de la campagne (typiquement dans `sweeps/_campaign.py`).
3. **Nom de la campagne** : `<YYYY-MM-DD>_<StrategyClass>_<Symbol>` (ex. `2026-05-15_HMASSLOsciV3_MNQ`). Si tu relances une campagne identique un autre jour, change la date.
4. **Les sweeps sont numérotés** (`01_`, `02_`, …) dans l'ordre de la méthode (cf. §🛠️). Chaque sweep redirige sa sortie vers `logs/<nom>.log`.
5. **Noms de fichiers neutres** : ne pas refléter de jargon spécifique à une stratégie (`osc`, `hma`, etc.) dans les noms d'étapes — utiliser des noms génériques (`strategy_params`, `filter_activation`, etc.). Le contenu peut bien sûr être stratégie-spécifique.
6. **Avant de créer une campagne**, jette un œil à `_shared/` pour réutiliser ce qui existe déjà.

---

## 🧱 Contraintes techniques

1. Utiliser uniquement ce dépôt (`backend/`, `src/`, `frontend/`, `scripts/`). Ne pas installer de dépendances externes.
2. Ne pas casser le code existant : pas de modifications de la stratégie ou du moteur. Travail uniquement via paramètres et engine settings.
3. Tous les backtests passent par le moteur event-driven (`src/engine/simulator.py`). Toujours via `scripts/goals/_shared/harness.py::run_backtest` (pas de HTTP).
4. **Defaults backend ≠ defaults UI**. `BacktestEngineSettings` (Python) et `DEFAULT_BACKTEST_ENGINE_SETTINGS` + `STRATEGY_ENGINE_OVERRIDES` (TS frontend) divergent. Le harness `_shared/harness.py` part **automatiquement** des UI defaults via `ui_default_engine_settings(strategy_name)` — c'est la source de vérité, ne JAMAIS reconstruire les engine settings manuellement avec `BacktestEngineSettings()` sans ces overrides. Si tu touches au frontend, mets à jour `_shared/engine_settings.py` en miroir.
5. Toutes les heures (blackouts, auto-close, sessions) sont en **reference Brussels time** (= horaire d'hiver). Le moteur applique automatiquement le shift DST — ne jamais essayer de corriger DST manuellement.
6. **L'auto-close est FIXÉ à 22:00 reference Brussels** (CME close). Ne pas le modifier, ne pas le sweeper. Si tu en as besoin pour un test diagnostique, fais-le ponctuellement et reviens à 22:00 dans toute config gagnante / preset.
7. Paramètres à explorer :
   - **Timeframe** (`3m`, `5m`, `7m`, `10m`, …)
   - **Risk** (`risk_per_trade`, `max_contracts`)
   - **Strategy params** (partir du preset fourni si présent, sinon des `default_params` natifs)
   - **Blackout windows** (activer / désactiver / ajouter)
   - **Daily limits** (mode `intra_bar` d'abord ; `after_close` si l'`intra_bar` casse l'edge)

---

## 🛠️ Méthode attendue

Procède **incrémentalement**, pas par grid search aveugle. Un sweep numéroté par étape dans `sweeps/`.

### Étape 1 — Baseline (`01_baseline_tfs.py`)
- **Si un preset de départ a été fourni** (variable `Preset de départ`), charge-le via `_shared/preset.py::replay_preset` et utilise ses params + engine_settings comme **point de départ** des sweeps. Affiche la baseline du preset comme référence.
- **Sinon**, lance la stratégie avec ses `default_params` natifs **sur chaque timeframe prioritaire**, avec les UI defaults (déjà branchés via `_shared/harness.py`).
Reporte `PnL`, `max DD ($)`, `PF`, `WR`, `N`, `AW`, `AL`. Identifie le meilleur point de départ (TF / preset) par **ratio Profit/DD**.

### Étape 2 — Activation des filtres (`02_filter_activation.py`)
Toggle un par un les filtres optionnels exposés par la stratégie (sur le meilleur TF). Garde ceux qui améliorent PF ou réduisent DD sans tuer le volume.

### Étape 3 — Paramètres core de la stratégie (`03_strategy_params.py`)
Sweep 1-D sur chaque hyper-paramètre de la stratégie (longueurs d'indicateurs, fenêtres, seuils, smoothing — quoi qu'expose la stratégie). Note les "non-événements" (paramètres sans effet) — c'est aussi un insight.

### Étape 4 — Risk / Daily limits (`04_risk_and_daily_limits.py`)
- Sweep `risk_per_trade`.
- **Daily limits — tester d'abord en mode `intra_bar`** (clôture instantanée dès que le seuil est atteint sur le PnL flottant), puis `after_close` si `intra_bar` casse l'edge.
- Comparer PF avec/sans limites.

### Étape 5 — Analyse temporelle (`05_hour_analysis.py`)
Bucketise les trades par **heure d'entrée** et **jour de la semaine** (`_shared/analysis.py`). Identifie :
- Les heures structurellement perdantes → candidats à blackout
- Les heures à PnL anormalement élevé → vérifier biais (DST, contrat unique, etc.)

### Étape 6 — Blackouts ciblés (`06_blackout_sweep.py`)
Ajoute en blackout les heures toxiques. Compare avec/sans pour valider l'effet additif.

### Étape 7 — Fine-tune (`07_finetune.py`)
Combine BEST params + blackouts + daily limits + risk pour trouver le couple qui satisfait les deux objectifs.

### Étape 8 — Validation finale (`08_final_validation.py`)
Re-run le gagnant + 3-5 alternatives proches sur la période complète demandée. Si les objectifs sont atteints, passe aux livrables.

---

## 📦 Livrables obligatoires

À la fin, fournis dans cet ordre :

### 1. Preset JSON au format UI

Utiliser `scripts/goals/_shared/preset.py::build_preset` puis `write_preset` — ces helpers garantissent le bon format (riskPerTrade en %, tous les `default_params` inclus, `engineSettings` complet, auto_close=22) et insèrent le preset dans `data/presets.json`.

Le preset doit :
- Vivre dans `scripts/goals/<slug>/winner_preset.json` (standalone copy)
- Apparaître dans `data/presets.json` en tête de liste (insertion automatique par `write_preset`)
- Inclure **tous les blackouts (actifs ET inactifs) explicitement** pour écraser les defaults UI au chargement
- Avoir `auto_close_hour = 22`, `auto_close_minute = 0`

### 2. Script de vérification (`verify_preset.py`)

Voir `scripts/goals/_shared/preset.py::verify_preset`. Le script de campagne fait juste :

```python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.goals._shared.preset import verify_preset

EXPECTED = {"net_pnl": 33_699, "max_dd_$": 2_319, "trades": 368,
            "win_rate": 45.9, "profit_factor": 1.78}

if __name__ == "__main__":
    ok = verify_preset(Path(__file__).resolve().parent / "winner_preset.json", EXPECTED)
    sys.exit(0 if ok else 1)
```

`python scripts/goals/<slug>/verify_preset.py` doit afficher `✅ MATCH`. Sinon, la campagne n'est pas terminée.

### 3. Rapport markdown (`REPORT.md` dans le dossier de campagne)

- **Résultat** : tableau objectifs vs atteints (PnL, DD, PF, WR, N, ratio Profit/DD).
- **Configuration gagnante** : TF, params (overrides explicités), risk, blackouts, daily limits, auto-close (=22, rappelé).
- **Top 3-5 alternatives** avec leurs compromis.
- **Insights** :
  - Hiérarchie des leviers (du plus impactant au plus marginal).
  - Effets contre-intuitifs (paramètres inactifs, combos qui dégradent, etc.).
  - Analyse temporelle (PnL par heure / jour).
  - Relation paramètre → métrique.
- **Démarche** : résumé des 8 étapes avec liens vers les sweeps.
- **Risques & idées pour la prochaine itération** :
  - Risque d'overfit (taille échantillon, dépendance à un contrat, période unique).
  - Idées (walk-forward, Bayesian sweep, multi-asset, audit de params "inactifs"…).
- **Reproduction** : 2-3 lignes (charger le preset depuis l'UI, lancer le verify script).

### 4. Logs des sweeps

Chaque sweep redirige sa sortie vers `logs/<nom>.log`. Pattern :

```bash
python scripts/goals/<slug>/sweeps/01_baseline_tfs.py | tee scripts/goals/<slug>/logs/01_baseline_tfs.log
```

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :
1. ✅ Profit net > objectif PnL
2. ✅ Max DD < objectif DD
3. ✅ Le preset JSON existe au bon format dans `scripts/goals/<slug>/winner_preset.json`
4. ✅ `auto_close_hour = 22` dans le preset
5. ✅ Le preset est inséré dans `data/presets.json` (visible dans les favoris UI)
6. ✅ `python scripts/goals/<slug>/verify_preset.py` affiche `✅ MATCH`
7. ✅ Le `REPORT.md` est complet
8. ✅ Tous les fichiers de la campagne sont dans `scripts/goals/<slug>/`, rien à plat dans `scripts/`

Si tu n'arrives pas à atteindre les objectifs après une exploration sérieuse, **n'invente pas une config qui passe juste par chance** : présente la meilleure config trouvée, explique pourquoi le seuil n'a pas été atteint, et propose 2-3 hypothèses concrètes (changement de stratégie, élargissement de l'historique, etc.).

---

## 🧠 Bonnes pratiques

- **Préfère le ratio Profit/DD** comme métrique de tri primaire. Réduire le risk_per_trade scale linéairement PnL et DD : seul leur ratio compte structurellement.
- **Ne fais pas confiance aux defaults backend** pour produire un résultat reproductible dans l'UI. Le harness `_shared/harness.py` part automatiquement des UI defaults — ne JAMAIS le contourner.
- **Sweep 1-D avant tout combo**. Un grid 4-D à 5 valeurs par dim = 625 runs ; un sweep 1-D = 4×5 = 20 runs et donne 90% de l'info.
- **Cache les bars** : `_shared/harness.py` le fait déjà via dict mémoire. Un sweep de 50 configs ne doit pas re-lire 17 mois de CSV à chaque fois.
- **Bucketise les trades** avant de proposer des blackouts. Les blackouts arbitraires sont la première source d'overfit.
- **Documente les "non-événements"** : un paramètre sans effet observable est un insight (potentiel bug, simplification à proposer).
- **Garde les logs des sweeps** dans `logs/` — utile pour comparer entre itérations et auditer plus tard.

---

## ⚙️ Référence rapide — où aller chercher quoi

| Information | Fichier |
|-------------|---------|
| Stratégies disponibles + warmup | `backend/api.py` (`STRATEGIES`, `STRATEGY_WARMUP_BARS`) |
| Defaults backend du moteur | `backend/api.py` (`BacktestEngineSettings`) |
| **Defaults UI du moteur** | `frontend/src/api.ts` (`DEFAULT_BACKTEST_ENGINE_SETTINGS`) |
| **Overrides UI par stratégie** | `frontend/src/App.tsx` (`STRATEGY_ENGINE_OVERRIDES`) |
| Miroir Python des UI defaults | `scripts/goals/_shared/engine_settings.py` |
| Harness backtest réutilisable | `scripts/goals/_shared/harness.py` |
| Build / write / verify preset | `scripts/goals/_shared/preset.py` |
| Analyse hour/dow des trades | `scripts/goals/_shared/analysis.py` |
| `default_params` d'une stratégie | `src/strategies/<name>.py` |
| Logique du simulateur, exit modes, position sizing | `src/engine/simulator.py` |
| Specs contrats (tick size, value, fees) | `backend/api.py` (`CONTRACT_SPECS`, `FEES_MAP`) |
| Données historiques + contrats actifs | `data/market_data/`, `src/data/market_store.py` (`SYMBOL_CONTRACTS`) |
| Format presets (exemples) | `data/presets.json` |
| Format presets (typage frontend) | `frontend/src/api.ts` (`SingleBacktestPreset`) |
| Exemple complet de campagne | `scripts/goals/2026-05-15_HMASSLOsciV3_MNQ/` |
