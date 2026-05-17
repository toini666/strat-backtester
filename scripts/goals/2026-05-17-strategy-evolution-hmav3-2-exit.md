# Goal — Évolution ciblée de HMASSLOsciV3 : mécanisme de prise de profit

Ton objectif est de **proposer ET valider expérimentalement** entre 5 et 9 améliorations concrètes du **mécanisme de sortie / prise de profit** de `HMASSLOsciV3`, en partant de ses deux presets gagnants actuels. Cette campagne est **mono-pilier** : tout porte sur la sortie (final exit + partial). On ne touche **PAS** aux entrées, ni aux SL, ni au sizing.

Chaque insight doit être adossé à un **A/B test réel** sur les backtests, pas à une simple observation.

Tu travailles en **trois phases obligatoires** :

1. **Observer** — disséquer les sorties actuelles (cross HMA rapide + HyperWave) trade par trade pour comprendre où le PnL se gagne / se perd entre le cross rapide et la HW confirmante, et générer des hypothèses d'alternatives.
2. **Tester** — dupliquer la stratégie en `HMASSLOsciV3LabExitV1` (nouvelle classe, defaults = comportement V3 exact) et **implémenter chaque hypothèse comme un paramètre configurable** dont le default reproduit le comportement original. Chaque hypothèse passe par un A/B sweep réel (OFF=baseline, ON=hypothèse active).
3. **Synthétiser** — pour chaque hypothèse : verdict KEEP / REJECT / MIXED + chiffres, et proposer une vraie config "winner V<N+1>" pour chaque asset où ça bat la baseline.

**Une hypothèse non testée ne compte pas.** Le livrable se mesure au nombre d'hypothèses adossées à un A/B sweep reproductible.

---

## 🎯 Contexte — pourquoi cette campagne

Actuellement, la sortie finale de V3 ("HMA rapide/SSL → HW") fonctionne en **deux temps** :

1. **Trigger 1 — Cross HMA rapide / SSL** : la HMA rapide croise la SSL baseline dans le sens contraire au trade → le signal de sortie est *armé*.
2. **Trigger 2 — HyperWave (HW) confirmante** : on attend ensuite un cross HW pour fermer effectivement la position.

**Hypothèse de travail du trader** : attendre la HW après le cross rapide n'est peut-être pas nécessaire et peut même rogner le PnL. Plusieurs alternatives méritent d'être testées empiriquement :

- Sortir directement au cross rapide, sans attendre la HW.
- Attendre la HW **mais ne sortir que si on est en gain** au moment où elle arrive (sinon laisser courir).
- Sortir au **changement de couleur du canal HMA** (canal_green flip).
- Combinaisons de partials sur cross rapide / HW / canal flip pour libérer du risque par étapes plutôt qu'en une seule sortie binaire.

La campagne -1 (`2026-05-17-strategy-evolution-hmav3-1.md`) couvrait les 3 piliers (entry / SL / TP) de manière équilibrée. **Cette campagne -2 est volontairement étroite et profonde** : un seul pilier (sortie), creusé au maximum.

---

## 🧭 Cadre d'analyse — un seul pilier, deux leviers

Toutes les hypothèses doivent toucher **uniquement la sortie**. Deux leviers possibles :

| Levier | Question | Type d'amélioration |
|--------|----------|---------------------|
| **EX. Trigger de sortie finale** | Quel événement déclenche la fermeture complète (ou la dernière fraction) de la position ? | Remplacer ou conditionner "cross rapide → HW" par un autre trigger (cross rapide seul, HW seul, canal flip, MFE-floor, time-based, hybride profit-only…). |
| **PT. Partial take-profit (étagement)** | Faut-il libérer une fraction de la position plus tôt, et sur quel signal ? | Activer / désactiver / régler `hw_partial_pct`, tester un partial sur cross rapide seul, sur HW seul, sur canal flip, sur MFE seuil, etc. |

**Pour CHAQUE levier**, tu dois analyser **les deux populations** :

- **Winners → amplification** : qu'est-ce qui caractérise les sorties qui ont laissé le plus de PnL sur la table ? Comment en garder davantage ?
- **Losers → exclusion** : qu'est-ce qui caractérise les sorties qui ont basculé d'un trade gagnant à un trade perdant (ou plat) ? Comment couper avant le retournement ?

**Quota sur les hypothèses retenues — qualité > quantité** :
- **2 à 5 hypothèses sur le levier EX** (trigger de sortie).
- **1 à 4 hypothèses sur le levier PT** (partial / étagement).
- **Total : 5 à 9 hypothèses au maximum**, pas plus.
- **≥ 1 hypothèse motivée par les losers** (cas où le trigger actuel sort trop tard / un trade gagnant rebascule perdant).

**Principe** : il vaut mieux **3-4 hypothèses solidement testées** (sweep multi-valeurs, walk-forward, verdict robuste) que **8 hypothèses bâclées**. Les idées non retenues vont dans `OBSERVATIONS.md` comme "candidates non testées ce cycle" — utiles pour l'itération suivante.

Exemple concret de répartition acceptable :
- 3 hypothèses levier EX (1 cross rapide seul, 1 cross rapide + condition profit-only, 1 canal flip)
- 2 hypothèses levier PT (1 partial sur cross rapide à 50%, 1 partial sur HW seul)
= 5 hypothèses, les deux leviers couverts, dont au moins 1 issue des losers.

Autre répartition acceptable :
- 4 hypothèses levier EX (cross rapide seul, HW-if-profit, canal flip, MFE-floor)
- 1 hypothèse levier PT (partial conditionnel sur MFE > X R)
= 5 hypothèses, profondeur maximale sur EX.

---

## 🎯 Variables figées pour cette campagne

> Ne touche PAS à ces variables. Elles sont la spécification de la mission.

- **Stratégie à étudier** : `HMASSLOsciV3`

