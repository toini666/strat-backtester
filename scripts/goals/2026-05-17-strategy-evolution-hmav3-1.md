# Goal — Évolution empirique d'une stratégie (analyse + hypothèses TESTÉES)

Ton objectif est de **proposer ET de valider expérimentalement** entre 5 et 10 améliorations concrètes sur une stratégie existante, en partant de ses presets gagnants actuels. Chaque insight doit être adossé à un **A/B test réel** sur les backtests, pas à une simple observation.

Tu travailles en **trois phases obligatoires** :

1. **Observer** — analyser **autant les trades gagnants que les trades perdants** des presets de référence, sur **les 3 piliers d'un setup** (entry / SL avoidance / TP) pour générer des hypothèses.
2. **Tester** — dupliquer la stratégie en `<Name>Lab` (nouvelle classe, defaults = comportement original) et **implémenter chaque hypothèse comme un paramètre configurable** dont le default reproduit le comportement V3. Chaque hypothèse passe par un A/B sweep réel (OFF=baseline, ON=hypothèse active).
3. **Synthétiser** — pour chaque hypothèse : verdict KEEP / REJECT / MIXED + chiffres, et proposer une vraie config "winner V<N+1>".

**Une hypothèse non testée ne compte pas.** Le livrable se mesure au nombre d'hypothèses adossées à un A/B sweep reproductible.

---

## 🧭 Cadre d'analyse — les 3 piliers × 2 angles

Toute hypothèse doit pouvoir être rattachée à **un des trois piliers d'un setup** :

| Pilier | Question | Type d'amélioration | Source d'inspiration |
|--------|----------|---------------------|----------------------|
| **A. Conditions d'entrée** | Quelles entrées prendre / refuser ? | Nouveau filtre, tweak d'un filtre existant, condition supplémentaire à `generate_signals()` | Comparer ce qui distingue les entrées gagnantes des perdantes |
| **B. Évitement des SL** | Comment éviter ou couper les trades qui finissent en SL ? | Filtre pré-entrée si pattern toxique récurrent, exit défensif si pas de momentum après N bars, SL plus serré si la signature le permet | Patterns des trades perdants (Stop Loss + Auto-Close loss) |
| **C. Optimisation des TP** | Comment maximiser le PnL des trades qui marchent ? | Condition d'exit différée, partial exit conditionnel, hold plus long si signal aligné, sortie anticipée si MFE plafonne | Patterns des trades gagnants (Canal Exit profit + Auto-Close profit) |

**Pour CHAQUE pilier**, tu dois analyser **les deux populations** :

- **Winners → amplification** : qu'est-ce qui caractérise les entrées gagnantes ? Comment en prendre davantage ou maximiser leur PnL ?
- **Losers → exclusion** : qu'est-ce qui caractérise les entrées perdantes ? Comment les filtrer ou les couper avant le SL ?

