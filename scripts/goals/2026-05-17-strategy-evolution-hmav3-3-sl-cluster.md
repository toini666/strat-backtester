# Goal — Évolution ciblée de HMASSLOsciV3 : chaînes de SL en latéralisation

Ton objectif est de **diagnostiquer puis valider expérimentalement** des contre-mesures concrètes au phénomène d'**enchaînements de stop-loss consécutifs** observé sur `HMASSLOsciV3`, en particulier (mais pas exclusivement) en périodes de latéralisation. La mission est en deux temps :

- **D'abord caractériser** : qu'est-ce qu'un "cluster de SL" sur cette stratégie ? Est-il statistiquement anormal (vs un enchaînement aléatoire compte tenu du WR) ? À quels patterns / régimes est-il corrélé ?
- **Ensuite traiter** : tester 5 à 9 contre-mesures via une stratégie Lab, et mesurer leur effet sur PnL / DD / ratio P/DD.

Chaque insight doit être adossé à un **A/B test réel** sur les backtests, pas à une simple observation.

Tu travailles en **trois phases obligatoires** :

1. **Observer & caractériser** — instrumenter les SL pour repérer les clusters, mesurer si le phénomène est statistiquement réel, et générer des hypothèses de mitigation (Phase 1 = la phase la plus importante de cette mission).
2. **Tester** — dupliquer la stratégie en `HMASSLOsciV3LabSLClusterV1` et **implémenter chaque hypothèse comme un paramètre configurable** dont le default reproduit le comportement V3 exact. Chaque hypothèse passe par un A/B sweep réel (OFF=baseline, ON=hypothèse active).
3. **Synthétiser** — pour chaque hypothèse : verdict KEEP / REJECT / MIXED + chiffres, et proposer une vraie config "winner V<N+1>" pour chaque asset où ça bat la baseline.

**Une hypothèse non testée ne compte pas.** Le livrable se mesure au nombre d'hypothèses adossées à un A/B sweep reproductible.

---

## 🎯 Contexte — pourquoi cette campagne

**Observation utilisateur** : "Dans les périodes de latéralisation, on a parfois des enchaînements de plusieurs SL d'affilée." Ces clusters sont coûteux à double titre : ils tirent le DD vers le bas (concentration des pertes) **et** ils érodent le moral / la confiance dans le système.

**Mais avant de "corriger"**, il faut **objectiver** :

1. Les clusters de SL sont-ils plus fréquents que ce qu'on attendrait d'un processus aléatoire avec le WR observé ? (Test de Wald-Wolfowitz / runs test, ou simulation de Bernoulli.)
2. Si oui, sont-ils corrélés à un état mesurable du marché (largeur de canal HMA, slope HMA, ATR, range/ATR ratio, MFI plat, oscillateur plat, heure, session, contrat-spécifique) ?
3. Existe-t-il un signal détectable **avant** ou **pendant** le premier SL d'un futur cluster, qui permettrait de filtrer / pauser / dégonfler ?

Sans réponse quantifiée à ces questions, toute "contre-mesure" est du curve-fitting. **Phase 1 est non négociable et représente ~40% de l'effort de la mission.**

La campagne -1 (`2026-05-17-strategy-evolution-hmav3-1.md`) couvrait les 3 piliers (entry / SL / TP) à plat. La campagne -2 (`2026-05-17-strategy-evolution-hmav3-2-exit.md`) s'est concentrée sur la sortie. **Cette campagne -3 est verticale sur un phénomène** : les clusters de SL. Le périmètre des leviers est large (tout est autorisé : entry filter, SL placement, exit, sizing, cooldown, blackout dynamique), mais **toutes les hypothèses doivent dériver d'une observation Phase 1 sur les clusters**.

---

## 🧭 Cadre d'analyse — phénomène d'abord, leviers ensuite

### Étape 1 — définir "cluster de SL" quantitativement

Au minimum **deux définitions** à tester en parallèle dans Phase 1 (la "bonne" définition est celle qui sépare le mieux les périodes coûteuses des périodes normales) :

| Définition | Formule | Notes |
|------------|---------|-------|
| **D1 — Run de SL** | Suite d'au moins 3 trades consécutifs en SL (sans aucun gain intercalé) | Définition stricte, facile à détecter en live. |
| **D2 — Densité de SL** | ≥ K SL dans une fenêtre glissante de N bars (ex. K=3, N=20) | Capture les clusters avec micro-gagnants intercalés. Demande de tuner K et N. |
| **D3 — DD-burst** *(optionnel)* | DD intra-session qui dépasse Z $ en moins de M bars | Définition orientée P&L, agnostique du nombre de trades. |

**Phase 1 doit choisir** la définition retenue pour le reste de la mission, en argumentant chiffres à l'appui (combien de clusters détectés, % du DD total couvert, contraste signal/bruit).

### Étape 2 — leviers possibles (ouverts, Phase 1 priorise)

| Famille | Mécanisme | Exemples d'hypothèses |
|---------|-----------|-----------------------|
| **R — Régime** | Détecter un état marché "chop" et **bloquer / décaler** les entrées | Filtre canal HMA narrow + slope flat ; filtre range/ATR ratio ; filtre MFI plat ; filtre oscillateur dans une bande ; blackout dynamique session-aware. |
| **C — Consécutif** | Réagir **après K SL consécutifs** (réactif, post-événement) | Cooldown N bars après K SL ; skip jusqu'à fin de session après K SL ; reset après 1 gain. |
| **S — Signal** | Renforcer / durcir la condition d'entrée si signature suspecte | Exiger une confirmation MFI / delta / cloud supplémentaire ; rehausser le seuil oscillateur ; filtrer les setups dans la 1ʳᵉ ou la dernière bar de la fenêtre d'entrée si la signature de cluster s'y concentre. |
| **X — Exit** | Sortir plus vite si l'entrée présente la signature cluster | Réduire le `max_sl_points` dans le régime détecté ; sortie défensive si MAE > X R en moins de Y bars ; couper si canal flippe contre nous rapidement. |
| **Z — Sizing** | Dégonfler après K SL consécutifs ou en régime détecté | Risk_per_trade × 0.5 après 2 SL, restauré après 1 gain ; sizing fonction du DD intra-jour. |
| **L — SL placement** | Replacer le SL différemment quand la signature cluster est présente | SL basé sur ATR au lieu de HW-lookaround dans le régime ; SL minimum élargi ; SL minimum réduit (cut-and-run). |