- **Nom de la stratégie duplicate à créer** : `HMASSLOsciV3LabExitV1`
  - **UN SEUL FICHIER** : `src/strategies/hma_ssl_osci_v3_lab_exit_v1.py` — toutes les hypothèses de la campagne s'accumulent dans cette même classe.
  - **Hérite** de `HMASSLOsciV3`, ne la copie pas.
  - **Un paramètre configurable par hypothèse**, default = comportement V3 exact (incl. `final_exit_mode = "HMA rapide/SSL → HW"` et `hw_partial_pct = 0.0`).
  - Chaque hypothèse vit dans son propre bloc `if p.get("<flag>"): …` — indépendante et désactivable.
  - Test #0 obligatoire : Lab avec tous les flags à default reproduit V3 exact sur les 2 presets de référence.
  - Ajouter une entrée dans `STRATEGY_WARMUP_BARS` (`backend/api.py`) si nécessaire — V3 utilise 250, le Lab hérite donc de 250 par cohérence.

- **Presets gagnants de référence** *(les 2 baselines vs lesquelles chaque hypothèse est mesurée)* :
  - `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json`
  - `scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json`
  - Le PnL et le DD de référence sont leurs valeurs publiées dans leurs `REPORT.md`. La phase 1 commence par un sanity-check qui reproduit ces valeurs au cent près.

- **Période** : reprend celle des presets de référence (chaque preset = sa propre période).

- **Initial equity / contrats / risk** : ceux du preset (50 000 $ pour les deux winners actuels). On ne sweep PAS le sizing dans cette campagne.

- **Auto-close** : **22:00 reference Brussels — FIXE, NE JAMAIS MODIFIER**.

- **Nombre d'hypothèses à tester** : **5 à 9, dont 2-5 sur le levier EX et 1-4 sur le levier PT**. Toutes doivent provenir d'observations sourcées (Phase 1) — pas d'idées hors-sol.

- **Budget simulation** : `~100-200` runs au total. Une hypothèse simple = 1 A/B sur 2 presets = 4 runs. Une hypothèse à sweep param = 5-15 runs × 2 presets. Mieux vaut 4 hypothèses testées en profondeur que 8 en surface.

- **Périmètre interdit** : ne touche PAS aux paramètres d'entrée (filtres `hw_dir_on`, `hw_extreme_on`, `cloud_on`, `delta_on`, `entry_window_bars`, `max_candle_pct`…), au calcul du SL (`max_sl_points`, `tick_buffer`, `signal_candle_sl_on`), ni au sizing. Une hypothèse qui change le nombre d'entrées est hors-sujet pour cette campagne — flag-la "OUT OF SCOPE" dans `OBSERVATIONS.md` et ne la teste pas.

---

## 🗂️ Organisation des fichiers (obligatoire)

```
src/strategies/
└─ hma_ssl_osci_v3_lab_exit_v1.py           ← NOUVELLE classe, hérite de HMASSLOsciV3
                                              Defaults = V3 strict.
                                              Ajouter aussi son entrée dans
                                              STRATEGY_WARMUP_BARS (= 250).

scripts/goals/
└─ 2026-05-17_HMASSLOsciV3_exit_v1/         ← LA campagne (dossier dédié)
   ├─ README.md                              ← objectifs + statut + reproduction
   ├─ phase1_observation/                    ← analyse trade-par-trade des sorties
   │  ├─ run_analysis.py
   │  ├─ outputs/
   │  │  ├─ exits_<preset>.csv               ← 1 ligne par trade fermé + contexte sortie
   │  │  ├─ exits_ALL.csv                    ← cumul des 2 presets
   │  │  └─ summary.json                     ← aggregates par trigger, MFE bucket, etc.
   │  └─ OBSERVATIONS.md                     ← 10-20 hypothèses brutes, classées EX / PT
   ├─ phase2_hypotheses/                     ← UN sweep par hypothèse
   │  ├─ _shared.py                          ← BASELINES dict, helpers de comparaison
   │  ├─ 00_sanity_lab_equals_v3.py          ← OBLIGATOIRE : Lab(defaults) == V3 ✓
   │  ├─ 01_<hypothesis_name>.py             ← ex. 01_ex_fast_cross_only.py
   │  ├─ 02_<hypothesis_name>.py
   │  ├─ … (5-9 sweeps au total)
   │  └─ logs/                               ← un .log par sweep
   ├─ phase3_combinations/                   ← combos des hypothèses KEEP
   │  ├─ 01_pairs.py
   │  ├─ 02_triples.py
   │  └─ logs/
   ├─ winner_v6_MNQ.json                     ← preset gagnant V<N+1> par asset (si trouvé)
   ├─ winner_v4_MGC.json
   ├─ verify_winner.py                       ← rejoue chaque winner V<N+1>
   ├─ HYPOTHESES.md                          ← tableau des 5-9 hypothèses + verdicts
   └─ REPORT.md                              ← rapport final
```

**Règles strictes** :
1. **La nouvelle stratégie doit hériter de `HMASSLOsciV3`**, surcharger uniquement ce qui change, et conserver tous les paramètres de l'originale identiques par défaut.
2. **Le sweep `00_sanity_lab_equals_v3.py` est obligatoire** : il rejoue les 2 baselines avec `HMASSLOsciV3LabExitV1` + tous les nouveaux flags désactivés et **doit** retrouver le PnL/DD exact des winners originaux (à 1 cent près). Si non, la stratégie Lab est cassée — arrêter et déboguer avant tout le reste.
3. **Une hypothèse = un fichier `phase2_hypotheses/NN_<name>.py`** qui produit un tableau A/B (baseline vs ON) sur **chacun** des 2 presets de référence. Chaque sweep redirige son output vers `logs/`.
4. **Toujours utiliser `scripts/goals/_shared/harness.py::run_backtest`** — jamais reconstruire les engine settings à la main.
5. Le `hma_ssl_osci_v3_lab_exit_v1.py` reste **dans `src/strategies/`** (le mécanisme d'auto-discovery l'enregistre automatiquement). Le fichier original `hma_ssl_osci_v3.py` n'est **pas touché**.
6. **Préfixe `lab_exit_` ou `lab_pt_`** sur tous les nouveaux paramètres (selon le levier), pour éviter toute collision avec les paramètres V3 et signaler clairement leur appartenance au Lab.