**Quota sur les hypothèses retenues — qualité > quantité** :
- **1 à 3 hypothèses par pilier** (A, B, C). Pas plus.
- **Total : 3 à 9 hypothèses au maximum.**
- **≥ 1 hypothèse motivée par les losers** (filtre d'exclusion ou exit défensif) — interdit de ne traiter que les winners.

**Principe** : il vaut mieux **2-3 hypothèses solidement testées** (sweep multi-valeurs, walk-forward, verdict robuste) que **8 hypothèses bâclées**. Si tu ne sais pas choisir entre 5 idées candidates pour un pilier, garde les 2-3 avec la **meilleure cross-preset stability** et le **plus gros effet observé en Phase 1**. Les autres sont notées dans `OBSERVATIONS.md` comme "non retenues pour ce cycle" (utiles pour l'itération suivante).

Exemple concret de répartition acceptable :
- 2 hypothèses pilier A (1 amplification winners, 1 filtre losers)
- 2 hypothèses pilier B (toutes deux issues des losers)
- 1 hypothèse pilier C (cut anticipé issue des losers)
= 5 hypothèses, 3 piliers couverts, 4 issues des losers.

Autre répartition acceptable :
- 1 hypothèse pilier A (amplification winners)
- 1 hypothèse pilier B (issue des losers)
- 1 hypothèse pilier C (issue des winners)
= 3 hypothèses, minimum strict, mais testées en profondeur (sweep + walk-forward + combo).

---

## 🎯 Variables à remplir avant de lancer

> Remplis cette section AVANT d'invoquer le prompt. Supprime les options non retenues.

- **Stratégie à étudier** *(une seule)* :
  - `HMASSLOsciV3`

- **Nom de la stratégie duplicate à créer** : `HMASSLOsciV3Labv1`
  - **UN SEUL FICHIER** : `src/strategies/<snake_case_name>.py` — toutes les hypothèses de la campagne s'accumulent dans cette même classe.
  - **Hérite** de la stratégie originale, ne la copie pas.
  - **Un paramètre configurable par hypothèse**, default = comportement original (= V3 strict si Lab hérite de V3).
  - Chaque hypothèse vit dans son propre bloc `if p.get("<flag>"): …` — indépendante et désactivable.
  - Test #0 obligatoire : Lab avec tous les flags à default reproduit V3 exact.

- **Presets gagnants de référence** *(min. 1, max. 3)* :
  - `scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/winner_preset.json`
  - `scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/winner_preset.json`
  - `scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/winner_preset.json`
  - Ces presets sont les **baselines vs lesquelles chaque hypothèse est mesurée**. Le PnL et le DD de référence sont leurs valeurs publiées dans leurs `REPORT.md`.

- **Période** : reprend celle des presets de référence

- **Initial equity** : `50 000 $` (ou ce que dictent les presets).

- **Auto-close** : **22:00 reference Brussels — FIXE, NE JAMAIS MODIFIER**.

- **Nombre d'hypothèses à tester** : **1 à 3 par pilier (A, B, C), total 3-9**. Qualité > quantité. Toutes doivent provenir d'observations sourcées (Phase 1) — pas d'idées hors-sol.

- **Budget simulation** : `~150-250` runs au total. Une hypothèse simple = 1 A/B (2 runs). Une hypothèse à sweep param = 5-15 runs. Mieux vaut 3 hypothèses testées en profondeur (sweep multi-valeurs + walk-forward + combo) que 8 testées superficiellement.

---

## 🗂️ Organisation des fichiers (obligatoire)

```
src/strategies/
└─ <strategy_lab>.py                        ← NOUVELLE classe, hérite de l'originale
                                                Defaults = comportement original.
                                                ⚠ Ajoute aussi son entrée dans
                                                  STRATEGY_WARMUP_BARS si l'originale
                                                  y figure (backend/api.py).

scripts/goals/
└─ <YYYY-MM-DD>_<Strategy>_evolution/        ← UNE campagne = UN dossier
   ├─ README.md                             ← objectifs + statut + reproduction
   ├─ phase1_observation/                   ← analyse trade-par-trade des winners
   │  ├─ run_analysis.py
   │  ├─ outputs/
   │  │  ├─ trades_<preset>.csv             ← 1 ligne par trade + contexte indicateur
   │  │  ├─ trades_ALL.csv                  ← cumul des 3 presets
   │  │  └─ summary.json                    ← aggregates par statut, hour, slope, etc.
   │  └─ OBSERVATIONS.md                    ← 10-20 hypothèses brutes, classées
   ├─ phase2_hypotheses/                    ← UN sweep par hypothèse
   │  ├─ _shared.py                         ← BASELINES dict, helpers de comparaison
   │  ├─ 00_sanity_lab_equals_v3.py         ← OBLIGATOIRE : Lab(defaults) == V3 ✓
   │  ├─ 01_<hypothesis_name>.py            ← ex. 01_entry_window_min_bars.py
   │  ├─ 02_<hypothesis_name>.py
   │  ├─ … (5-10 sweeps au total)
   │  └─ logs/                              ← un .log par sweep
   ├─ phase3_combinations/                  ← combos des hypothèses KEEP
   │  ├─ 01_pairs.py
   │  ├─ 02_triples.py
   │  └─ logs/
   ├─ winner_v4_<asset>.json                ← preset gagnant V<N+1> par asset
   ├─ verify_winner_v4.py                   ← rejoue chaque winner V<N+1>
   ├─ HYPOTHESES.md                         ← tableau des 5-10 hypothèses + verdicts
   └─ REPORT.md                             ← rapport final
```

**Règles strictes** :
1. **La nouvelle stratégie doit hériter de l'originale**, surcharger uniquement ce qui change, et conserver tous les paramètres de l'originale identiques par défaut.
2. **Le sweep `00_sanity_lab_equals_v3.py` est obligatoire** : il rejoue les 3 baselines avec `<Strategy>Lab` + tous les nouveaux flags désactivés et **doit** retrouver le PnL/DD exact des winners originaux (à 1 cent près). Si non, la nouvelle stratégie est cassée — arrêter et déboguer avant tout le reste.
3. **Une hypothèse = un fichier `phase2_hypotheses/NN_<name>.py`** qui produit un tableau A/B (baseline vs ON) sur **chacun** des 3 presets de référence. Chaque sweep redirige son output vers `logs/`.
4. **Toujours utiliser `scripts/goals/_shared/harness.py::run_backtest`** — jamais reconstruire les engine settings à la main.
5. Le `<strategy>_lab.py` reste **dans `src/strategies/`** (le mécanisme d'auto-discovery l'enregistre automatiquement). Ce n'est PAS une violation du "ne pas modifier la stratégie existante" : c'est une **nouvelle** stratégie qui en hérite. Le fichier original n'est pas touché.

---

## 🧱 Contraintes techniques

1. **Ne pas modifier les stratégies existantes.** Toute évolution passe par une nouvelle classe dans `src/strategies/<lab>.py` qui hérite.
2. **UNE seule stratégie Lab pour TOUTES les hypothèses de la campagne** (voir section dédiée ci-dessous). Pas N versions de la stratégie.
3. **Ne pas modifier le simulateur** (`src/engine/simulator.py`). Si une hypothèse nécessite un comportement d'exit non supporté, le **simuler dans la stratégie** (en pré-calculant des séries de signaux que le simulateur consomme déjà — `partial_close_long/short`, `entry_price_long/short`, etc.) ou l'inclure dans le `REPORT.md` comme "non testable sans refonte moteur — proposition pour itération ultérieure".
4. **Une hypothèse à la fois par sweep.** Pas de comparaison "Lab avec 4 flags ON vs V3". Toujours ON / OFF d'UN flag, sur les MÊMES presets de référence.
5. **Reporter PnL et DD en $** (pas en %), pour pouvoir comparer directement aux objectifs des presets.
6. **Métrique de tri** : delta de **ratio Profit/DD**. Une hypothèse qui ajoute du PnL en ajoutant proportionnellement plus de DD ne KEEP pas.
7. **Auto-close à 22:00** — non négociable, jamais sweepé.
8. **Defaults UI = source de vérité** (cf. `_shared/engine_settings.py`).

---

## 🧪 UNE seule stratégie Lab, paramètres indépendants

Modèle attendu : **à la fin de la campagne, il existe UN SEUL fichier `src/strategies/<strategy>_lab.py`** qui contient **tous les paramètres correspondant à toutes les hypothèses testées**, chacun indépendant et désactivable, avec default = comportement V3 d'origine.

### Pourquoi ?

- **Lecture du rapport simple** : tu lis `HYPOTHESES.md`, tu vois les verdicts, tu choisis ce que tu veux activer. Pas besoin de jongler entre N classes.
- **Adoption sélective** : si tu valides 3 hypothèses sur 5, tu actives 3 flags dans le preset. Les 2 autres restent OFF mais le code existe pour les retester plus tard.
- **Indépendance garantie** : chaque hypothèse vit dans son propre bloc conditionnel `if p.get("<flag>", default): …` — pas de couplage entre elles.
- **Compatibilité ascendante** : `Lab` avec tous les flags par défaut produit exactement les trades de V3 (= test `00_sanity_lab_equals_v3.py`).

### Squelette type d'une stratégie Lab cumulative

```python
# src/strategies/hma_ssl_osci_v3_lab.py
from .hma_ssl_osci_v3 import HMASSLOsciV3
import pandas as pd
import numpy as np


class HMASSLOsciV3Lab(HMASSLOsciV3):
    """Bench d'évolutions de HMASSLOsciV3. Tous les nouveaux paramètres
    ont un default qui reproduit le comportement V3 exact — la stratégie
    Lab sans aucun flag activé = V3 strict (vérifié par le sanity test).
    """

    name = "HMASSLOsciV3Lab"

    default_params = {
        **HMASSLOsciV3.default_params,
        # === Hypothèse 1 — Pilier A (entry) : retard fenêtre d'entrée
        "entry_window_min_bars": 0,         # default V3 = 0 (pas de retard)
        # === Hypothèse 2 — Pilier A (entry) : filtre candle agressive
        "lab_max_candle_pct": 0.0,          # 0 = inactif (= V3)
        # === Hypothèse 3 — Pilier B (SL avoidance) : exit défensif MAE
        "lab_early_kill_mae_r": 0.0,        # 0 = inactif
        # === Hypothèse 4 — Pilier C (TP optim) : pas de Canal Exit tard si in-profit
        "lab_no_canal_exit_after_hour": 0,  # 0 = inactif
        # === Hypothèse 5 — Pilier C (TP optim) : exit MFE-floor
        "lab_mfe_floor_r": 0.0,             # 0 = inactif
    }

    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "entry_window_min_bars":    [0, 1, 2, 3, 4],
        "lab_max_candle_pct":       [0.0, 0.3, 0.5, 0.7],
        "lab_early_kill_mae_r":     [0.0, 0.6, 0.8, 1.0],
        "lab_no_canal_exit_after_hour": [0, 20, 21],
        "lab_mfe_floor_r":          [0.0, 0.2, 0.3, 0.5],
    }

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        result = super().generate_signals(data, p)

        # === H1 — entry_window_min_bars =====================================
        min_bars = int(p.get("entry_window_min_bars", 0))
        if min_bars > 0:
            self._apply_entry_window_min(result, data, min_bars)

        # === H2 — lab_max_candle_pct ========================================
        max_cp = float(p.get("lab_max_candle_pct", 0.0))
        if max_cp > 0.0:
            self._apply_candle_filter(result, data, max_cp)

        # === H3 — early_kill_mae_r : nécessite séries consommées par le sim
        # ex. injecter dans `be_long/be_short` ou pré-calculer
        # `partial_close_long/short` — cf. simulator.py pour les signaux
        # consommables sans modification moteur.
        # … etc.

        return result

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        s = super().get_simulator_settings(p)
        # === H4 — lab_no_canal_exit_after_hour : surcharger le mode d'exit
        # … etc.
        return s

    # ----- helpers privés, un par hypothèse -----
    def _apply_entry_window_min(self, result, data, min_bars):
        setup_long = result["setup_bar_long"]
        setup_short = result["setup_bar_short"]
        long_e = result["long_entries"].values.copy()
        short_e = result["short_entries"].values.copy()
        for i in range(len(long_e)):
            if long_e[i] and setup_long.iloc[i] >= 0:
                if (i - int(setup_long.iloc[i])) < min_bars:
                    long_e[i] = False
            if short_e[i] and setup_short.iloc[i] >= 0:
                if (i - int(setup_short.iloc[i])) < min_bars:
                    short_e[i] = False
        result["long_entries"] = pd.Series(long_e, index=data.index)
        result["short_entries"] = pd.Series(short_e, index=data.index)

    def _apply_candle_filter(self, result, data, max_cp):
        # cancel entries on bars where candle body % > max_cp
        # …
        pass
```

### Conventions de nommage

- **Préfixe `lab_`** sur les paramètres dont le nom risque d'entrer en collision ou qui sont clairement spécifiques au Lab. Pas de préfixe pour les paramètres "évidents" qui pourraient migrer dans la stratégie d'origine si validés (ex. `entry_window_min_bars`).
- **Default = neutralité** : 0, False, "" ou ce qui désactive le bloc. JAMAIS un default qui change le comportement V3.
- **Un helper privé `_apply_<hyp_name>()` par hypothèse** — découpe le code par hypothèse, lisible, supprimable proprement si l'hypothèse est rejetée à la prochaine itération.

### Conséquence sur les sweeps

Les sweeps de Phase 2 lancent tous le **même Lab** avec un seul flag toggle entre OFF et ON :

```python
# phase2_hypotheses/01_entry_window_min_bars.py
PARAMS_OFF = {"entry_window_min_bars": 0}                    # = V3 strict
PARAMS_ON  = {"entry_window_min_bars": 2}                    # H1 active
# … run baseline avec PARAMS_OFF puis avec PARAMS_ON
```

```python
# phase2_hypotheses/02_max_candle_pct.py
PARAMS_OFF = {"lab_max_candle_pct": 0.0}                     # = V3 strict
PARAMS_ON  = {"lab_max_candle_pct": 0.5}                     # H2 active
# …
```

Les combos de Phase 3 activent plusieurs flags en même temps sur le même Lab.

---

## 🛠️ Méthode obligatoire

### Phase 1 — Observation (génération d'hypothèses, winners ET losers)

Dans `phase1_observation/run_analysis.py` :

1. **Replay déterministe** des presets de référence (sanity-check : PnL doit matcher les rapports publiés à 1 cent près). Si match raté → ton harness est mal configuré, débugue avant d'avancer.
2. **Capturer pour chaque trade actif** : entry/exit time, side, status, pnl, size, sl_dist_pts, MAE/MFE en R, bars_in_trade, position dans la fenêtre d'entrée (`bars_since_setup`), état des indicateurs à l'entrée et à la sortie (canal width / slope / color, HW value, MFI, etc.), temps jusqu'au prochain HW post-entrée et post-sortie, distance R d'un "shadow exit" (sortie au HW suivant).
3. **Bucketiser symétriquement winners ET losers** — pour chaque variable d'entrée (slope, width, hw value, hour, sl distance, bars_since_setup, etc.), produire DEUX vues :
   - Distribution des **winners** (Canal Exit profit + Auto-Close profit + TP_HW)
   - Distribution des **losers** (Stop Loss + Auto-Close loss + Canal Exit loss si applicable)
   - Le but : repérer où les deux distributions divergent maximalement = signature exploitable.
4. **Construire `OBSERVATIONS.md` en 3 sections (= 3 piliers)**. Chaque section contient des sous-sections **Winners** et **Losers** :

   ```markdown
   # OBSERVATIONS.md

   ## A. Conditions d'entrée
   ### A.1 — issues des Winners
   - obs-A1a : "les entrées avec canal slope ∈ [0, +0.01%/bar] sortent R=1.18 (n=85) vs R=0.20 ailleurs"
     → hypothèse : ajouter filtre `canal_max_abs_slope` qui force ce range
   - …
   ### A.2 — issues des Losers
   - obs-A2a : "les SL <1 bar (n=128, −$23k) ont en moyenne candle_pct=1.4% à l'entrée vs 0.6% pour les non-SL"
     → hypothèse : abaisser `max_candle_pct` à 0.5
   - …

   ## B. Évitement des SL
   ### B.1 — issues des Winners
   - obs-B1a : "les trades survivants à 4+ bars ont MAE moyen=0.65R vs 1.40R pour les SL → la signature 'pas de drawdown brutal au début' est prédictive"
     → hypothèse : exit défensif si MAE >0.8R dans les 3 premiers bars
   ### B.2 — issues des Losers
   - obs-B2a : "65% des SL ont un canal qui n'a PAS flippé pendant la vie du trade"
     → hypothèse : cut anticipé si après N bars le canal reste contre le trade
   - …

   ## C. Optimisation des TP
   ### C.1 — issues des Winners
   - obs-C1a : "les Auto-Close (profit) capturent +$45k avec WR 98% → quand un trade tient jusqu'à 21:00 en profit, il finit presque toujours +"
     → hypothèse : désactiver Canal Exit après 21:00 si in-profit (forcer auto-close)
   ### C.2 — issues des Losers
   - obs-C2a : "les Canal Exit losers ont MFE moyen=0.39R, 77% n'ont jamais dépassé +0.5R → ces trades n'ont jamais 'fonctionné'"
     → hypothèse : exit anticipé si MFE plafonne sous 0.3R après 5 bars
   ```

5. **Top 5-10 hypothèses retenues** = celles avec :
   - cross-preset stability (signal va dans le même sens sur les 3 presets),
   - magnitude visible (delta de moyenne non noyé dans la variance),
   - n suffisant (caveat sample size si n<100).
   - **Respect du quota par pilier** : min 1 hypothèse par pilier (A, B, C), min 1 hypothèse issue des losers.

> **Conformément aux retours utilisateur passés** : l'observation est nécessaire mais **insuffisante**. La phase 1 ne livre PAS d'insight final. Elle livre des hypothèses **à tester en Phase 2**.

#### ⚠️ Anti-pattern Phase 1 — analyser seulement les winners

Si tu produis 8 hypothèses dont 8 viennent uniquement de la lecture des trades gagnants, **la moitié du signal du dataset est ignorée**. Les losers sont au moins aussi instructifs : ils racontent **ce qu'il NE faut pas prendre** ou **comment couper plus tôt**, ce qui est souvent le levier le plus rentable (réduire le DD vaut autant pour le ratio P/DD que d'augmenter le PnL).

### Phase 2 — Test empirique (le cœur du travail)

> **Principe** : transformer chaque hypothèse en **un paramètre configurable** ajouté à `<Strategy>Lab`. Tu codes le tweak (= la nouvelle condition) directement dans la stratégie Lab, mais sous un flag dont le default reproduit le comportement V3 original. Le sweep d'hypothèse n'a alors qu'à toggler le flag OFF/ON.
>
> Concrètement, c'est l'équivalent de "adapte la stratégie pour ajouter cette nouvelle condition" sauf que :
> - la modification est **isolée dans `<Strategy>Lab`** (pas dans la classe d'origine),
> - elle est **rétrocompatible** (default = V3),
> - elle est **mesurable** (A/B sweep automatique).

Pour chaque hypothèse retenue, faire les 3 étapes :

#### Étape 2.a — Ajouter le paramètre dans `<Strategy>Lab`

Exemple pour l'hypothèse "n'entrer qu'à partir du Nᵉ bar après le slow-cross" :

```python
# Dans src/strategies/hma_ssl_osci_v3_lab.py
from .hma_ssl_osci_v3 import HMASSLOsciV3

class HMASSLOsciV3Lab(HMASSLOsciV3):
    name = "HMASSLOsciV3Lab"

    default_params = {
        **HMASSLOsciV3.default_params,
        # === Nouveau param (default = comportement V3 = 0) ===
        "entry_window_min_bars": 0,
    }

    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "entry_window_min_bars": [0, 1, 2, 3, 4],
    }

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        result = super().generate_signals(data, p)
        min_bars = int(p.get("entry_window_min_bars", 0))
        if min_bars > 0:
            # Récupère setup_bar_long/short déjà calculés par V3
            setup_long = result["setup_bar_long"]
            setup_short = result["setup_bar_short"]
            long_e = result["long_entries"].values
            short_e = result["short_entries"].values
            for i in range(len(long_e)):
                if long_e[i] and setup_long.iloc[i] >= 0:
                    if (i - int(setup_long.iloc[i])) < min_bars:
                        long_e[i] = False
                if short_e[i] and setup_short.iloc[i] >= 0:
                    if (i - int(setup_short.iloc[i])) < min_bars:
                        short_e[i] = False
            import pandas as pd
            result["long_entries"] = pd.Series(long_e, index=data.index)
            result["short_entries"] = pd.Series(short_e, index=data.index)
        return result
```

Notes :
- Le default `entry_window_min_bars=0` reproduit V3 exactement (filtre inactif).
- L'hypothèse vit **uniquement dans le Lab**, jamais dans `hma_ssl_osci_v3.py`.
- Si l'hypothèse touche aux exits, surcharger `get_simulator_settings()` plutôt que `generate_signals()`.
- Si l'hypothèse nécessite une logique d'exit non supportée par le simulateur, la **simuler via les séries de signaux que le simulateur consomme déjà** (`partial_close_long/short`, `entry_price_long/short`, `canal_exit_requires_arming`, etc.) — pas de modif du simulateur.

#### Étape 2.b — Écrire `phase2_hypotheses/NN_<name>.py`

Ce script doit :
- Définir les 3 presets de référence (`_shared.py::BASELINES`).
- Pour chaque preset, lancer la version **OFF** (= reproduction baseline avec Lab + default) et la version **ON** (= hypothèse active).
- Optionnel : sweep multi-valeurs (ex. `entry_window_min_bars ∈ {1, 2, 3}`).
- Sortie en tableau format `_shared.py::print_ab_row` :

     ```
     === Hypothesis: <name> ===
     Preset       | Baseline PnL | Baseline DD | ON PnL    | ON DD   | ΔPnL    | ΔDD    | ΔP/DD
     MNQ_v4       | $50,770      | $2,268      | $51,200   | $2,180  | +$430   | -$88   | +1.42
     MGC_v2       | $44,711      | $2,378      | $44,100   | $2,420  | -$611   | +$42   | -0.82
     MNQ_MGC      | $101,921     | $2,363      | $103,500  | $2,290  | +$1,579 | -$73   | +2.18
     ```

#### Étape 2.c — Verdict de l'hypothèse

   - **KEEP** si ΔP/DD positif sur ≥ 2 des 3 presets et négatif nulle part de manière catastrophique.
   - **REJECT** si ΔP/DD négatif sur ≥ 2 des 3 presets ou si le DD explose.
   - **MIXED** si améliore un asset et dégrade un autre — noter pour les combos asset-spécifiques.

**Important** : si une hypothèse change le **nombre de trades** entre OFF et ON, le delta brut est attendu — ce qui compte c'est le delta du ratio P/DD et le profil (où on a coupé : les bons ou les mauvais trades ?). Toujours documenter la baisse/hausse de N avec son effet sur PnL/DD séparément.

### Phase 3 — Combinaisons

1. Prendre les hypothèses **KEEP** et leurs valeurs sweet-spot. Tester les **paires** puis le **combo complet**.
2. Comparer le combo final aux baselines.
3. Si le combo gagne sur **≥ 1 preset** → **construire `winner_v4_<asset>.json`** et `verify_winner_v4.py`.

### Phase 4 — Validation & risque

- **Walk-forward simple** : split la période en 2 (training / test). Re-fit les hypothèses KEEP sur la 1ère moitié, mesurer le delta sur la 2nde. Si une hypothèse dégrade sur la seconde moitié → la rétrograder en MIXED dans le REPORT.
- **Out-of-sample** : si possible, tester sur une période adjacente (1 mois avant ou après).

---

## 📦 Livrables obligatoires

À la fin, fournis dans cet ordre :

### 1. La nouvelle stratégie

`src/strategies/<strategy_lab>.py` qui :
- Hérite de la stratégie originale.
- Ajoute les nouveaux paramètres avec defaults = comportement original.
- Le test `00_sanity_lab_equals_v3.py` doit passer (Lab(defaults) reproduit exactement V3).

### 2. Tableau de verdicts (`HYPOTHESES.md`)

Format obligatoire — la colonne **Pilier** (A entry / B SL avoidance / C TP optim) et la colonne **Angle** (W winners / L losers / W+L) sont **non négociables** : elles forcent la couverture des 3 piliers et la prise en compte des losers.

```markdown
| # | Pilier | Angle | Hypothèse | Param ajouté | Source obs. | Verdict | Best ΔPnL$ | Best ΔDD$ | Best ΔP/DD | Cross-preset | Note |
|--:|:------:|:-----:|-----------|--------------|-------------|---------|-----------:|----------:|-----------:|--------------|------|
| 1 | A | W | Entrer N≥2 bars après setup | `entry_window_min_bars=2` | obs-A1b | KEEP | +$2,150 | −$120 | +3.10 | 3/3 ✓ | sweet spot 2-3 |
| 2 | A | L | Filtrer entrées avec candle_pct>0.5 | `max_candle_pct=0.5` | obs-A2a | KEEP | +$1,400 | −$310 | +2.80 | 3/3 ✓ | tue 8% des trades, presque tous SL |
| 3 | B | L | Exit défensif si MAE>0.8R en 3 bars | `early_kill_mae_r=0.8` | obs-B2b | MIXED | +$900 (MNQ) / −$300 (MGC) | … | … | 2/3 | asset-specific |
| 4 | B | W | Cut si canal non-flippé après 8 bars | `canal_flip_timeout=8` | obs-B1c | REJECT | … | … | … | 1/3 | tue les long-runners |
| 5 | C | W | Désactiver Canal Exit après 21h si in-profit | `no_canal_exit_late_if_profit=True` | obs-C1a | KEEP | +$1,800 | +$50 | +2.40 | 3/3 ✓ | capture +Auto-Close |
| 6 | C | L | Exit anticipé si MFE plafonne sous 0.3R | `mfe_floor_r=0.3` | obs-C2a | … | … | … | … | … | … |
```

Quota à respecter dans la colonne **Pilier** : ≥ 1 ligne par pilier (A, B, C).
Quota à respecter dans la colonne **Angle** : ≥ 1 ligne issue des losers (L ou W+L).

### 3. Preset(s) JSON V<N+1>

Pour chaque asset où le combo final bat la baseline :
- `winner_v4_<asset>.json` au format UI (utilise `_shared/preset.py::build_preset` + `write_preset`).
- Visible en tête des favoris UI (insertion auto dans `data/presets.json`).

### 4. Script de vérification (`verify_winner_v4.py`)

Rejoue chaque winner V<N+1> et affiche `✅ MATCH` ou `❌ DIFF`. Pas de match → ne pas déclarer le job fini.

### 5. Rapport markdown (`REPORT.md`)

Sections obligatoires, dans cet ordre :

1. **Cadrage** — période, presets de référence, métriques de baseline (1 paragraphe).
2. **Phase 1 — observation** — 1 tableau résumé des hypothèses brutes générées, lien vers `OBSERVATIONS.md`.
3. **Phase 2 — A/B tests** — Pour chaque hypothèse testée :
   - Hypothèse en 1 ligne.
   - Mécanisme proposé en 2-3 lignes.
   - Tableau A/B (cf. format ci-dessus).
   - **Verdict** : KEEP / REJECT / MIXED + justification.
4. **Phase 3 — combinaison gagnante** — Combo final + delta vs baselines + DD safe ?
5. **Phase 4 — validation walk-forward** — résultats par fold, hypothèses qui dégradent hors-fold.
6. **Limites & risques** — overfit, sample size, dépendance à un contrat.
7. **Pistes pour itération suivante** — hypothèses MIXED à creuser, hypothèses non-testables (refonte moteur), audits restants.
8. **Reproduction** — 2-3 lignes (script `run_analysis.py`, sweeps `02_*.py`, verify).

### 6. Logs des sweeps

Chaque sweep : `… | tee logs/<nom>.log`. Logs sont des artefacts d'audit.

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :

1. ✅ **Sanity test passé** : `00_sanity_lab_equals_v3.py` reproduit les baselines à 1 cent près sur les 3 presets, avec **TOUS les flags Lab à leur default** (= comportement V3 strict).
2. ✅ **Entre 3 et 9 hypothèses testées** (1 à 3 par pilier), chacune avec un A/B sweep réel.
3. ✅ **Couverture des 3 piliers** : ≥ 1 hypothèse pilier A (entry), ≥ 1 pilier B (SL avoidance), ≥ 1 pilier C (TP optim).
4. ✅ **Analyse symétrique winners/losers** : ≥ 1 hypothèse issue des losers (= filtre d'exclusion ou exit défensif) **explicitement marquée Angle=L ou W+L** dans `HYPOTHESES.md`.
5. ✅ **Chaque hypothèse a un verdict** KEEP / REJECT / MIXED dans `HYPOTHESES.md` adossé à des chiffres.
6. ✅ **Au moins 1 winner V<N+1>** existe (sinon le rapport explique pourquoi aucune combinaison ne bat les baselines).
7. ✅ `verify_winner_v4.py` affiche `✅ MATCH` pour chaque winner.
8. ✅ **UN SEUL fichier `<strategy>_lab.py`** existe dans `src/strategies/`, **hérite** de la stratégie originale, **ajoute UN paramètre configurable par hypothèse** (default = comportement original), et n'a PAS modifié la stratégie originale.
9. ✅ Chaque hypothèse correspond à un **bloc indépendant et désactivable** dans le Lab (helper privé `_apply_<name>()` recommandé). On peut activer un sous-ensemble sans casser les autres.
10. ✅ `REPORT.md` couvre les 8 sections obligatoires.
11. ✅ Tous les fichiers de la campagne sont dans `scripts/goals/<slug>/`, rien à plat.

Si une hypothèse n'a pas pu être testée (limite moteur, complexité hors budget), la marquer **NOT TESTED** dans `HYPOTHESES.md` avec la raison — **ça ne compte PAS dans le quota des 5-10**.

---

## 🧠 Bonnes pratiques

- **Pas de soft claims** : "ce serait intéressant", "à priori ça aiderait", "il semble que" — interdits. Toute affirmation = chiffre du backtest.
- **Une hypothèse par sweep**. Si tu testes 4 paramètres ensemble, tu ne sais pas lequel contribue.
- **Toujours les MÊMES presets de référence** pour A/B — sinon les deltas ne sont pas comparables.
- **Mesure delta en $** (pas en %) — le DD est budgeté en $, le PnL aussi.
- **Reproduire toute hypothèse à coup sûr** : si un sweep n'est pas rerunnable, l'insight ne peut pas être audité plus tard.
- **L'observation seule ne livre pas** : si Phase 1 produit 12 observations mais Phase 2 n'en teste que 3, c'est un échec de la mission, pas un succès partiel.
- **Walk-forward même léger > rien** : un simple split 50/50 invalide la moitié des "sweet spots" de rounding.
- **Documente les "non-événements"** : une hypothèse REJECT est un insight aussi précieux qu'un KEEP. Le tableau les liste toutes.

---

## ⚙️ Référence rapide

| Information | Fichier |
|-------------|---------|
| Stratégies + warmup | `backend/api.py` (`STRATEGIES`, `STRATEGY_WARMUP_BARS`) |
| Defaults UI | `frontend/src/api.ts` + `frontend/src/App.tsx` |
| Miroir Python UI defaults | `scripts/goals/_shared/engine_settings.py` |
| Harness backtest | `scripts/goals/_shared/harness.py` |
| Build/verify preset | `scripts/goals/_shared/preset.py` |
| Logique simulateur, exit modes | `src/engine/simulator.py` |
| Specs contrats | `backend/api.py` (`CONTRACT_SPECS`) |
| Exemple campagne classique | `scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/` |
| Exemple analyse observation seule (sans A/B) | `scripts/goals/2026-05-17_HMASSLOsciV3_analysis/` (= ce qu'il ne FAUT PAS produire seul) |

---

## ❌ Anti-patterns observés (à NE PAS reproduire)

- **Produire 9 insights observés mais aucun A/B test** → c'est de l'analyse, pas de l'évolution stratégie.
- **N'analyser que les winners** → la moitié du signal du dataset est ignorée. Les patterns des losers sont au moins aussi instructifs (où couper, quoi filtrer, comment réduire le DD).
- **Concentrer toutes les hypothèses sur un seul pilier** (ex. 6 hypothèses sur les entrées, 0 sur les SL et 0 sur les TP) → la couverture A/B/C est obligatoire.
- **Proposer une "v4 future" sans la coder** → la duplicate strategy doit exister et le sanity test doit passer.
- **Tester sur 1 seul preset** → le verdict cross-asset est central ; minimum 2 presets différents.
- **Sweep multi-paramètre sans baseline matching** → si la version OFF du sweep ne reproduit pas le winner d'origine, le delta mesure du bruit.
- **Compter une hypothèse non testée dans les 5-10** → seules les hypothèses avec un sweep + verdict comptent.
- **Combiner 5 hypothèses puis A/B le combo vs baseline** sans avoir A/B chaque hypothèse seule → on ne sait pas attribuer le delta.
- **Toucher au simulateur ou à la stratégie originale** pour faire passer une hypothèse → utiliser uniquement de la composition via la nouvelle classe Lab.
- **Créer une classe Lab par hypothèse** (ex. `HMASSLOsciV3LabH1`, `H2`, …) → tout doit s'accumuler dans **UN SEUL `<Strategy>Lab`** avec un paramètre toggleable par hypothèse. Sinon c'est ingérable, illisible, et le combo final demande de fusionner les classes à la main.
- **Multiplier les hypothèses bâclées** (8-10 testées en surface) → mieux vaut 3-5 testées en profondeur (sweep multi-valeurs + walk-forward + combo). Quota max = 3 par pilier, 9 au total.

---

## 📐 Format du `_shared.py` d'une campagne d'évolution

Helper minimal à mettre dans `phase2_hypotheses/_shared.py` :

```python
"""Constants and helpers shared across hypothesis sweeps."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

# Each baseline = absolute path to a winner preset
BASELINES = {
    "MNQ_v4": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/winner_preset.json",
    "MGC_v2": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/winner_preset.json",
    "MNQ_MGC": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/winner_preset.json",
}

# Reference PnL/DD from the published REPORT.md of each baseline
BASELINE_METRICS = {
    "MNQ_v4":  {"pnl": 50_770.0, "dd": 2_268.0},
    "MGC_v2":  {"pnl": 44_711.0, "dd": 2_378.0},
    "MNQ_MGC": {"pnl": 101_921.0, "dd": 2_363.0},
}


def load_preset(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def print_ab_row(label: str, base_pnl: float, base_dd: float,
                 on_pnl: float, on_dd: float):
    dpnl = on_pnl - base_pnl
    ddd  = on_dd - base_dd
    base_pdd = base_pnl / base_dd if base_dd else 0
    on_pdd   = on_pnl / on_dd if on_dd else 0
    print(f"{label:<14s} | ${base_pnl:>10,.0f} | ${base_dd:>6,.0f} | "
          f"${on_pnl:>10,.0f} | ${on_dd:>6,.0f} | "
          f"{dpnl:+9,.0f} | {ddd:+7,.0f} | {(on_pdd-base_pdd):+5.2f}")
```

Et le squelette d'un sweep d'hypothèse :

```python
"""01_entry_window_min_bars — A/B test sur les 3 baselines."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize
from _shared import BASELINES, BASELINE_METRICS, load_preset, print_ab_row

HYPOTHESIS = {
    "name": "entry_window_min_bars",
    "param_key": "entry_window_min_bars",
    "values_to_sweep": [1, 2, 3],     # OFF=0 baseline, ON=2 sweep
    "off_value": 0,
}

# … code qui pour chaque baseline x chaque valeur lance run_backtest …
# Compare et appelle print_ab_row.
```

L'organisation tarir par sweep = un seul fichier indépendant rerunable = audit facile.