**Phase 1 priorise** : à partir des corrélations observées, sélectionne **les 2-4 familles les plus probablement actionnables** et produit 1-3 hypothèses par famille retenue, dans la limite de **5 à 9 hypothèses au total**. Les autres familles sont notées dans `OBSERVATIONS.md` comme "non retenues pour ce cycle".

**Garde-fou** : pas plus de **3 hypothèses par famille**. Si tu produis 8 hypothèses de famille R sans toucher aux autres, tu fais du sur-ajustement à un type de filtre — autoréfléchis et redistribue.

**Pour CHAQUE hypothèse**, tu dois préciser :
- **Source obs.** : quelle observation Phase 1 la motive (ex. "obs-R.2 : canal width médian dans cluster = 0.18, vs 0.42 hors cluster, n=…")
- **Angle** : préventif (bloque avant le 1ᵉʳ SL du cluster) vs réactif (réagit après K SL).

---

## 🎯 Variables figées pour cette campagne

> Ne touche PAS à ces variables.

- **Stratégie à étudier** : `HMASSLOsciV3`

- **Nom de la stratégie duplicate à créer** : `HMASSLOsciV3LabSLClusterV1`
  - **UN SEUL FICHIER** : `src/strategies/hma_ssl_osci_v3_lab_sl_cluster_v1.py`.
  - **Hérite** de `HMASSLOsciV3`, ne la copie pas.
  - **Un paramètre configurable par hypothèse**, default = comportement V3 strict.
  - Chaque hypothèse vit dans son propre bloc `if p.get("<flag>"): …` — indépendante et désactivable.
  - Test #0 obligatoire : Lab avec tous les flags à default reproduit V3 exact sur les 2 presets de référence.
  - Ajouter une entrée dans `STRATEGY_WARMUP_BARS` (`backend/api.py`) avec la valeur de V3 (250) ou plus si une famille demande une fenêtre d'analyse plus longue (ex. ATR(100), régime sur 200 bars).

- **Presets gagnants de référence** :
  - `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json`
  - `scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json`
  - Le PnL et le DD de référence = valeurs publiées dans leurs `REPORT.md`. Phase 1 commence par un sanity-check au cent près.

- **Période** : reprend celle des presets.