---

## 🧱 Contraintes techniques

1. **Ne pas modifier les stratégies existantes.** Toute évolution passe par la nouvelle classe `HMASSLOsciV3LabExitV1` qui hérite de `HMASSLOsciV3`.
2. **UNE seule stratégie Lab pour TOUTES les hypothèses de la campagne.** Pas N versions de la stratégie.
3. **Ne pas modifier le simulateur** (`src/engine/simulator.py`). Le simulateur supporte déjà beaucoup de modes via les signaux que la stratégie produit (`canal_exit_mode`, `partial_close_long/short`, `entry_price_long/short`, `canal_green`, `hma_flip_up/down`, `ssl_baseline`, etc.) — exploiter ces hooks plutôt que de toucher au moteur. Si une hypothèse exige vraiment un comportement non supporté, la documenter dans `REPORT.md` comme "non testable sans refonte moteur — proposition pour itération ultérieure" et ne pas la compter dans le quota.
4. **Une hypothèse à la fois par sweep.** Pas de comparaison "Lab avec 4 flags ON vs V3". Toujours ON / OFF d'UN flag, sur les MÊMES presets de référence.
5. **Reporter PnL et DD en $** (pas en %), pour comparer directement aux objectifs des presets.
6. **Métrique de tri principale** : delta de **ratio Profit/DD**. Une hypothèse qui ajoute du PnL en ajoutant proportionnellement plus de DD ne KEEP pas. Métriques secondaires à toujours afficher : ΔPnL, ΔDD, ΔWinRate, Δavg-bars-in-trade, Δnombre-trades-clôturés-différemment.
7. **Auto-close à 22:00** — non négociable, jamais sweepé.
8. **Defaults UI = source de vérité** (cf. `_shared/engine_settings.py`).
9. **N'introduit PAS de nouvelle entrée.** Le nombre d'entrées (`long_entries`/`short_entries`) doit rester strictement identique entre OFF et ON. Les hypothèses ne peuvent modifier que ce qui se passe **après l'entrée**.

---

## 🧪 UNE seule stratégie Lab, paramètres indépendants

Modèle attendu : **à la fin de la campagne, il existe UN SEUL fichier `src/strategies/hma_ssl_osci_v3_lab_exit_v1.py`** qui contient **tous les paramètres correspondant à toutes les hypothèses testées**, chacun indépendant et désactivable, avec default = comportement V3 d'origine.

### Pourquoi ?

- **Lecture du rapport simple** : tu lis `HYPOTHESES.md`, tu vois les verdicts, tu choisis ce que tu veux activer. Pas besoin de jongler entre N classes.
- **Adoption sélective** : si tu valides 3 hypothèses sur 6, tu actives 3 flags dans le preset. Les 3 autres restent OFF mais le code existe pour les retester plus tard.
- **Indépendance garantie** : chaque hypothèse vit dans son propre bloc conditionnel `if p.get("<flag>", default): …` — pas de couplage entre elles.
- **Compatibilité ascendante** : `Lab` avec tous les flags par défaut produit exactement les trades de V3 (= test `00_sanity_lab_equals_v3.py`).

### Squelette type de `HMASSLOsciV3LabExitV1`

