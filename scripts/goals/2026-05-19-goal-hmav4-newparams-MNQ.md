# Goal — Recherche de configuration optimale pour `HMASSLOsciV4` sur MNQ

Ton objectif est de trouver une configuration de **paramètres optimaux** pour la stratégie sélectionnée, qui atteint les objectifs chiffrés ci-dessous, dans le respect des contraintes du dépôt.

---

## 🎯 Variables à remplir avant de lancer

- **Stratégie** : `HMASSLOsciV4`

- **Symbole / Ticker** : `MNQ`

- **Période de backtest**: `2025-01-06T00:00` → `2026-05-15T00:00`

- **Initial equity**: `50 000 $`

- **Max contracts**: `50`

- **Timeframes prioritaires à explorer**: `7m en priorité` (TF du preset de départ). Autres TFs (`5m`, `10m`) **autorisés** si l'analyse Phase 1 indique qu'un autre TF pourrait débloquer une meilleure config — mais le TF principal de recherche reste `7m`.

- **Preset de départ** : `[WIN MNQ] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $68.8k / DD $1.6k)` dans `data/presets.json` (id `34d5eaec-d375-40bb-a779-8fec81ff2633`).
  - Baseline V3 publiée : **PnL ≈ $68 800**, **max DD ≈ $1 600**.
  - **Important** : ce preset est en `HMASSLOsciV3`. Pour cette campagne, on **migre la config vers `HMASSLOsciV4`** — les defaults V4 reproduisent V3 (cf. docstring de `HMASSLOsciV4`), donc le replay V4 doit retrouver les mêmes métriques au cent près. Phase 1 commence par valider ce sanity check.

- **Auto-close**: **22:00 reference Brussels — FIXE, NE JAMAIS MODIFIER** (clôture officielle CME)

**Objectifs chiffrés** (les deux doivent être atteints) :
- **Profit net total** : maximiser, idéalement **dépasser la baseline V3 (~$68.8k)**, sur un budget de **~500 simulations**.
- **Max drawdown** : **< 2 000 $** (strict).

Si tu ne dépasses pas la baseline V3 en PnL après une exploration sérieuse, présente la **meilleure config V4 trouvée respectant DD < $2k** + le ratio Profit/DD, et explique-toi (cf. critères de succès).

---

## 🆕 Spécificité de cette campagne — `HMASSLOsciV4` apporte de nouveaux leviers

`HMASSLOsciV4` hérite de V3 et ajoute des paramètres d'exit/entry inédits. **Tous sont autorisés et encouragés à être explorés**, surtout en combinaison avec les leviers classiques (blackouts, risk, strategy params).

### Paramètres V4 ajoutés au portage initial (date : 2026-05-16 environ)

| Paramètre | Default V4 (= V3) | Effet quand activé |
|-----------|-------------------|---------------------|
| `reject_entry_at_sl_extreme` | `False` | Refuse l'entrée si la bougie touche la lowest/highest de la fenêtre HW (équivalent V3 `signal_candle_sl_on` avec sémantique RAW). |
| `move_to_be_on_fast_hma_cross` | `False` | Sur cross HMA rapide/SSL, si trade en profit, déplace SL à BE (marque TP1). |
| `final_exit_min_rr` | `0.0` | Filtre le HW final exit : ne sort que si le RR courant ≥ seuil. Sinon sortie reportée au HW suivant. |
| `move_to_be_on_rejected_exit` | `False` | Quand un final exit est reporté (RR insuffisant ou MFI report), si trade en profit, déplace SL à BE. |
| `early_exit_fired_mode` | `"off"` | Gère le cas où la signal de sortie est déjà actif à l'entrée. `"off"` (= V3-compat) / `"hw_rr"` (= Pine V4 default) / `"canal_inverse"` / `"next_slow_cross"`. |

### Paramètres V4 ajoutés le 2026-05-19 (portage incrémentale Pine V4)

| Paramètre | Default V4 (= V3) | Effet quand activé |
|-----------|-------------------|---------------------|
| `block_entry_if_both_windows` | `False` | Bloque les deux directions quand les fenêtres long ET short sont ouvertes simultanément (canal HMA "tricotant" autour de la baseline SSL). |
| `tp_mode_fast_hma_hw` | `True` | TP standard cross HMA rapide → next HW. Désactivable pour laisser vivre le trade sans ce chemin. |
| `tp_mode_slow_hma_cross` | `False` | Sortie immédiate à la clôture sur cross HMA lente / SSL en sens opposé du trade. Indépendant de `tp_mode_fast_hma_hw`. |
| `report_tp_if_mfi_ok` | `False` | Au HW de sortie (fast-HMA + HW), si trade en perte ET nuage MFI ⑤ encore aligné, reporte au HW suivant. N'agit que si `tp_mode_fast_hma_hw=True`. |