- **Initial equity / contrats / risk** : ceux du preset. **Le sizing peut être modifié par une hypothèse de famille Z** (c'est même un levier valide ici), mais le sizing baseline reste celui du preset.

- **Auto-close** : **22:00 reference Brussels — FIXE, NE JAMAIS MODIFIER**.

- **Nombre d'hypothèses à tester** : **5 à 9, réparties sur ≥ 2 familles** identifiées en Phase 1. Toutes doivent provenir d'observations sourcées (Phase 1).

- **Budget simulation** : `~150-300` runs au total. Plus large que les missions -1 et -2 car le périmètre des familles est large : prévoir plus de A/B basiques + walk-forward.

- **Périmètre autorisé** : **tous les leviers** (entry filter, SL placement, exit, sizing, cooldown, dynamic blackout). **Le seul périmètre interdit** est de toucher au simulateur (`src/engine/simulator.py`) ou à `hma_ssl_osci_v3.py`.

---

## 🗂️ Organisation des fichiers (obligatoire)

```
src/strategies/
└─ hma_ssl_osci_v3_lab_sl_cluster_v1.py   ← NOUVELLE classe, hérite de HMASSLOsciV3
                                            Defaults = V3 strict.
                                            Ajouter dans STRATEGY_WARMUP_BARS.

scripts/goals/
└─ 2026-05-17_HMASSLOsciV3_sl_cluster_v1/  ← LA campagne (dossier dédié)
   ├─ README.md
   ├─ phase1_observation/                    ← diagnostic du phénomène — LE CŒUR de la mission
   │  ├─ 01_define_cluster.py                ← teste D1/D2/D3, choisit la définition retenue
   │  ├─ 02_statistical_baseline.py          ← runs test / simulation Bernoulli : clusters anormaux ?
   │  ├─ 03_regime_correlation.py            ← corrélations cluster ↔ régimes marché
   │  ├─ 04_signature_signal.py              ← signature des trades qui démarrent un cluster
   │  ├─ outputs/
   │  │  ├─ clusters_<preset>.csv            ← 1 ligne par cluster détecté + contexte
   │  │  ├─ trades_annotated_<preset>.csv    ← 1 ligne par trade + in_cluster flag + features régime
   │  │  └─ summary.json
   │  └─ OBSERVATIONS.md                     ← 10-25 hypothèses brutes, classées par famille
   ├─ phase2_hypotheses/                     ← UN sweep par hypothèse
   │  ├─ _shared.py
   │  ├─ 00_sanity_lab_equals_v3.py          ← OBLIGATOIRE
   │  ├─ 01_<family>_<name>.py               ← ex. 01_r_canal_width_filter.py
   │  ├─ 02_<family>_<name>.py
   │  ├─ … (5-9 sweeps au total)
   │  └─ logs/
   ├─ phase3_combinations/                   ← combos des hypothèses KEEP
   │  ├─ 01_pairs.py
   │  ├─ 02_triples.py
   │  └─ logs/
   ├─ winner_<vX>_MNQ.json                   ← preset gagnant V<N+1> par asset (si trouvé)
   ├─ winner_<vX>_MGC.json
   ├─ verify_winner.py
   ├─ HYPOTHESES.md                          ← tableau des 5-9 hypothèses + verdicts
   └─ REPORT.md
```

**Règles strictes** :

1. **La nouvelle stratégie doit hériter de `HMASSLOsciV3`**, surcharger uniquement ce qui change.
2. **Le sweep `00_sanity_lab_equals_v3.py` est obligatoire** : Lab(defaults) doit reproduire les baselines au cent près. Si non, arrêter et déboguer.
3. **Une hypothèse = un fichier `phase2_hypotheses/NN_<family>_<name>.py`** qui produit un tableau A/B (baseline vs ON) sur **chacun** des 2 presets.
4. **Toujours utiliser `scripts/goals/_shared/harness.py::run_backtest`** — jamais reconstruire les engine settings à la main.
5. Le `hma_ssl_osci_v3_lab_sl_cluster_v1.py` reste **dans `src/strategies/`** (auto-discovery). Le fichier original `hma_ssl_osci_v3.py` n'est **pas touché**.
6. **Préfixe `lab_<family>_`** sur tous les nouveaux paramètres (selon la famille : `lab_r_`, `lab_c_`, `lab_s_`, `lab_x_`, `lab_z_`, `lab_l_`), pour éviter toute collision avec V3 et signaler clairement la famille.

---

## 🧱 Contraintes techniques

1. **Ne pas modifier les stratégies existantes.** Toute évolution passe par la nouvelle classe Lab.
2. **UNE seule stratégie Lab pour TOUTES les hypothèses de la campagne.**
3. **Ne pas modifier le simulateur** (`src/engine/simulator.py`). Exploiter les hooks existants (cf. aide-mémoire en fin de mission). Si une hypothèse exige un comportement non supporté, la documenter dans `REPORT.md` comme "non testable sans refonte moteur" et ne pas la compter dans le quota.
4. **Une hypothèse à la fois par sweep.** Pas de comparaison "Lab avec 4 flags ON vs V3".
5. **Reporter PnL et DD en $** (pas en %).
6. **Métrique principale** : delta de **ratio Profit/DD**. Métriques secondaires impératives pour cette campagne : Δnombre de SL, Δnombre de clusters détectés, Δavg-cluster-PnL, ΔWinRate, Δnombre de trades, Δexpectancy. Une hypothèse qui supprime 80% des clusters mais aussi 80% des trades n'est pas une victoire si l'expectancy par trade chute.
7. **Auto-close à 22:00** — non négociable.
8. **Defaults UI = source de vérité** (cf. `_shared/engine_settings.py`).
9. **Cohérence forward-only** : aucune hypothèse ne doit utiliser une information du futur (ex. "skip si dans les 10 prochains bars il y a 3 SL") — toutes les conditions doivent être évaluables **à la barre courante** avec uniquement l'historique passé.

---

## 🧪 UNE seule stratégie Lab, paramètres indépendants

Modèle attendu : **à la fin de la campagne, il existe UN SEUL fichier `src/strategies/hma_ssl_osci_v3_lab_sl_cluster_v1.py`** qui contient **tous les paramètres correspondant à toutes les hypothèses testées**, chacun indépendant et désactivable, avec default = comportement V3 d'origine.

### Pourquoi ?

- **Lecture du rapport simple** : un `HYPOTHESES.md`, un Lab, des verdicts. Pas N classes à fusionner.
- **Adoption sélective** : KEEP 3/6 → on active 3 flags dans le preset.
- **Indépendance garantie** : chaque hypothèse vit dans son propre bloc conditionnel.
- **Compatibilité ascendante** : Lab(defaults) ≡ V3 (vérifié par `00_sanity_lab_equals_v3.py`).

### Squelette type de `HMASSLOsciV3LabSLClusterV1`

```python
# src/strategies/hma_ssl_osci_v3_lab_sl_cluster_v1.py
from .hma_ssl_osci_v3 import HMASSLOsciV3
import pandas as pd
import numpy as np


class HMASSLOsciV3LabSLClusterV1(HMASSLOsciV3):
    """Bench de contre-mesures pour les chaînes de SL de HMASSLOsciV3.
    Tous les nouveaux paramètres ont un default qui reproduit le comportement
    V3 exact — la stratégie Lab sans aucun flag activé = V3 strict
    (vérifié par phase2_hypotheses/00_sanity_lab_equals_v3.py).

    Conventions de nommage des flags :
      lab_r_*  → famille Régime (détection de chop, filtre d'entrée)
      lab_c_*  → famille Consécutif (réaction post-événement)
      lab_s_*  → famille Signal (durcissement de l'entrée)
      lab_x_*  → famille eXit (sortie défensive)
      lab_z_*  → famille siZing (dégonflage dynamique)
      lab_l_*  → famille SL pLacement (replacement du SL)
    """

    name = "HMASSLOsciV3LabSLClusterV1"

    default_params = {
        **HMASSLOsciV3.default_params,
        # === Famille R — Régime (à remplir selon les hypothèses Phase 1) ====
        # ex. filtre canal HMA narrow + slope flat
        "lab_r_canal_min_width_pct": 0.0,         # 0 = inactif
        "lab_r_canal_max_slope_abs": 0.0,         # 0 = inactif
        # === Famille C — Consécutif =========================================
        # ex. cooldown N bars après K SL consécutifs
        "lab_c_cooldown_after_k_sl_k": 0,         # 0 = inactif
        "lab_c_cooldown_after_k_sl_bars": 0,      # 0 = inactif
        # === Famille S — Signal =============================================
        # ex. exiger un seuil oscillateur plus strict
        "lab_s_require_sig_extreme": 0.0,         # 0 = inactif
        # === Famille X — Exit défensif ======================================
        "lab_x_early_kill_mae_r": 0.0,            # 0 = inactif
        # === Famille Z — Sizing dynamique ===================================
        "lab_z_size_decay_after_k_sl_k": 0,       # 0 = inactif
        "lab_z_size_decay_factor": 1.0,           # 1 = inactif
        # === Famille L — SL placement =======================================
        "lab_l_sl_atr_mult_in_regime": 0.0,       # 0 = inactif
    }

    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "lab_r_canal_min_width_pct":    [0.0, 0.10, 0.15, 0.20, 0.30],
        "lab_r_canal_max_slope_abs":    [0.0, 0.005, 0.01, 0.02],
        "lab_c_cooldown_after_k_sl_k":  [0, 2, 3, 4],
        "lab_c_cooldown_after_k_sl_bars": [0, 5, 10, 20, 50],
        "lab_s_require_sig_extreme":    [0.0, 25.0, 35.0, 45.0],
        "lab_x_early_kill_mae_r":       [0.0, 0.4, 0.6, 0.8],
        "lab_z_size_decay_after_k_sl_k": [0, 2, 3],
        "lab_z_size_decay_factor":      [1.0, 0.75, 0.5, 0.25],
        "lab_l_sl_atr_mult_in_regime":  [0.0, 1.0, 1.5, 2.0],
    }

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        result = super().generate_signals(data, p)

        # === Famille R ====================================================
        if float(p.get("lab_r_canal_min_width_pct", 0.0)) > 0:
            self._apply_r_canal_width_filter(result, data, p)
        if float(p.get("lab_r_canal_max_slope_abs", 0.0)) > 0:
            self._apply_r_canal_slope_filter(result, data, p)

        # === Famille C ====================================================
        if int(p.get("lab_c_cooldown_after_k_sl_k", 0)) > 0:
            # Note : nécessite l'historique des trades passés. Comme la stratégie
            # ne le voit pas directement, on **pré-calcule une série de blackouts
            # post-cluster** que le simulateur consommera via `entry` filter.
            # Plus simple : compter les SL dans la dernière fenêtre via une heuristique
            # basée sur les sorties simulées en pré-pass (cf. options d'implém. ci-bas).
            self._apply_c_cooldown_after_k_sl(result, data, p)

        # === Famille S ====================================================
        if float(p.get("lab_s_require_sig_extreme", 0.0)) > 0:
            self._apply_s_signal_hardening(result, data, p)

        # === Famille X ====================================================
        if float(p.get("lab_x_early_kill_mae_r", 0.0)) > 0:
            self._apply_x_early_kill(result, data, p)

        # === Famille L ====================================================
        if float(p.get("lab_l_sl_atr_mult_in_regime", 0.0)) > 0:
            self._apply_l_sl_atr(result, data, p)

        return result

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        s = super().get_simulator_settings(p)
        # === Famille Z (sizing dynamique) =================================
        # Le sizing est appliqué au niveau du simulateur via risk_per_trade.
        # Une hypothèse Z peut nécessiter d'injecter un risk_per_trade
        # variable bar-par-bar — vérifier si le simulateur supporte un
        # `size_multiplier` par signal d'entrée. Sinon, simuler en pré-pass
        # (cf. notes).
        return s

    # ----- helpers privés, un par hypothèse -----
    def _apply_r_canal_width_filter(self, result, data, p):
        # Cancel entries on bars where (canal_upper - canal_lower) / close < threshold
        pass

    def _apply_r_canal_slope_filter(self, result, data, p):
        pass

    def _apply_c_cooldown_after_k_sl(self, result, data, p):
        # Option 1 : pré-simuler les SL avec V3 pour repérer où ils tombent,
        # puis interdire les entrées dans les N bars suivants. Attention au
        # data-leakage : la simulation doit utiliser uniquement les SL qui se
        # sont déjà produits **avant** la bar courante.
        # Option 2 : tracker dans une boucle bar-par-bar (cf. les boucles V3),
        # plus propre car forward-only par construction.
        pass

    def _apply_s_signal_hardening(self, result, data, p):
        pass

    def _apply_x_early_kill(self, result, data, p):
        pass

    def _apply_l_sl_atr(self, result, data, p):
        pass
```

### Conventions de nommage

- **Préfixe `lab_<famille>_`** : `lab_r_`, `lab_c_`, `lab_s_`, `lab_x_`, `lab_z_`, `lab_l_`.
- **Default = neutralité** : `False`, `0`, `0.0`, `1.0` (pour facteurs multiplicatifs). JAMAIS un default qui change le comportement V3.
- **Un helper privé `_apply_<famille>_<name>()` par hypothèse**.

### Conséquence sur les sweeps

```python
# phase2_hypotheses/01_r_canal_width_filter.py
PARAMS_OFF = {"lab_r_canal_min_width_pct": 0.0}    # = V3 strict
PARAMS_ON_VARIANTS = [
    {"lab_r_canal_min_width_pct": 0.10},
    {"lab_r_canal_min_width_pct": 0.15},
    {"lab_r_canal_min_width_pct": 0.20},
]
```

---

## 🛠️ Méthode obligatoire

### Phase 1 — Observation & caractérisation (LE CŒUR DE LA MISSION)

Cette phase est plus longue et plus structurée que dans les missions -1 et -2 parce qu'on ne sait pas a priori si le phénomène mérite d'être traité.

#### Étape 1.0 — Sanity replay

Replay déterministe des 2 presets de référence. PnL doit matcher les rapports publiés à 1 cent près. Si raté → harness mal configuré, débugue avant tout.

#### Étape 1.1 — Définir le cluster (`01_define_cluster.py`)

Pour chacune des 3 définitions (D1, D2, D3, voir cadre d'analyse) :
- Détecter tous les clusters sur les 2 presets.
- Mesurer : **nombre de clusters**, **% de tous les SL contenus dans un cluster**, **% du DD total imputable aux clusters**, **PnL moyen d'un cluster**, **distribution de la longueur des clusters**.
- **Choisir la définition retenue** pour la suite, en justifiant chiffres à l'appui.

#### Étape 1.2 — Baseline statistique (`02_statistical_baseline.py`)

Question : le nombre de clusters observé est-il anormalement élevé vs un processus aléatoire avec le WR observé ?

- Calculer le **WR global** (= P(gain) par trade) et la **distribution observée des runs de SL**.
- Simuler **N=10 000 séquences** de Bernoulli(WR) de même longueur que la séquence réelle, et compter la distribution des runs simulés.
- **Comparer** : si la fréquence observée de runs ≥ K est dans le 95ᵉ centile de la simulation → corrélation temporelle réelle, ça vaut le coup de traiter. Si dans la médiane → le phénomène est juste la conséquence d'un WR < 1 + nombre de trades. **Dans ce cas, la mission peut conclure "phénomène non actionnable au niveau micro" et se rabattre sur les leviers de sizing / DD (famille Z) plutôt que de filtrage.**

Documente ce résultat dans `REPORT.md § Cadrage` — c'est l'angle d'attaque.

#### Étape 1.3 — Corrélations cluster ↔ régime (`03_regime_correlation.py`)

Pour chaque trade, calculer un panel de features de régime :
- `canal_width_pct = (canal_upper - canal_lower) / close * 100`
- `canal_slope_5b = |canal_mid[i] - canal_mid[i-5]| / canal_mid[i-5]`
- `atr_14`, `atr_50`, `atr_ratio = atr_14 / atr_50`
- `range_ratio = (high - low) / atr_14`
- `mfi_abs`, `mfi_change`, `osc_value`, `osc_abs`
- `hour`, `session` (Asia / UK / US)
- `bars_since_last_sl`, `consecutive_sl_so_far` (purement passé)

Bucketiser **trades dans cluster** vs **trades hors cluster** :
- Distribution de chaque feature dans les deux populations.
- **Test de Kolmogorov-Smirnov** ou simple comparaison médianes pour repérer les features les plus discriminantes.
- Heatmap : pour chaque feature continue, quintile vs cluster-rate observé.

#### Étape 1.4 — Signature du trade déclencheur (`04_signature_signal.py`)

Pour chaque cluster, regarder spécifiquement le **trade qui ouvre le cluster** (1er SL d'une série) :
- A-t-il une signature différente du trade SL "isolé" ?
- Quels filtres V3 étaient OFF / ON ? Quelle valeur prenait `max_candle_pct`, l'oscillateur, le delta, le cloud à son entrée ?
- À quel moment de la fenêtre d'entrée a-t-il été pris (1ʳᵉ bar du setup vs Nᵉ bar) ?

But : repérer si une condition d'entrée spécifique précède systématiquement les clusters.

#### Étape 1.5 — Construire `OBSERVATIONS.md`

Structure obligatoire — une section par famille (R / C / S / X / Z / L), winners et losers traités symétriquement :

```markdown
# OBSERVATIONS.md

## 0. Caractérisation du phénomène
- Définition retenue : D2 (≥3 SL dans 20 bars)
- Stats MNQ_v5 : N clusters = …, % du DD imputable = …, longueur médiane = …
- Stats MGC_v3 : …
- Test Bernoulli : clusters observés au 92ᵉ centile (MNQ) / 88ᵉ (MGC) → phénomène réel mais modéré.

## R. Famille Régime
### R.preventif — corrélations marché → cluster
- obs-R.1 : "63% des clusters démarrent quand canal_width_pct < 0.15 (médiane hors cluster = 0.32, n=…)"
  → hypothèse H-R.1 : filtre lab_r_canal_min_width_pct = 0.15
- obs-R.2 : "78% des clusters démarrent quand |canal_slope_5b| < 0.005"
  → hypothèse H-R.2 : filtre lab_r_canal_max_slope_abs
- …

## C. Famille Consécutif
- obs-C.1 : "après 2 SL consécutifs, P(SL_suivant) = 0.62 vs P_baseline = 0.42 → momentum négatif réel"
  → hypothèse H-C.1 : cooldown 10 bars après 2 SL consécutifs
- …

## S. Famille Signal
- …

## X. Famille Exit
- …

## Z. Famille Sizing
- …

## L. Famille SL placement
- …

## Hypothèses retenues pour Phase 2
| # | Famille | Hypothèse | Source | Estim. effort |
|--:|---------|-----------|--------|---------------|
| 1 | R | canal_width filter | obs-R.1 | A/B + sweep 3 valeurs |
| 2 | C | cooldown 10b après 2 SL | obs-C.1 | A/B + sweep K∈{2,3}, bars∈{10,20} |
| … | … | … | … | … |
```

Top **5 à 9 hypothèses retenues** selon :
- cross-preset stability,
- magnitude de l'effet observé,
- n suffisant,
- diversité des familles (≥ 2 familles).

> **Conformément aux retours utilisateur passés** : l'observation est nécessaire mais **insuffisante**. La phase 1 ne livre PAS d'insight final. Elle livre des hypothèses **à tester en Phase 2**.

#### ⚠️ Anti-patterns Phase 1 spécifiques à cette campagne

- **Conclure "il y a un phénomène" sans test statistique** → l'étape 1.2 est obligatoire. Sans elle, les clusters peuvent être un artefact d'un WR<1.
- **Concentrer toutes les hypothèses sur une seule famille** → distribution sur au moins 2 familles. Si Phase 1 ne discrimine qu'une seule famille (cas possible), justifier explicitement pourquoi les autres ont été écartées avec chiffres à l'appui.
- **Confondre cause et corrélation** → "les clusters ont lieu quand canal_width est bas" ne veut pas dire "filtrer sur canal_width évite les clusters". La Phase 2 doit valider, pas supposer.
- **Ignorer le trade-off** → un filtre R qui supprime 70% des clusters mais aussi 60% des entrées tueuses du PnL global. Toujours mesurer Δnombre-de-trades en parallèle de ΔPnL.

### Phase 2 — Test empirique

Pour chaque hypothèse retenue, faire les 3 étapes :

#### Étape 2.a — Ajouter le paramètre dans `HMASSLOsciV3LabSLClusterV1`

Voir squelette ci-dessus. Default reproduit V3. Helper privé `_apply_<famille>_<name>()`. Aucune modif du simulateur ni de la classe V3.

#### Étape 2.b — Écrire `phase2_hypotheses/NN_<family>_<name>.py`

- Charge les 2 presets de référence.
- Pour chaque preset, lance OFF (default Lab = V3) et ON (hypothèse active).
- Sweep multi-valeurs pour les paramètres continus.
- Sortie en tableau étendu (cette campagne demande plus de métriques) :

  ```
  === Hypothesis: lab_r_canal_min_width_pct=0.15 ===
  Preset  | Base PnL | Base DD | ON PnL | ON DD | ΔPnL   | ΔDD   | ΔP/DD | ΔWR   | Δ#trades | Δ#SL  | Δ#clusters
  MNQ_v5  | $68,800  | $1,600  | …      | …     | +/-    | +/-   | +/-   | +/-   | +/-      | +/-   | +/-
  MGC_v3  | $44,711  | $2,378  | …      | …     | …      | …     | …     | …     | …        | …     | …
  ```

  Note les 3 nouvelles colonnes : Δ#SL, Δ#clusters (avec la définition retenue Phase 1), Δ#trades. Sans elles, on ne sait pas si l'hypothèse "marche pour la bonne raison".

#### Étape 2.c — Verdict de l'hypothèse

- **KEEP** si ΔP/DD positif sur les 2 presets, **ET** Δ#clusters négatif (sinon l'hypothèse marche mais pas pour la raison invoquée → suspect overfit).
- **REJECT** si ΔP/DD négatif sur les 2 presets, ou si Δ#clusters ≈ 0 (l'hypothèse ne traite pas le phénomène ciblé).
- **MIXED** si améliore un asset et dégrade l'autre, ou si réduit les clusters sur un asset mais pas l'autre.
- **WORKS_BUT_OFF_TARGET** *(nouveau verdict spécifique à cette campagne)* si ΔP/DD positif mais Δ#clusters ≈ 0 → l'hypothèse améliore le PnL pour une autre raison, ce n'est pas une mitigation de cluster. À documenter, à reverser dans une autre campagne, mais à ne pas inclure dans le winner V<N+1> de cette campagne (ce serait du sandbagging).

### Phase 3 — Combinaisons

1. Prendre les hypothèses **KEEP** et leurs valeurs sweet-spot. Tester les **paires** puis les **triples**.
2. Vérifier la non-redondance : si deux hypothèses R suppriment les mêmes clusters, leur combinaison n'apporte rien. La table de combinaison doit montrer **#clusters supprimés par chacune seule** vs **par la combo** — si la combo = max des deux (et non somme), c'est de la redondance.
3. Construire `winner_<vX>_<asset>.json` pour chaque asset où le combo bat la baseline.

### Phase 4 — Validation & risque

- **Walk-forward split 50/50** : ajuster les sweet-spots sur la 1ʳᵉ moitié, mesurer sur la 2nde. Une hypothèse robuste doit garder ΔP/DD > 0 sur la 2nde moitié.
- **Test sur une période adjacente** (1 mois avant ou après) si possible.
- **Test inversion** : pour les hypothèses de famille R (filtre régime), tester ce qui se passe **avec le filtre inversé** (= ne prendre QUE les trades dans le régime "cluster-prone"). Si l'inversion donne aussi un mauvais résultat, le régime est juste "moins bon" pour tout. Si l'inversion donne un résultat catastrophique, le régime est vraiment toxique et l'hypothèse est solide.

---

## 📦 Livrables obligatoires

### 1. La nouvelle stratégie

`src/strategies/hma_ssl_osci_v3_lab_sl_cluster_v1.py` qui :
- Hérite de `HMASSLOsciV3`.
- Ajoute les nouveaux paramètres avec defaults = V3 strict.
- `00_sanity_lab_equals_v3.py` passe au cent près sur les 2 presets.
- Entrée correspondante dans `STRATEGY_WARMUP_BARS`.

### 2. Tableau de verdicts (`HYPOTHESES.md`)

Format obligatoire :

```markdown
| # | Famille | Angle | Hypothèse | Param ajouté | Source obs. | Verdict | ΔPnL$ MNQ | ΔPnL$ MGC | ΔP/DD | Δ#clusters | Cross-preset | Note |
|--:|:-------:|:-----:|-----------|--------------|-------------|---------|----------:|----------:|------:|-----------:|--------------|------|
| 1 | R | préventif | Filtre canal_width ≥ 0.15 | `lab_r_canal_min_width_pct=0.15` | obs-R.1 | KEEP | +$X | +$X | +X.XX | −X | 2/2 ✓ | … |
| 2 | C | réactif | Cooldown 10 bars après 2 SL | `lab_c_cooldown_after_k_sl_k=2`, `..._bars=10` | obs-C.1 | … | … | … | … | … | … | … |
| … | … | … | … | … | … | … | … | … | … | … | … | … |
```

**Quotas obligatoires** :
- ≥ 2 familles représentées dans la colonne Famille.
- ≥ 1 hypothèse "préventif" et ≥ 1 "réactif" dans la colonne Angle.
- Δ#clusters est **obligatoire** pour chaque ligne — c'est la métrique-clé de la mission.

### 3. Preset(s) JSON V<N+1>

Pour chaque asset où le combo final bat la baseline :
- `winner_<vX>_<asset>.json` (incrémenter le suffixe par rapport au dernier existant dans `scripts/goals/`).
- Format UI (`_shared/preset.py::build_preset` + `write_preset`).
- `strategyName` = `"HMASSLOsciV3LabSLClusterV1"`.
- Insertion auto dans `data/presets.json`.

### 4. Script de vérification (`verify_winner.py`)

Rejoue chaque winner V<N+1> et affiche `✅ MATCH` ou `❌ DIFF`.

### 5. Rapport markdown (`REPORT.md`)

Sections obligatoires :

1. **Cadrage** — période, 2 presets de référence, métriques de baseline, **observation initiale (description quantitative du phénomène)**, **résultat du test statistique Phase 1.2** (le phénomène est-il anormal vs random ?).
2. **Phase 1 — caractérisation** — définition retenue, table de corrélations cluster ↔ régime, signature du trade déclencheur, lien vers `OBSERVATIONS.md`. **Section la plus longue du rapport.**
3. **Phase 2 — A/B tests** — pour chaque hypothèse : mécanisme + tableau étendu + verdict.
4. **Phase 3 — combinaison gagnante** — combo final + delta vs baselines + non-redondance.
5. **Phase 4 — validation walk-forward** — résultats par fold + test inversion régime.
6. **Limites & risques** — overfit, sample size de clusters (souvent N petit), dépendance à un contrat, robustesse à un changement de régime.
7. **Pistes pour itération suivante** — hypothèses MIXED, familles écartées Phase 1, hypothèses non-testables (refonte moteur), candidates `WORKS_BUT_OFF_TARGET` à reverser dans une autre campagne.
8. **Reproduction** — 3 lignes (run_analysis, sweeps, verify).

### 6. Logs des sweeps

Chaque sweep : `… | tee logs/<nom>.log`.

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :

1. ✅ **Sanity test passé** : `00_sanity_lab_equals_v3.py` reproduit les baselines au cent près.
2. ✅ **Phase 1 livre une caractérisation chiffrée du phénomène** (définition retenue + test statistique + corrélations + signature) — pas juste une intuition.
3. ✅ **Entre 5 et 9 hypothèses testées**, réparties sur **≥ 2 familles** (R / C / S / X / Z / L).
4. ✅ **≥ 1 hypothèse préventive ET ≥ 1 hypothèse réactive** (colonne Angle dans `HYPOTHESES.md`).
5. ✅ **Δ#clusters reporté pour chaque hypothèse** (métrique-clé de la mission).
6. ✅ **Chaque hypothèse a un verdict** KEEP / REJECT / MIXED / WORKS_BUT_OFF_TARGET avec chiffres.
7. ✅ **Au moins 1 winner V<N+1>** existe pour ≥ 1 asset (sinon le rapport explique pourquoi aucune combinaison ne bat les baselines).
8. ✅ `verify_winner.py` affiche `✅ MATCH` pour chaque winner.
9. ✅ **UN SEUL fichier `hma_ssl_osci_v3_lab_sl_cluster_v1.py`** existe, hérite de `HMASSLOsciV3`, ajoute UN paramètre configurable par hypothèse (default = V3 strict), et n'a PAS modifié `hma_ssl_osci_v3.py`.
10. ✅ Chaque hypothèse correspond à un **bloc indépendant et désactivable** dans le Lab.
11. ✅ **Le simulateur n'a pas été modifié** (`src/engine/simulator.py` inchangé).
12. ✅ **Aucune hypothèse n'utilise d'information future** (forward-only).
13. ✅ `REPORT.md` couvre les 8 sections obligatoires.
14. ✅ Tous les fichiers de la campagne sont dans `scripts/goals/2026-05-17_HMASSLOsciV3_sl_cluster_v1/`.

**Cas spécial — le phénomène n'est pas anormal** : si Phase 1.2 conclut que les clusters observés sont compatibles avec un processus aléatoire au WR observé (= pas de momentum négatif réel), tu peux décider de :
- (a) Pivoter la mission sur la famille Z (sizing / DD-management) qui reste valide même sans corrélation temporelle, et tester 3-5 hypothèses Z. Considérer la mission comme un succès partiel ("phénomène non actionnable au niveau micro, mais DD réductible au niveau macro").
- (b) Arrêter la mission après Phase 1 avec un rapport "no-go" documenté. C'est un livrable valide — éviter de coder du curve-fitting pour atteindre un quota artificiel.

---

## 🧠 Bonnes pratiques

- **Pas de soft claims** : "ce serait intéressant", "à priori ça aiderait" — interdits. Toute affirmation = chiffre du backtest.
- **Une hypothèse par sweep**.
- **Toujours les MÊMES presets de référence** pour A/B.
- **Mesure delta en $** (pas en %).
- **Reproduire toute hypothèse à coup sûr**.
- **L'observation seule ne livre pas** : si Phase 1 produit 20 observations mais Phase 2 n'en teste que 3, c'est un échec.
- **Walk-forward même léger > rien**.
- **Documente les REJECT et les WORKS_BUT_OFF_TARGET** — autant d'insight qu'un KEEP.
- **Toujours mesurer Δ#trades en parallèle de ΔPnL** — une hypothèse qui élimine 60% des SL en éliminant 60% des entrées n'est pas une victoire.
- **Forward-only pour toute condition d'entrée** — ne jamais utiliser une info de bar future, même indirectement via la pré-simulation.

---

## ⚙️ Référence rapide

| Information | Fichier |
|-------------|---------|
| Stratégies + warmup | `backend/api.py` (`STRATEGIES`, `STRATEGY_WARMUP_BARS`) |
| Stratégie V3 d'origine (à hériter, ne pas modifier) | `src/strategies/hma_ssl_osci_v3.py` |
| Stratégie V2 (parent de V3, helpers `_compute_hma_canal_full`, etc.) | `src/strategies/hma_ssl_osci_v2.py` |
| Defaults UI | `frontend/src/api.ts` + `frontend/src/App.tsx` |
| Miroir Python UI defaults | `scripts/goals/_shared/engine_settings.py` |
| Harness backtest | `scripts/goals/_shared/harness.py` |
| Build/verify preset | `scripts/goals/_shared/preset.py` |
| Logique simulateur, exit modes, signaux consommables | `src/engine/simulator.py` |
| Specs contrats | `backend/api.py` (`CONTRACT_SPECS`) |
| Preset MNQ_v5 (baseline 1) | `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json` |
| Preset MGC_v3 (baseline 2) | `scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json` |
| Mission -1 (3 piliers) | `scripts/goals/2026-05-17-strategy-evolution-hmav3-1.md` |
| Mission -2 (exit focus) | `scripts/goals/2026-05-17-strategy-evolution-hmav3-2-exit.md` |

---

## ❌ Anti-patterns observés (à NE PAS reproduire)

- **Produire des hypothèses sans Phase 1.2** — pas de test statistique = pas de mission valide. Le phénomène pourrait être un artefact.
- **Mesurer ΔPnL sans Δ#clusters** — on ne sait alors pas si l'hypothèse traite le phénomène ciblé ou améliore par effet de bord.
- **Concentrer 8 hypothèses sur une seule famille** — la mission est diagnostique, donc multi-famille par construction.
- **Toucher au simulateur ou à la stratégie V3 originale** — composition uniquement.
- **Créer une classe Lab par hypothèse** — UN SEUL Lab cumulatif.
- **Tester sur 1 seul preset** — verdict cross-asset obligatoire.
- **Utiliser une info future** (ex. "pré-simuler tous les SL puis interdire les entrées dans les N bars autour") — forward-only strict.
- **Couvrir un cluster en supprimant 50% des trades** — Δ#trades > Δ#SL = victoire à la Pyrrhus.
- **Combiner les hypothèses sans tester chacune seule** — on ne peut pas attribuer l'effet.
- **Inclure une hypothèse WORKS_BUT_OFF_TARGET dans le winner V<N+1>** — ce serait revendiquer une mitigation de cluster qui n'en est pas une. Documenter, puis reverser dans une autre campagne.

---

## 📐 Format du `_shared.py` d'une campagne d'évolution

```python
"""Constants and helpers shared across hypothesis sweeps."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

BASELINES = {
    "MNQ_v5": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json",
    "MGC_v3": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json",
}

BASELINE_METRICS = {
    "MNQ_v5":  {"pnl": 68_800.0, "dd": 1_600.0},   # à confirmer depuis REPORT.md
    "MGC_v3":  {"pnl": 44_711.0, "dd": 2_378.0},   # à confirmer depuis REPORT.md
}

# Definition retenue Phase 1 (à mettre à jour après 01_define_cluster.py)
CLUSTER_DEF = {
    "type": "D2",          # ou D1 / D3
    "k_sl": 3,
    "window_bars": 20,
}


def load_preset(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def swap_strategy_name(preset: dict, new_name: str) -> dict:
    out = dict(preset)
    out["strategyName"] = new_name
    return out


def count_clusters(trades: list[dict], cluster_def: dict = CLUSTER_DEF) -> int:
    """Compte les clusters de SL selon la définition retenue Phase 1.
    À implémenter selon le type (D1 = run strict, D2 = densité, D3 = DD-burst)."""
    raise NotImplementedError


def print_ab_row_extended(label: str, base_pnl: float, base_dd: float,
                          on_pnl: float, on_dd: float,
                          base_n_sl: int, on_n_sl: int,
                          base_n_clusters: int, on_n_clusters: int,
                          base_n_trades: int, on_n_trades: int):
    dpnl = on_pnl - base_pnl
    ddd  = on_dd - base_dd
    base_pdd = base_pnl / base_dd if base_dd else 0
    on_pdd   = on_pnl / on_dd if on_dd else 0
    print(f"{label:<10s} | ${base_pnl:>9,.0f} | ${base_dd:>6,.0f} | "
          f"${on_pnl:>9,.0f} | ${on_dd:>6,.0f} | "
          f"{dpnl:+8,.0f} | {ddd:+7,.0f} | {(on_pdd-base_pdd):+5.2f} | "
          f"{on_n_trades-base_n_trades:+5d} | {on_n_sl-base_n_sl:+5d} | "
          f"{on_n_clusters-base_n_clusters:+5d}")
```

Squelette d'un sweep d'hypothèse :

```python
"""01_r_canal_width_filter — A/B test sur les 2 baselines."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize
from _shared import (
    BASELINES, BASELINE_METRICS, CLUSTER_DEF,
    load_preset, swap_strategy_name, count_clusters, print_ab_row_extended,
)

HYPOTHESIS = {
    "name": "lab_r_canal_min_width_pct",
    "param_key": "lab_r_canal_min_width_pct",
    "values_to_sweep": [0.10, 0.15, 0.20],
    "off_value": 0.0,
}

LAB_STRATEGY_NAME = "HMASSLOsciV3LabSLClusterV1"

# Pour chaque baseline :
#   - charger preset, swap strategyName → LAB_STRATEGY_NAME
#   - OFF run : flag=off_value (sanity, doit ~matcher la baseline)
#   - ON runs (sweep) : flag=v pour chaque v dans values_to_sweep
#   - extraire #trades, #SL, #clusters via count_clusters(result["trades"])
#   - print_ab_row_extended(...)
```

---

## 🧷 Aide-mémoire : hooks du simulateur exploitables sans modif moteur

(à confirmer dans `src/engine/simulator.py` au moment de l'implémentation)

| Hook (signal ou setting) | Levier exploitable |
|--------------------------|--------------------|
| `long_entries` / `short_entries` (Series bool) | Famille R, S, C : annuler les entrées qui matchent un filtre. |
| `sl_long` / `sl_short` (Series float) | Famille L : repositionner le SL conditionnellement. |
| `partial_close_long` / `partial_close_short` | Famille X : forcer une sortie défensive précoce. |
| `entry_price_long` / `entry_price_short` | Famille L, X. |
| `canal_lower`, `canal_upper`, `canal_green` | Familles R, X (régime, exit défensif). |
| `cooldown_bars` (int, par signal) | Famille C : ajuster dynamiquement le cooldown. Sinon, pré-calculer une série de blackouts d'entrée. |
| `canal_exit_mode` (settings) | Famille X. |
| `tp1_execution_mode` (settings) | Famille X. |
| `risk_per_trade` (engine settings) | Famille Z : sizing **global** uniquement (pas de modulation par-bar côté simulateur — pour un sizing dynamique, **annuler des entrées** est plus simple qu'ajuster la taille — discuter en Phase 1 si la famille Z est gardée). |

**Limite connue** : le simulateur ne supporte pas (à confirmer) un `size_multiplier` par signal d'entrée. Une hypothèse Z de "dégonflage après K SL" devra donc soit modifier le `risk_per_trade` du preset complet (= sweep statique, pas dynamique), soit transformer "demi-position" en "skip 1 entrée sur 2" (= proxy approximatif). Documenter cette limite dans `REPORT.md` § Limites si la famille Z est retenue.