```python
# src/strategies/hma_ssl_osci_v3_lab_exit_v1.py
from .hma_ssl_osci_v3 import HMASSLOsciV3
import pandas as pd
import numpy as np


class HMASSLOsciV3LabExitV1(HMASSLOsciV3):
    """Bench d'évolutions du mécanisme de sortie de HMASSLOsciV3.
    Tous les nouveaux paramètres ont un default qui reproduit le comportement
    V3 exact — la stratégie Lab sans aucun flag activé = V3 strict
    (vérifié par phase2_hypotheses/00_sanity_lab_equals_v3.py).
    """

    name = "HMASSLOsciV3LabExitV1"

    default_params = {
        **HMASSLOsciV3.default_params,
        # === Levier EX (trigger de sortie finale) ============================
        # H1 — sortir directement au cross HMA rapide, sans attendre la HW
        "lab_exit_fast_cross_only": False,         # default V3 = False
        # H2 — attendre la HW mais ne sortir que si in-profit à ce moment
        "lab_exit_hw_only_if_profit": False,
        # H3 — sortir sur flip du canal HMA (canal_green change de couleur)
        "lab_exit_on_canal_flip": False,
        # H4 — exit "MFE floor" : sortir si MFE >X R puis retombe sous Y R
        "lab_exit_mfe_floor_r": 0.0,               # 0 = inactif
        # H5 — time-based : forcer la sortie au cross rapide après N bars
        "lab_exit_fast_cross_after_bars": 0,       # 0 = inactif
        # === Levier PT (partial take-profit) =================================
        # H6 — partial sur cross HMA rapide (avant le HW final exit)
        "lab_pt_on_fast_cross_pct": 0.0,           # 0 = inactif (V3 = pas de partial cross)
        # H7 — partial sur flip canal HMA
        "lab_pt_on_canal_flip_pct": 0.0,
        # H8 — partial sur MFE atteint (ex. ferme 50% si MFE>=1R)
        "lab_pt_on_mfe_r_pct": 0.0,
        "lab_pt_on_mfe_r_trigger": 0.0,
        # H9 — partial double-étage : 30% sur cross rapide, 30% sur HW, reste sur canal flip
        # (à implémenter via la combinaison des 3 flags ci-dessus en Phase 3, pas un flag dédié)
    }

    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "lab_exit_fast_cross_only":       [False, True],
        "lab_exit_hw_only_if_profit":     [False, True],
        "lab_exit_on_canal_flip":         [False, True],
        "lab_exit_mfe_floor_r":           [0.0, 0.3, 0.5, 0.8, 1.0],
        "lab_exit_fast_cross_after_bars": [0, 5, 10, 15, 20],
        "lab_pt_on_fast_cross_pct":       [0.0, 25.0, 50.0, 75.0],
        "lab_pt_on_canal_flip_pct":       [0.0, 25.0, 50.0],
        "lab_pt_on_mfe_r_pct":            [0.0, 25.0, 50.0],
        "lab_pt_on_mfe_r_trigger":        [0.0, 0.5, 1.0, 1.5],
    }

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        result = super().generate_signals(data, p)

        # === EX hypothèses qui modifient les séries d'exit/partial consommées
        # par le simulateur (canal_lower/upper/green, partial_close_long/short,
        # ssl_baseline, hma_flip_up/down). Implémenter chaque hypothèse comme
        # un helper privé _apply_<name>(result, data, p) ci-dessous.
        if p.get("lab_exit_fast_cross_only"):
            self._apply_exit_fast_cross_only(result, data, p)
        if p.get("lab_exit_hw_only_if_profit"):
            self._apply_exit_hw_only_if_profit(result, data, p)
        if p.get("lab_exit_on_canal_flip"):
            self._apply_exit_on_canal_flip(result, data, p)
        # … etc.

        # === PT hypothèses : produire/cumuler les séries
        # `partial_close_long`/`partial_close_short` consommées par le simulateur.
        if float(p.get("lab_pt_on_fast_cross_pct", 0.0)) > 0:
            self._apply_pt_on_fast_cross(result, data, p)
        if float(p.get("lab_pt_on_canal_flip_pct", 0.0)) > 0:
            self._apply_pt_on_canal_flip(result, data, p)
        if float(p.get("lab_pt_on_mfe_r_pct", 0.0)) > 0:
            self._apply_pt_on_mfe(result, data, p)

        return result

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        s = super().get_simulator_settings(p)
        # Ex : si une hypothèse impose un canal_exit_mode différent, le surcharger ici.
        # Ex : si une PT hypothèse fixe `tp1_partial_pct`, le surcharger ici plutôt
        # que de toucher hw_partial_pct (qui est un param V3).
        # … etc.
        return s

    # ----- helpers privés, un par hypothèse -----
    def _apply_exit_fast_cross_only(self, result, data, p):
        # Force le canal_exit_mode à fermer dès le cross HMA rapide / SSL,
        # sans attendre la HW. Implémentation possible :
        #   - garder canal_exit_mode = "v3_fast_hma_ssl" mais court-circuiter
        #     l'attente de HW en injectant directement partial_close_* à 100%
        #     sur la bar du cross rapide ; OU
        #   - construire une série custom et surcharger get_simulator_settings()
        #     pour que le simulateur utilise un canal_exit_mode adapté.
        pass

    def _apply_exit_hw_only_if_profit(self, result, data, p):
        # Conserve le comportement V3 (cross rapide → HW) mais filtre la sortie HW
        # à la bar de close : si Close < entry_price (long) ou > entry_price (short),
        # ne pas exécuter le partial_close (ré-injecter False dans la série).
        # Suppose que le simulateur consomme `partial_close_long/short` ;
        # pré-calculer ici la série filtrée à partir de hw_cross_over/under.
        pass

    def _apply_exit_on_canal_flip(self, result, data, p):
        # Inject une série `partial_close_long/short` qui passe à True quand
        # canal_green flip dans le sens contraire au trade ; combinée avec
        # un partial 100% via tp1_partial_pct=1.0, ça simule une sortie totale
        # sur flip canal sans toucher au simulateur.
        pass

    def _apply_pt_on_fast_cross(self, result, data, p):
        # Inject partial_close_long/short = True à la bar du cross HMA rapide,
        # avec tp1_partial_pct = lab_pt_on_fast_cross_pct/100.
        pass

    def _apply_pt_on_canal_flip(self, result, data, p):
        pass

    def _apply_pt_on_mfe(self, result, data, p):
        # Requiert un tracking du MFE bar-par-bar : c'est moins direct car le
        # simulateur connaît l'entry_price mais pas la stratégie. Solution :
        # implémenter la condition au niveau de la stratégie via partial_close_*
        # en utilisant `entry_price_long/short` produits par le simulateur
        # (cf. signaux supportés dans simulator.py).
        pass
```

### Conventions de nommage

- **Préfixe `lab_exit_`** pour les flags du levier EX (trigger de sortie finale).
- **Préfixe `lab_pt_`** pour les flags du levier PT (partial take-profit).
- **Default = neutralité** : `False`, `0`, `0.0`. JAMAIS un default qui change le comportement V3.
- **Un helper privé `_apply_<hyp_name>()` par hypothèse** — découpe le code par hypothèse, lisible, supprimable proprement si l'hypothèse est rejetée.

### Conséquence sur les sweeps

Les sweeps de Phase 2 lancent tous le **même Lab** avec un seul flag toggle entre OFF et ON :

```python
# phase2_hypotheses/01_ex_fast_cross_only.py
PARAMS_OFF = {"lab_exit_fast_cross_only": False}   # = V3 strict
PARAMS_ON  = {"lab_exit_fast_cross_only": True}    # H1 active
# … run baseline avec PARAMS_OFF puis avec PARAMS_ON
```

```python
# phase2_hypotheses/06_pt_on_fast_cross.py
PARAMS_OFF = {"lab_pt_on_fast_cross_pct": 0.0}     # = V3 strict
# Sweep multi-valeurs : 25 / 50 / 75 % pour trouver le sweet spot
PARAMS_ON_VARIANTS = [
    {"lab_pt_on_fast_cross_pct": 25.0},
    {"lab_pt_on_fast_cross_pct": 50.0},
    {"lab_pt_on_fast_cross_pct": 75.0},
]
```

Les combos de Phase 3 activent plusieurs flags en même temps sur le même Lab.

---

## 🛠️ Méthode obligatoire

### Phase 1 — Observation des sorties (génération d'hypothèses, winners ET losers)

Dans `phase1_observation/run_analysis.py` :

1. **Replay déterministe** des 2 presets de référence (sanity-check : PnL doit matcher les rapports publiés à 1 cent près). Si match raté → ton harness est mal configuré, débugue avant d'avancer.