**Tu n'es PAS obligé de tous les activer.** Tu n'es PAS obligé d'en activer un seul si la baseline V3 reste imbattable. Tu DOIS les considérer comme leviers explorables dans tes sweeps Phase 2/3 — au même titre que blackouts, risk, daily limits, strategy params.

---

## 🗂️ Organisation des fichiers (obligatoire)

```
scripts/
└─ goals/
   └─ 2026-05-19_HMASSLOsciV4_MNQ/                ← UNE campagne = UN dossier
      ├─ README.md             objectifs, période, statut, comment reproduire
      ├─ sweeps/
      │  ├─ _campaign.py       constantes locales (STRATEGY, SYMBOL, PERIOD, BASELINE_PARAMS)
      │  ├─ 01_baseline_tfs.py
      │  ├─ 02_filter_activation.py
      │  ├─ 03_strategy_params.py
      │  ├─ 04_v4_exit_params.py        ← spécifique à la campagne : sweep des leviers V4
      │  ├─ 05_risk_and_daily_limits.py
      │  ├─ 06_hour_analysis.py
      │  ├─ 07_blackout_sweep.py
      │  ├─ 08_finetune.py
      │  └─ 09_final_validation.py
      ├─ logs/                 sortie texte des sweeps (un .log par script)
      ├─ winner_preset.json    preset gagnant au format UI
      ├─ verify_preset.py      rejoue le preset, doit afficher ✅ MATCH
      └─ REPORT.md             rapport final
```

Règles strictes :

1. **Ne JAMAIS écrire un script de campagne en dehors de `scripts/goals/<slug>/`**.
2. **Mettre dans `_shared/` uniquement ce qui est ré-utilisable** entre campagnes. Sinon, helpers locaux dans `sweeps/_campaign.py`.
3. **Nom du dossier** : `2026-05-19_HMASSLOsciV4_MNQ`.
4. **Sweeps numérotés**, chaque sweep redirige sa sortie vers `logs/<nom>.log`.
5. **Noms de fichiers neutres** (sauf `04_v4_exit_params.py` qui est explicitement la nouveauté de cette campagne — c'est OK car le but est de tester ces leviers spécifiques).
6. **Avant de créer une campagne**, jette un œil à `_shared/` pour réutiliser ce qui existe.

---

## 🧱 Contraintes techniques

1. Utiliser uniquement ce dépôt (`backend/`, `src/`, `frontend/`, `scripts/`). Pas de dépendances externes.
2. **Ne pas modifier la stratégie ou le moteur** : tout passe par paramètres et engine settings.
3. Tous les backtests passent par `scripts/goals/_shared/harness.py::run_backtest` (pas de HTTP). **Important** : le harness câble depuis le 2026-05-19 les 7 champs V4 (`final_exit_min_rr`, `move_to_be_*`, `early_exit_fired_mode`, `tp_mode_fast_hma_hw`, `tp_mode_slow_hma_cross`, `report_tp_if_mfi_ok`). Si tu observes un drift entre Phase 1 sanity (V4 defaults vs V3 winner) → vérifie d'abord que ces champs sont bien transmis.
4. **Defaults backend ≠ defaults UI**. Le harness part automatiquement des UI defaults via `ui_default_engine_settings("HMASSLOsciV4")`. Ne jamais reconstruire `BacktestEngineSettings()` à la main.
5. Toutes les heures (blackouts, auto-close, sessions) sont en **reference Brussels time**. Le moteur applique automatiquement le shift DST.
6. **L'auto-close est FIXÉ à 22:00**. Jamais sweepé.
7. **Tout est explorable** :
   - **Timeframe** (priorité `7m`, autres autorisés)
   - **Risk** (`risk_per_trade`, `max_contracts`)
   - **Strategy params V3-hérités** (longueurs HMA/SSL, oscillator, MFI, filtres ①-⑧, etc.)
   - **Paramètres V4 nouveaux** (les 9 cités plus haut)
   - **Blackout windows** (activer/désactiver/ajouter)
   - **Daily limits** (mode `intra_bar` d'abord ; `after_close` si l'`intra_bar` casse l'edge)

---

## 🛠️ Méthode attendue

Procède **incrémentalement**, pas par grid search aveugle. Un sweep numéroté par étape dans `sweeps/`.

### Étape 1 — Baseline V3→V4 sanity (`01_baseline_tfs.py`)
- Charge le preset V3 baseline via `_shared/preset.py::replay_preset`.
- **Migre vers V4** : recopie tous les params V3 → params V4 (drop des params V4-absents : `hw_partial_pct`, `hw_partial_min_rr`, `block_loss_exit_before_partial`, `final_exit_mode`; translate `signal_candle_sl_on` → `reject_entry_at_sl_extreme`). Laisse les 9 nouveaux paramètres V4 à leurs defaults (= reproduit V3).
- Run `HMASSLOsciV4` avec cette config sur **TF 7m**.
- **Sanity check obligatoire** : PnL/DD V4 ≈ PnL/DD V3 baseline à 1 cent près. Si non, **stop** — la rétrocompat est cassée, débug avant tout sweep.
- Optionnel : lance la même config sur `5m` / `10m` pour valider qu'on reste sur `7m`.
- Reporte `PnL`, `max DD ($)`, `PF`, `WR`, `N`, `AW`, `AL`, ratio Profit/DD.

### Étape 2 — Activation des filtres oscillator (`02_filter_activation.py`)
Toggle un par un les filtres optionnels exposés par la stratégie (`hw_dir_on`, `hw_extreme_on`, `sig_extreme_on`, `hw_range_on`, `cloud_on`, `delta_on`, `cloud_zero_on`, `delta_ext_on`). Garde ceux qui améliorent ratio P/DD sans tuer le volume.

### Étape 3 — Paramètres core (`03_strategy_params.py`)
Sweep 1-D sur chaque hyper-paramètre V3-hérité (longueurs HMA/SSL/MFI, fenêtres, seuils, smoothing, `cooldown_bars`, `max_candle_pct`, `tick_buffer`, `max_sl_points`, `entry_window_bars`, `one_trade_per_entry_window`). Note les "non-événements" — c'est aussi un insight. **Souviens-toi** (mémoire utilisateur) : `mf_length` et `risk_per_trade` sont **non monotones** sur HMASSLOsciV3 → faire un sweep fin avant tout combo.

### Étape 4 — **Paramètres V4 (`04_v4_exit_params.py`)** — étape spécifique à cette campagne
Sweep 1-D sur chacun des 9 paramètres V4 (boolean ON/OFF, sauf `final_exit_min_rr` qui demande un sweep numérique). À considérer :
- `block_entry_if_both_windows` — booléen.
- `reject_entry_at_sl_extreme` — booléen.
- `tp_mode_fast_hma_hw` — booléen. **Si OFF**, tester en combo avec `tp_mode_slow_hma_cross=True` (sinon le trade n'a plus de TP — résultat attendu mais à mesurer).
- `tp_mode_slow_hma_cross` — booléen.
- `report_tp_if_mfi_ok` — booléen. **N'agit que si `tp_mode_fast_hma_hw=True`** (chemin HW).
- `move_to_be_on_fast_hma_cross` — booléen.
- `final_exit_min_rr` — numérique (sweep `0.0, 0.5, 1.0, 1.5, 2.0`).
- `move_to_be_on_rejected_exit` — booléen (pertinent si `final_exit_min_rr > 0` OU `report_tp_if_mfi_ok=True`).
- `early_exit_fired_mode` — catégoriel (`"off"`, `"hw_rr"`, `"canal_inverse"`, `"next_slow_cross"`).

Pour chacun, tableau A/B : config baseline V4 (= V3) vs config + ce levier ON. Verdict KEEP / REJECT / MIXED selon ΔP/DD. Garde les KEEPs pour la Phase 7/8.

### Étape 5 — Risk / Daily limits (`05_risk_and_daily_limits.py`)
- Sweep `risk_per_trade` (fin, autour de 0.48 % = baseline).
- **Daily limits — tester d'abord en mode `intra_bar`**, puis `after_close` si l'`intra_bar` casse l'edge.
- Comparer PF / P/DD avec et sans limites.

### Étape 6 — Analyse temporelle (`06_hour_analysis.py`)
Bucketise les trades par **heure d'entrée** et **jour de la semaine** (`_shared/analysis.py`). Identifie :
- Les heures structurellement perdantes → candidats à blackout.
- Les heures à PnL anormalement élevé → vérifier biais (DST, contrat unique, etc.).

### Étape 7 — Blackouts ciblés (`07_blackout_sweep.py`)
Ajoute en blackout les heures toxiques. **Considère aussi modifier les blackouts existants** du preset baseline (les 5 actifs : `08-09`, `11-12`, `12-13`, `14-15`, `22-23:59`) — peut-être qu'avec les nouveaux paramètres V4 actifs, certains blackouts deviennent inutiles. Compare avec/sans pour valider l'effet additif.

### Étape 8 — Fine-tune (`08_finetune.py`)
Combine BEST params + blackouts + daily limits + risk + paramètres V4 KEEPs pour trouver la config qui satisfait les deux objectifs : **PnL max** sous DD **< $2 000**.

### Étape 9 — Validation finale (`09_final_validation.py`)
Re-run le gagnant + 3-5 alternatives proches sur la période complète demandée. Optionnel mais recommandé : split temporel 50/50 pour s'assurer que l'edge n'est pas concentré dans une seule moitié. Si les objectifs sont atteints → livrables.

---

## 📦 Livrables obligatoires

À la fin, fournis dans cet ordre :

### 1. Preset JSON au format UI

Utiliser `scripts/goals/_shared/preset.py::build_preset` puis `write_preset` — ces helpers garantissent le bon format (riskPerTrade en %, **tous les `default_params` V4 inclus**, `engineSettings` complet, auto_close=22) et insèrent le preset dans `data/presets.json`.

Le preset doit :
- Vivre dans `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/winner_preset.json` (copie standalone).
- Apparaître dans `data/presets.json` en tête de liste (insertion automatique par `write_preset`).
- Inclure **tous les blackouts (actifs ET inactifs) explicitement** pour écraser les defaults UI au chargement.
- Avoir `auto_close_hour = 22`, `auto_close_minute = 0`.
- `strategyName = "HMASSLOsciV4"`.
- **Tous les 9 paramètres V4 listés explicitement** (même ceux laissés à default), pour traçabilité.
- Nom suggéré : `[WIN MNQ V4] HMASSLOsciV4 — MNQ 7m — V4 (PnL $X / DD $X)`.

### 2. Script de vérification (`verify_preset.py`)

Pattern standard :

```python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.goals._shared.preset import verify_preset

EXPECTED = {"net_pnl": <PnL final>, "max_dd_$": <DD final>, "trades": <N>,
            "win_rate": <WR>, "profit_factor": <PF>}

if __name__ == "__main__":
    ok = verify_preset(Path(__file__).resolve().parent / "winner_preset.json", EXPECTED)
    sys.exit(0 if ok else 1)
```

`python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/verify_preset.py` doit afficher `✅ MATCH`. Sinon la campagne n'est pas terminée.

### 3. Rapport markdown (`REPORT.md`)

- **Résultat** : tableau objectifs vs atteints (PnL, DD, PF, WR, N, ratio Profit/DD) ; comparaison explicite à la baseline V3 (PnL $68.8k / DD $1.6k).
- **Configuration gagnante** : TF, params V3-hérités (overrides explicités), **valeurs finales des 9 paramètres V4** (lesquels sont restés à default, lesquels ont été activés), risk, blackouts, daily limits, auto-close (=22, rappelé).
- **Top 3-5 alternatives** avec leurs compromis (notamment celles qui s'approchent de DD=$2k mais avec PnL différent).
- **Insights** :
  - **Hiérarchie des leviers** : du plus impactant au plus marginal, en particulier l'apport relatif des nouveaux paramètres V4 vs les leviers classiques.
  - **Quels paramètres V4 ont KEEP, REJECT, ou MIXED ?** Tableau récapitulatif.
  - Effets contre-intuitifs (paramètres inactifs, combos qui dégradent, interactions inattendues entre flags V4).
  - Analyse temporelle (PnL par heure / jour).
  - Relation paramètre → métrique.
- **Démarche** : résumé des 9 étapes avec liens vers les sweeps.
- **Risques & idées pour la prochaine itération** :
  - Risque d'overfit (taille échantillon, dépendance à un contrat, période unique).
  - Idées (walk-forward, Bayesian sweep, portage sur MGC, audit des paramètres "inactifs").
  - Si certains paramètres V4 sont restés MIXED, candidats à creuser dans la prochaine campagne.
- **Reproduction** : 2-3 lignes (charger le preset depuis l'UI, lancer le verify script).

### 4. Logs des sweeps

Chaque sweep redirige sa sortie vers `logs/<nom>.log`. Pattern :

```bash
python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/sweeps/01_baseline_tfs.py | tee scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/logs/01_baseline_tfs.log
```

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :
1. ✅ Phase 1 sanity confirme V4(defaults) = V3 baseline (à 1 cent près).
2. ✅ Max DD < **2 000 $** (strict).
3. ✅ Le preset JSON existe au bon format dans `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/winner_preset.json`.
4. ✅ `auto_close_hour = 22` dans le preset.
5. ✅ `strategyName = "HMASSLOsciV4"` dans le preset.
6. ✅ Le preset est inséré dans `data/presets.json` (visible dans les favoris UI).
7. ✅ `python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/verify_preset.py` affiche `✅ MATCH`.
8. ✅ Le `REPORT.md` est complet et explicite quels paramètres V4 ont été activés/rejetés.
9. ✅ Tous les fichiers de la campagne sont dans `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/`, rien à plat dans `scripts/`.

**Objectif PnL — souple** : si tu ne dépasses pas la baseline V3 ($68.8k) après ~500 simulations, présente la **meilleure config V4 trouvée respectant DD < $2k** et explique pourquoi V4 n'apporte pas de gain. C'est aussi un livrable utile (signal que les nouveaux paramètres ne sont pas pertinents sur ce preset MNQ → pistes pour MGC, multi-asset, ou autres TFs en itération suivante).

**Ne jamais inventer une config qui passe juste par chance** : si une config affiche PnL > baseline mais DD aux limites, marquer ce risque, proposer au moins une alternative plus conservatrice dans le top 3-5.

---

## 🧠 Bonnes pratiques

- **Préfère le ratio Profit/DD** comme métrique de tri primaire. Réduire `risk_per_trade` scale linéairement PnL et DD : seul leur ratio compte structurellement.
- **Ne fais pas confiance aux defaults backend** pour produire un résultat reproductible dans l'UI. Le harness `_shared/harness.py` part automatiquement des UI defaults — ne JAMAIS le contourner.
- **Sweep 1-D avant tout combo**. Un grid 4-D à 5 valeurs par dim = 625 runs ; un sweep 1-D = 4×5 = 20 runs et donne 90% de l'info.
- **Les nouveaux paramètres V4 peuvent interagir** : un combo `tp_mode_fast_hma_hw=False + tp_mode_slow_hma_cross=True` change radicalement la sortie. Tester d'abord en singletons, ensuite en paires sur les KEEPs, ensuite combo complet.
- **Cache les bars** : `_shared/harness.py` le fait déjà via dict mémoire.
- **Bucketise les trades** avant de proposer des blackouts. Les blackouts arbitraires sont la première source d'overfit.
- **Documente les "non-événements"** : un paramètre V4 sans effet observable est un insight (potentiel bug, simplification à proposer).
- **Garde les logs des sweeps** dans `logs/`.
- **Souviens-toi des non-monotonies connues** (mémoire utilisateur) : `mf_length` et `risk_per_trade` sont non-monotones sur HMASSLOsciV3 → balayer fin avant tout combo. Idem pour les paramètres V4 numériques (notamment `final_exit_min_rr`).

---

## ⚙️ Référence rapide — où aller chercher quoi

| Information | Fichier |
|-------------|---------|
| Stratégies disponibles + warmup | `backend/api.py` (`STRATEGIES`, `STRATEGY_WARMUP_BARS`) |
| Defaults backend du moteur | `backend/api.py` (`BacktestEngineSettings`) |
| **Defaults UI du moteur** | `frontend/src/api.ts` (`DEFAULT_BACKTEST_ENGINE_SETTINGS`) |
| **Overrides UI par stratégie** | `frontend/src/App.tsx` (`STRATEGY_ENGINE_OVERRIDES`) |
| Miroir Python des UI defaults | `scripts/goals/_shared/engine_settings.py` |
| Harness backtest réutilisable | `scripts/goals/_shared/harness.py` (V4 fields câblés depuis 2026-05-19) |
| Build / write / verify preset | `scripts/goals/_shared/preset.py` |
| Analyse hour/dow des trades | `scripts/goals/_shared/analysis.py` |
| `default_params` HMASSLOsciV4 + docstring détaillée des paramètres | `src/strategies/hma_ssl_osci_v4.py` |
| Logique des exits V4 dans le simulateur | `src/engine/simulator.py` (bloc `is_v4_exit_mode`, autour des lignes 1330-1440) |
| PineScript source de vérité | `Pinescripts/HMA-SSL-Osci-v4.txt` |
| Specs contrats MNQ | `backend/api.py` (`CONTRACT_SPECS`, `FEES_MAP`) |
| Preset baseline V3 | `data/presets.json` id `34d5eaec-d375-40bb-a779-8fec81ff2633` |
| Exemple complet de campagne récente | `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/` |