2. **Capturer pour chaque trade fermé** :
   - `entry_time`, `exit_time`, `side`, `status`, `pnl`, `size`
   - `sl_dist_pts`, `entry_price`, `exit_price`
   - `bars_in_trade`, `bars_from_fast_cross_to_hw_exit` (combien de bars on a attendu la HW après le cross rapide ?)
   - `mfe_r`, `mae_r` (MFE/MAE en R, pour situer la trajectoire intra-trade)
   - `pnl_at_fast_cross` (PnL hypothétique si on était sorti au cross rapide), `pnl_at_hw_exit` (réel)
   - `delta_pnl_hw_minus_fast` (= pnl_at_hw_exit − pnl_at_fast_cross : positif = la HW a payé, négatif = la HW a coûté)
   - `canal_green_at_fast_cross`, `canal_green_at_exit` (état du canal au cross rapide et à la sortie effective)
   - `hour_of_exit`, `session`
   - **Au moins une simulation "shadow"** : pour chaque trade, calculer `pnl_si_sortie_au_fast_cross_seul`, `pnl_si_sortie_au_canal_flip`, et comparer au PnL réel.

3. **Bucketiser symétriquement sorties gagnantes ET sorties perdantes/dégradées** :
   - Distribution des trades où `delta_pnl_hw_minus_fast > 0` (= attendre la HW a payé)
   - Distribution des trades où `delta_pnl_hw_minus_fast < 0` (= attendre la HW a coûté)
   - Distribution des trades qui sont passés positifs puis sont revenus négatifs avant la sortie HW (= "give back" → exit défensif candidat)
   - Le but : repérer si la "value-add" de la HW est constante ou si elle est asymétrique (bénéfique dans certains régimes, néfaste dans d'autres).

4. **Construire `OBSERVATIONS.md` en 2 sections (= les 2 leviers EX / PT)**. Chaque section contient des sous-sections **Winners** et **Losers** :

   ```markdown
   # OBSERVATIONS.md

   ## EX. Trigger de sortie finale
   ### EX.W — issues des Winners (sorties qui ont laissé du PnL sur la table OU au contraire bien capturé)
   - obs-EX.W.1 : "sur MNQ_v5, attendre la HW après cross rapide ajoute en moyenne +$X par trade gagnant (n=Y), mais c'est concentré sur 28% des trades — les 72% restants auraient eu le même PnL en sortant au cross rapide"
     → hypothèse H1 : sortir directement au cross rapide (lab_exit_fast_cross_only=True)
   - …

   ### EX.L — issues des Losers (sorties qui ont coûté du PnL OU re-basculé négatif)
   - obs-EX.L.1 : "65% des sorties HW arrivent quand le trade est déjà repassé sous l'entry → on encaisse le re-give-back"
     → hypothèse H2 : sortir au cross rapide si on est en profit à ce moment, sinon attendre HW (lab_exit_hw_only_if_profit=True)
   - obs-EX.L.2 : "33% des trades ont vu canal_green flipper avant le HW exit ; ces trades finissent en moyenne −$Z vs +$W si on avait sorti au flip"
     → hypothèse H3 : sortir sur flip canal (lab_exit_on_canal_flip=True)
   - obs-EX.L.3 : "les trades dont le MFE a dépassé 1.5R puis est retombé sous 0.5R finissent en moyenne avec un PnL de … vs un PnL idéalisé de … s'ils étaient sortis au pic"
     → hypothèse H4 : exit MFE-floor (lab_exit_mfe_floor_r=0.5)
   - …

   ## PT. Partial take-profit
   ### PT.W — issues des Winners
   - obs-PT.W.1 : "les gros gagnants (>2R) passent quasi tous par un cross rapide intermédiaire → capturer 25% à ce moment fixerait du PnL sans rogner le tail"
     → hypothèse H6 : partial sur cross rapide (lab_pt_on_fast_cross_pct=25.0)
   - …

   ### PT.L — issues des Losers
   - obs-PT.L.1 : "47% des trades qui finissent SL ou flat avaient atteint MFE >= 1R à un moment → un partial sur MFE seuil aurait capturé +$X au total sans toucher aux winners purs"
     → hypothèse H8 : partial sur MFE atteint (lab_pt_on_mfe_r_pct=50.0, trigger=1.0)
   ```

5. **Top 5-9 hypothèses retenues** = celles avec :
   - cross-preset stability (signal va dans le même sens sur les 2 presets),
   - magnitude visible (delta de moyenne non noyé dans la variance),
   - n suffisant (caveat sample size si n<50 sur un preset),
   - couverture des deux leviers (min 2 hypothèses EX, min 1 hypothèse PT),
   - **au moins 1 hypothèse issue des losers** (filtre / exit défensif).

> **Conformément aux retours utilisateur passés** : l'observation est nécessaire mais **insuffisante**. La phase 1 ne livre PAS d'insight final. Elle livre des hypothèses **à tester en Phase 2**.

#### ⚠️ Anti-pattern Phase 1 — ne regarder que les sorties "réussies"

Si tu produis 6 hypothèses dont 6 viennent uniquement des trades où le HW exit a "bien fonctionné", **tu rates l'angle principal de la mission** : démontrer (ou réfuter) que l'attente HW peut coûter du PnL sur une fraction non négligeable des trades. Les trades où la HW a coûté sont **le cœur de cette campagne** — ne les sous-représente pas.

### Phase 2 — Test empirique (le cœur du travail)

> **Principe** : transformer chaque hypothèse en **un paramètre configurable** ajouté à `HMASSLOsciV3LabExitV1`. Tu codes le tweak directement dans la stratégie Lab, mais sous un flag dont le default reproduit le comportement V3 original. Le sweep d'hypothèse n'a alors qu'à toggler le flag OFF/ON.

Pour chaque hypothèse retenue, faire les 3 étapes :

#### Étape 2.a — Ajouter le paramètre dans `HMASSLOsciV3LabExitV1`

Voir squelette ci-dessus. Le default doit reproduire V3. Implémenter un helper privé `_apply_<name>()` qui modifie uniquement les séries consommées par le simulateur (`partial_close_long/short`, `canal_green`, `entry_price_long/short`, `ssl_baseline`, etc.). **Aucune modification du simulateur n'est autorisée.**

Si une hypothèse requiert plusieurs paramètres liés (ex. PT avec un % et un trigger MFE), ajouter 2 flags couplés mais documentés comme une seule hypothèse dans `HYPOTHESES.md`.

#### Étape 2.b — Écrire `phase2_hypotheses/NN_<name>.py`

Ce script doit :
- Charger les 2 presets de référence (`_shared.py::BASELINES`).
- Pour chaque preset, lancer la version **OFF** (= reproduction baseline avec Lab + default) et la version **ON** (= hypothèse active).
- Pour les hypothèses à paramètre continu (ex. `lab_exit_mfe_floor_r ∈ {0.3, 0.5, 0.8, 1.0}`), sweep multi-valeurs.
- Sortie en tableau format `_shared.py::print_ab_row` :

  ```
  === Hypothesis: lab_exit_fast_cross_only ===
  Preset       | Baseline PnL | Baseline DD | ON PnL    | ON DD   | ΔPnL    | ΔDD    | ΔP/DD | ΔWinRate | Δavg_bars
  MNQ_v5       | $68,800      | $1,600      | $XX,XXX   | $X,XXX  | +$X,XXX | -$XXX  | +X.XX | +X.X%    | -X.X
  MGC_v3       | $44,711      | $2,378      | $XX,XXX   | $X,XXX  | +/-$    | +/-$   | +/-   | +/-      | +/-
  ```

#### Étape 2.c — Verdict de l'hypothèse

- **KEEP** si ΔP/DD positif sur les **2 presets** (cross-asset robustesse exigée pour une campagne à 2 presets seulement) et négatif nulle part.
- **REJECT** si ΔP/DD négatif sur les 2 presets ou si le DD explose sur l'un.
- **MIXED** si améliore un asset et dégrade l'autre — noter pour les combos asset-spécifiques (le winner final pour cet asset peut quand même intégrer le flag).

**Important** : si une hypothèse change le **nombre de trades clôturés différemment** ou le **profil de sortie** (ex. raccourcit `avg_bars_in_trade` de 30%), le delta brut est attendu — ce qui compte c'est le delta du ratio P/DD et le profil (où on a coupé : les bons ou les mauvais trades ?). Toujours documenter ces deltas annexes.

### Phase 3 — Combinaisons

1. Prendre les hypothèses **KEEP** (ou **MIXED** sur un asset spécifique) et leurs valeurs sweet-spot. Tester les **paires** puis le **combo complet par asset**.
2. Attention à la cohérence : certaines hypothèses sont mutuellement exclusives (ex. H1 "fast_cross_only" et H2 "hw_only_if_profit" — l'une remplace la HW, l'autre la conditionne). Documenter les combinaisons valides dans `phase3_combinations/README.md`.
3. Pour chaque asset, comparer le combo final à la baseline.
4. Si le combo gagne sur ≥ 1 asset → **construire `winner_v<N+1>_<asset>.json`** et `verify_winner.py`.

### Phase 4 — Validation & risque

- **Walk-forward simple** : split la période de chaque preset en 2 (training / test). Re-fit les hypothèses KEEP sur la 1ère moitié, mesurer le delta sur la 2nde. Si une hypothèse dégrade sur la seconde moitié → la rétrograder en MIXED dans le REPORT.
- **Out-of-sample** : si possible, tester sur 1 mois adjacent au preset.
- **Sensibilité aux paramètres continus** : pour les sweep multi-valeurs (`lab_exit_mfe_floor_r`, `lab_pt_on_fast_cross_pct`), vérifier que le sweet spot n'est pas un pic isolé (overfit) mais un plateau (robuste).

---

## 📦 Livrables obligatoires

À la fin, fournis dans cet ordre :

### 1. La nouvelle stratégie

`src/strategies/hma_ssl_osci_v3_lab_exit_v1.py` qui :
- Hérite de `HMASSLOsciV3`.
- Ajoute les nouveaux paramètres avec defaults = comportement V3 strict.
- Le test `00_sanity_lab_equals_v3.py` doit passer (Lab(defaults) reproduit exactement V3 sur les 2 presets, au cent près).
- L'entrée correspondante existe dans `STRATEGY_WARMUP_BARS` (`backend/api.py`).

### 2. Tableau de verdicts (`HYPOTHESES.md`)

Format obligatoire — les colonnes **Levier** (EX trigger / PT partial) et **Angle** (W winners / L losers / W+L) sont **non négociables** : elles forcent la couverture des 2 leviers et la prise en compte des losers.

```markdown
| # | Levier | Angle | Hypothèse | Param ajouté | Source obs. | Verdict | Best ΔPnL$ MNQ | Best ΔPnL$ MGC | Best ΔP/DD | Cross-preset | Note |
|--:|:------:|:-----:|-----------|--------------|-------------|---------|---------------:|---------------:|-----------:|--------------|------|
| 1 | EX | W+L | Sortir au cross rapide seul, sans attendre HW | `lab_exit_fast_cross_only=True` | obs-EX.W.1 / EX.L.1 | KEEP | +$X | +$X | +X.XX | 2/2 ✓ | … |
| 2 | EX | L | HW only if in profit (sinon laisser courir) | `lab_exit_hw_only_if_profit=True` | obs-EX.L.1 | … | … | … | … | … | … |
| 3 | EX | L | Sortir sur flip canal HMA | `lab_exit_on_canal_flip=True` | obs-EX.L.2 | … | … | … | … | … | … |
| 4 | EX | W | Exit MFE-floor | `lab_exit_mfe_floor_r=0.5` | obs-EX.L.3 | … | … | … | … | … | … |
| 5 | PT | W | Partial 50% sur cross rapide | `lab_pt_on_fast_cross_pct=50.0` | obs-PT.W.1 | … | … | … | … | … | … |
| 6 | PT | L | Partial 50% sur MFE ≥1R | `lab_pt_on_mfe_r_pct=50.0`, `..._trigger=1.0` | obs-PT.L.1 | … | … | … | … | … | … |
```

Quota à respecter dans la colonne **Levier** : ≥ 2 lignes levier EX, ≥ 1 ligne levier PT.
Quota à respecter dans la colonne **Angle** : ≥ 1 ligne issue des losers (L ou W+L).

### 3. Preset(s) JSON V<N+1>

Pour chaque asset où le combo final bat la baseline :
- `winner_v6_MNQ.json` (ou `_v4_MGC.json` selon le N courant — vérifier le dernier suffixe existant dans `scripts/goals/`).
- Au format UI (utilise `_shared/preset.py::build_preset` + `write_preset`).
- Visible en tête des favoris UI (insertion auto dans `data/presets.json`).
- `strategyName` = `"HMASSLOsciV3LabExitV1"` (et non plus `HMASSLOsciV3`, puisque la classe diffère).

### 4. Script de vérification (`verify_winner.py`)

Rejoue chaque winner V<N+1> et affiche `✅ MATCH` ou `❌ DIFF`. Pas de match → ne pas déclarer le job fini.

### 5. Rapport markdown (`REPORT.md`)

Sections obligatoires, dans cet ordre :

1. **Cadrage** — période, 2 presets de référence, métriques de baseline, rappel de la mission (focus exit) (1 paragraphe).
2. **Phase 1 — observation** — 1 tableau résumé des sorties actuelles (combien de trades où HW a payé / coûté, magnitude), lien vers `OBSERVATIONS.md`.
3. **Phase 2 — A/B tests** — Pour chaque hypothèse testée :
   - Hypothèse en 1 ligne.
   - Mécanisme proposé en 2-3 lignes (quel signal modifié, comment).
   - Tableau A/B (cf. format ci-dessus).
   - **Verdict** : KEEP / REJECT / MIXED + justification chiffrée.
4. **Phase 3 — combinaison gagnante** — Combo final par asset + delta vs baselines + DD safe ?
5. **Phase 4 — validation walk-forward** — résultats par fold, hypothèses qui dégradent hors-fold.
6. **Limites & risques** — overfit, sample size, dépendance à un contrat, hypothèses non-testables (refonte moteur).
7. **Pistes pour itération suivante** — hypothèses MIXED à creuser, paramètres à sweep plus finement, candidates EX/PT non-retenues ce cycle.
8. **Reproduction** — 2-3 lignes (script `run_analysis.py`, sweeps `phase2_hypotheses/*.py`, `verify_winner.py`).

### 6. Logs des sweeps

Chaque sweep : `… | tee logs/<nom>.log`. Logs sont des artefacts d'audit.

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :

1. ✅ **Sanity test passé** : `00_sanity_lab_equals_v3.py` reproduit les baselines à 1 cent près sur les 2 presets, avec **TOUS les flags Lab à leur default** (= comportement V3 strict).
2. ✅ **Entre 5 et 9 hypothèses testées** (2-5 sur levier EX, 1-4 sur levier PT), chacune avec un A/B sweep réel.
3. ✅ **Couverture des 2 leviers** : ≥ 2 hypothèses levier EX, ≥ 1 hypothèse levier PT.
4. ✅ **Analyse symétrique winners/losers** : ≥ 1 hypothèse issue des losers (exit défensif / give-back évité) **explicitement marquée Angle=L ou W+L** dans `HYPOTHESES.md`.
5. ✅ **Chaque hypothèse a un verdict** KEEP / REJECT / MIXED dans `HYPOTHESES.md` adossé à des chiffres.
6. ✅ **Au moins 1 winner V<N+1>** existe pour ≥ 1 asset (sinon le rapport explique pourquoi aucune combinaison ne bat les baselines — c'est un résultat valide).
7. ✅ `verify_winner.py` affiche `✅ MATCH` pour chaque winner.
8. ✅ **UN SEUL fichier `hma_ssl_osci_v3_lab_exit_v1.py`** existe dans `src/strategies/`, **hérite** de `HMASSLOsciV3`, **ajoute UN paramètre configurable par hypothèse** (default = comportement V3 strict), et n'a PAS modifié `hma_ssl_osci_v3.py`.
9. ✅ Chaque hypothèse correspond à un **bloc indépendant et désactivable** dans le Lab (helper privé `_apply_<name>()` recommandé). On peut activer un sous-ensemble sans casser les autres.
10. ✅ **Le simulateur n'a pas été modifié** (`src/engine/simulator.py` inchangé).
11. ✅ **Aucune hypothèse ne change le nombre d'entrées** (les `long_entries`/`short_entries` produits sont strictement identiques à V3).
12. ✅ `REPORT.md` couvre les 8 sections obligatoires.
13. ✅ Tous les fichiers de la campagne sont dans `scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/`, rien à plat.

Si une hypothèse n'a pas pu être testée (limite moteur, complexité hors budget), la marquer **NOT TESTED** dans `HYPOTHESES.md` avec la raison — **ça ne compte PAS dans le quota des 5-9**.

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
- **Préfère exploiter les hooks existants du simulateur** (`partial_close_*`, `canal_green`, `entry_price_*`, `canal_exit_mode`) — toute hypothèse qui exige une modif moteur sort du périmètre de cette campagne.

---

## ⚙️ Référence rapide

| Information | Fichier |
|-------------|---------|
| Stratégies + warmup | `backend/api.py` (`STRATEGIES`, `STRATEGY_WARMUP_BARS`) |
| Stratégie V3 d'origine (à hériter, ne pas modifier) | `src/strategies/hma_ssl_osci_v3.py` |
| Stratégie V2 (parent de V3, à connaître pour les helpers `_compute_hma_canal_full`, etc.) | `src/strategies/hma_ssl_osci_v2.py` |
| Defaults UI | `frontend/src/api.ts` + `frontend/src/App.tsx` |
| Miroir Python UI defaults | `scripts/goals/_shared/engine_settings.py` |
| Harness backtest | `scripts/goals/_shared/harness.py` |
| Build/verify preset | `scripts/goals/_shared/preset.py` |
| Logique simulateur, exit modes, signaux consommables | `src/engine/simulator.py` (chercher `canal_exit_mode`, `partial_close_long/short`, `v3_fast_hma_ssl`, `v3_fixed_points`) |
| Specs contrats | `backend/api.py` (`CONTRACT_SPECS`) |
| Preset MNQ_v5 (baseline 1) | `scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json` |
| Preset MGC_v3 (baseline 2) | `scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json` |
| Mission -1 (3 piliers) — pour comparaison de format | `scripts/goals/2026-05-17-strategy-evolution-hmav3-1.md` |

---

## ❌ Anti-patterns observés (à NE PAS reproduire)

- **Produire 9 insights observés mais aucun A/B test** → c'est de l'analyse, pas de l'évolution stratégie.
- **N'analyser que les sorties qui ont "bien marché"** → la moitié du signal est ignorée. La mission est précisément d'objectiver si l'attente HW coûte du PnL sur une fraction des trades.
- **Toucher aux entrées ou au SL** sous prétexte qu'un sweep "marcherait mieux" → hors-périmètre, à isoler dans une autre campagne (ex. -3, -4…).
- **Proposer une "v6 future" sans la coder** → la duplicate strategy doit exister et le sanity test doit passer.
- **Tester sur 1 seul preset** → le verdict cross-asset est central ; les 2 presets sont obligatoires.
- **Sweep multi-paramètre sans baseline matching** → si la version OFF du sweep ne reproduit pas le winner d'origine, le delta mesure du bruit.
- **Compter une hypothèse non testée dans les 5-9** → seules les hypothèses avec un sweep + verdict comptent.
- **Combiner 5 hypothèses puis A/B le combo vs baseline** sans avoir A/B chaque hypothèse seule → on ne sait pas attribuer le delta.
- **Toucher au simulateur ou à la stratégie V3 originale** pour faire passer une hypothèse → utiliser uniquement de la composition via la nouvelle classe Lab et les hooks existants du simulateur.
- **Créer une classe Lab par hypothèse** → tout doit s'accumuler dans **UN SEUL `HMASSLOsciV3LabExitV1`** avec un paramètre toggleable par hypothèse.
- **Multiplier les hypothèses bâclées** (8-10 testées en surface) → mieux vaut 4-5 testées en profondeur (sweep multi-valeurs + walk-forward + combo). Quota max = 9 au total.
- **Couvrir un seul levier** (8 hypothèses EX, 0 PT, ou inversement) → la dualité EX/PT est obligatoire.

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
    "MNQ_v5": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json",
    "MGC_v3": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v3/winner_preset.json",
}

# Reference PnL/DD from the published REPORT.md of each baseline
# (à remplir au démarrage en lisant les rapports — sanity-check obligatoire)
BASELINE_METRICS = {
    "MNQ_v5":  {"pnl": 68_800.0, "dd": 1_600.0},   # à confirmer depuis REPORT.md
    "MGC_v3":  {"pnl": 44_711.0, "dd": 2_378.0},   # à confirmer depuis REPORT.md
}


def load_preset(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def swap_strategy_name(preset: dict, new_name: str) -> dict:
    """Return a copy of the preset with strategyName replaced (V3 → LabExitV1).
    Defaults Lab params are added so the run is unambiguously V3-equivalent
    when no hypothesis flag is overridden."""
    out = dict(preset)
    out["strategyName"] = new_name
    return out


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
"""01_ex_fast_cross_only — A/B test sur les 2 baselines."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize
from _shared import BASELINES, BASELINE_METRICS, load_preset, swap_strategy_name, print_ab_row

HYPOTHESIS = {
    "name": "lab_exit_fast_cross_only",
    "param_key": "lab_exit_fast_cross_only",
    "values_to_sweep": [True],          # boolean → 1 ON value
    "off_value": False,
}

LAB_STRATEGY_NAME = "HMASSLOsciV3LabExitV1"

# Pour chaque baseline :
#   - charger le preset, swap strategyName → LAB_STRATEGY_NAME
#   - OFF run : lancer avec flag=off_value (= sanity, doit ~matcher la baseline)
#   - ON run  : lancer avec flag=values_to_sweep[0]
#   - print_ab_row(label, base_pnl, base_dd, on_pnl, on_dd)
```

L'organisation par sweep = un seul fichier indépendant rerunable = audit facile.

---

## 🧷 Aide-mémoire : hooks du simulateur exploitables sans modif moteur

(à confirmer dans `src/engine/simulator.py` au moment de l'implémentation)

| Hook (signal produit par la stratégie) | Comportement déclenché côté simulateur |
|----------------------------------------|----------------------------------------|
| `partial_close_long` / `partial_close_short` (Series bool) | Ferme `tp1_partial_pct` (ou `tp2_partial_pct`) de la position au close de la bar, **uniquement** si la bar est in-profit pour les modes V3 (cf. `simulator.py` ligne ~1268). |
| `canal_lower`, `canal_upper`, `canal_green` | Drive les exits canal selon `canal_exit_mode`. |
| `hma_flip_up` / `hma_flip_down` | Drive les exits canal en mode `inversion_hma`. |
| `ssl_baseline` | Drive le TP2 close-cross. |
| `canal_exit_requires_arming` (bool) | Force le canal exit à n'agir qu'après avoir touché le côté profit du canal. |
| `entry_price_long` / `entry_price_short` (Series) | Override le prix d'entrée (utile si une hypothèse veut reprendre la position à un niveau précis). |
| `block_loss_canal_exit_before_tp1` (settings) | Bloque les exits canal perdants avant TP1. |
| `canal_exit_mode` (settings: `both_hma`, `break_hma`, `inversion_hma`, `v3_fast_hma_ssl`, `v3_fixed_points`) | Choisit le mode d'exit final. |
| `tp1_execution_mode` (`"touch"` ou `"bar_close_if_touched"`) | Affecte le timing du partial. |

**Ces hooks couvrent largement les hypothèses listées dans cette mission.** Si une idée nécessite un nouveau hook, c'est qu'elle est hors-périmètre — la documenter dans `REPORT.md` § Limites comme "candidate pour campagne moteur".
