# Rapport final — Optimisation HMASSLOsciV3 sur MGC (v2)

**Période** : 2025-01-06 → 2026-05-15 (~17 mois — historique multi-contrats jusqu'à M26)
**Stratégie** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole** : MGC — micro-futures Gold
**Point de départ** : preset gagnant de la campagne v1 (`2026-05-15_HMASSLOsciV3_MGC`)
**Consigne** : repartir de la v1 sans les blackouts ajoutés (ne garder que `22:00-23:59`, le UI default) puis ré-optimiser les paramètres.

---

## 1. Résultat — **✅ les deux objectifs atteints**

| Objectif | Cible | Atteint | Statut |
|----------|-------|---------|--------|
| Profit net | > 30 000 $ | **44 711 $** | ✅ +$14 711 (1.49 × goal) |
| Max drawdown | < 2 500 $ | **2 378 $** | ✅ -$122 |

Métriques détaillées :

| Métrique | Valeur |
|----------|--------|
| Net PnL | **44 711 $** |
| Max drawdown $ | **2 378 $** |
| Profit factor | **1.56** |
| Win rate | 55.9 % |
| Trades actifs | 1 142 |
| Avg win / Avg loss | +196 $ / –159 $ |
| Reward:Risk | 1.23 |
| **Profit / DD ratio** | **18.80** |
| Total return | 89.4 % |

Vs la v1 (même stratégie, même symbole, même période) :

| | v1 (winner) | **v2 (winner)** | Δ |
|-|------|------|---|
| PnL | $32 821 | **$44 711** | **+36 %** |
| DD | $3 230 | **$2 378** | **−26 %** |
| P/DD | 10.16 | **18.80** | **+85 %** |
| WR | 46.3 % | 55.9 % | +9.6 pp |
| PF | 1.30 | 1.56 | +0.26 |
| Trades | 1 319 | 1 142 | −13 % |

**La v2 explose la v1** sur toutes les métriques : moins de trades mais beaucoup mieux sélectionnés (WR +10pp, PF +0.26). Les gains viennent de quatre leviers découverts dans cette itération :
1. `block_loss_exit_before_partial=True` (filtre v3 sous-utilisé en v1) — gros lift DD.
2. `hma1_len=9` (au lieu de 13 par défaut) — gros lift PnL + WR.
3. `max_sl_points=100` (au lieu de 300) — coupe les trades à SL extrême sans tuer le volume.
4. Refonte des blackouts : 11h reste catastrophique, mais H=06-07-08-09 (zone matinale neutre/légèrement perdante) sont devenues TOXIQUES sur ce nouveau set de signaux (sous-section §4).

---

## 2. Configuration retenue (`winner_preset.json`)

### Timeframe & risque
```python
interval       = "7m"
initial_equity = 50_000
risk_per_trade = 0.0047    # 0.47 %
max_contracts  = 50
```

### Paramètres de stratégie (overrides vs `default_params`)
```python
{
    "hma1_len": 9,                              # default 13
    "hma2_len": 34,                             # default 21
    "hw_range_on": True,                        # default False
    "block_loss_exit_before_partial": True,     # default False
    "max_sl_points": 100.0,                     # default 300.0
    "tick_buffer": 1,                           # default 0
}
```
Tous les autres params restent à leur valeur défaut v3 (cf. preset JSON).

### Blackouts (reference Brussels time)

| Fenêtre | Statut | Raison |
|---------|--------|--------|
| 00:00 – 00:05 | inactive (UI default) | — |
| 03:00 – 04:00 | **AJOUTÉ** | H=03 perdante (–$1,184) |
| 06:00 – 07:00 | **AJOUTÉ** | DD-reducer (paradoxal, voir §4-B) |
| 07:00 – 08:00 | **AJOUTÉ** | DD-reducer (paradoxal, voir §4-B) |
| 09:00 – 09:05 | inactive (UI default) | — |
| 09:00 – 10:00 | **AJOUTÉ** | DD-reducer |
| 11:00 – 12:00 | **AJOUTÉ** | H=11 toxique (–$3,559, WR 41%) |
| 12:00 – 14:00 | inactive (UI default) | — |
| 15:30 – 15:35 | inactive (UI default) | — |
| 16:30 – 22:00 | inactive (UI default) | — |
| 22:00 – 23:59 | active (UI default) | post-close CME |

### Auto-close
**22:00:00** reference Brussels (CME daily close, UI default pour `HMASSLOsciV3`). Jamais modifié.

### Daily limits
**Désactivées**. Testées en `intra_bar` et `after_close` (§5) : aucune combinaison n'a battu le couple winner sans-limits.

---

## 3. Top alternatives

Toutes valides (PnL > $30 k ET DD < $2.5 k) :

| # | Config | Risk | PnL | DD | PF | P/DD | Trade-off |
|---|--------|------|-----|----|----|------|-----------|
| **0** | **5BO (11+06+07+03+09)** | **0.47 %** | **$44 711** | **$2 378** | 1.56 | **18.80** | **← WINNER : PnL maxi avec DD safe** |
| 1 | 5BO (11+06+07+03+09) | 0.48 % | $44 225 | $2 484 | 1.54 | 17.81 | PnL ≈, mais DD au bord (8$ du seuil) |
| 2 | 5BO (11+06+07+03+09) | 0.43 % | $42 578 | $2 397 | 1.58 | 17.77 | PnL un peu moins fort, plus de PF |
| 3 | 5BO_alt (11+06+07+03+18) | 0.41 % | $39 549 | $2 440 | 1.56 | 16.21 | Substitue 09-10 par 18-19 |
| 4 | 4BO (11+06+07+03) | 0.37 % | $37 688 | $2 130 | 1.56 | 17.69 | Moins de blackouts, P/DD comparable |
| 5 | 4BO (11+06+07+03) | 0.40 % | $38 238 | $2 449 | 1.53 | 15.61 | Comme #4 mais risk plus élevé |

Les alternatives 1 & 2 sont les plus proches du winner. Si on veut **maximiser le P/DD au lieu du PnL** : alt #2 (risk=0.43 %) avec PF=1.58 est marginalement préférable. Le choix retenu maximise le PnL absolu sous contrainte DD < $2 500.

### Closest failures (marge documentée)
- 5BO @ 0.46 % : PnL=$43 495 / DD=**$2 655** — DD au-dessus du seuil. 1 cran sous le sweet spot.
- 5BO @ 0.50 % : PnL=$44 830 / DD=**$2 689** — idem. La fonction DD(risk) n'est pas monotone (cf. §4-D).

---

## 4. Insights de la recherche

### A. Hiérarchie des leviers (par lift de P/DD)

1. **Blackouts (5BO)** : 8.46 → 18.80 (×2.2). Le plus gros multiplicateur de la campagne. Particulièrement l'ajout des fenêtres `07-08` et `03-04` au-dessus de `11-12 + 06-07` (P/DD passe de 11.38 à 15.56), puis `09-10` (15.56 → 16.73→18.80 après scaling risk).
2. **`block_loss_exit_before_partial=True`** : 5.09 → 6.01 (×1.18). Réduit le DD de $5 051 à $4 320 sans toucher au PnL. Levier underused en v1.
3. **`hma1_len=9`** (au lieu de 13) : 6.01 → 6.73 (×1.12) seul mais +$10 k de PnL et +2pp WR — gros lift cumulatif quand combiné aux autres.
4. **`max_sl_points=100`** : 6.01 → 6.74 (×1.12). Coupe les trades à SL > 100 pts (filtre les setups où le canal HW est trop large). N'affecte PAS le nombre de trades (1461 → 1461) mais améliore le PnL net.
5. **`tick_buffer=1`** : 6.74 → 8.46 (×1.26 en combo avec les deux précédents). Marginal seul, amplificateur en combo.

### B. Heures à blackouter — paradoxe des "heures neutres"

Sweep horaire sur le baseline v2 :

| H | n | total | avg | WR | Décision |
|---|---|-------|-----|-----|----------|
| 11 | 78 | –$3 559 | –$46 | 41% | **BO** (clairement perdante) |
| 17 | 67 | –$1 279 | –$19 | 52% | pas BO (avg léger, complexité non concluante) |
| 03 | 66 | –$1 184 | –$18 | 44% | **BO** (gain DD net) |
| 06 | 67 | +$487 | +$7 | 40% | **BO** ⚠ |
| 07 | 63 | +$201 | +$3 | 54% | **BO** ⚠ |
| 09 | 58 | +$1 891 | +$33 | 53% | **BO** ⚠⚠ |

**Effet contre-intuitif** : les hours 06, 07 et 09 sont **positives** en PnL net mais blacker chacune **réduit le DD**. Mécanisme probable : les trades de cette zone matinale (cluster pré-US-open) déclenchent des séquences "win-then-bigloss" qui amplifient le DD intra-bar même si la moyenne reste positive. Le tradeoff est asymétrique — on perd un peu de PnL contre un gain DD beaucoup plus grand. Cohérent avec le fait que `block_loss_exit_before_partial` (qui agit sur le timing des sorties) a aussi un gros lift DD.

C'est aussi la raison pour laquelle le tri par P/DD plutôt que par PnL est crucial sur ce setup.

H=17 (campagne v1) a été testé et **dégrade** légèrement le P/DD ici aussi — confirmé.

### C. "Non-événements"

- **`ssl_mult` (5 valeurs)** : strictement aucun effet observable, comme en v1. Le canal SSL n'est probablement pas consommé via cette borne. À auditer (`src/strategies/hma_ssl_osci_v2.py::_compute_ssl`).
- **`mf_length`, `mf_smooth`** : aucun effet quand `cloud_on=False` (notre cas). Dead-code conditionnel. Logique vu le code, mais à noter.
- **`max_candle_pct` (sauf 0.5)** : pratiquement aucun effet.
- **`one_trade_per_entry_window=False`** : marginal (+0.17 P/DD) — pas retenu.
- **`delta_ext_on=True`** : DD écrasé à $2 504 (!) mais nombre de trades chute de 1 480 à 242 et PnL à $7 541 → P/DD=3.01. Filtre **trop restrictif**, pas retenu (le but n'est pas un DD ridiculement bas avec un PnL marginal).

### D. Fonction DD(risk) — non-monotonie

Sur 5BO winner (11+06+07+03+09) :

| risk | PnL | DD | P/DD | Pass? |
|------|-----|----|------|-------|
| 0.40 % | $37 693 | $2 251 | 16.75 | ✅ |
| 0.41 % | $38 851 | $2 281 | 17.03 | ✅ |
| 0.42 % | $40 162 | $2 400 | 16.73 | ✅ |
| 0.43 % | $42 578 | $2 397 | 17.77 | ✅ |
| 0.44 % | $42 864 | $2 575 | 16.65 | ❌ |
| 0.45 % | $42 749 | $2 648 | 16.14 | ❌ |
| 0.46 % | $43 495 | $2 655 | 16.38 | ❌ |
| **0.47 %** | **$44 711** | **$2 378** | **18.80** | **✅ ← WINNER** |
| 0.48 % | $44 225 | $2 484 | 17.81 | ✅ |
| 0.50 % | $44 830 | $2 689 | 16.67 | ❌ |
| 0.52 % | $48 307 | $2 818 | 17.14 | ❌ |

La fonction DD(risk) n'est **pas monotone** : un creux à 0.47 %, suivi d'un pic à 0.50 %. Cause : floor entier sur les contrats (`max(1, int(raw))` dans `simulator._calc_size`). À 0.47 %, l'arrondi assigne moins de contrats sur certains gros loss-days qu'à 0.46 % ou 0.50 %. C'est un **sweet spot d'arrondi** — robustesse à interroger en walk-forward.

### E. Day-of-week (au winner)

Sur la base v2 (avant blackouts) :

| Jour | n | total | avg | WR |
|------|---|-------|-----|-----|
| Lun | 276 | +$11 601 | +$42 | 55% |
| Mar | 297 | +$8 901 | +$30 | 49% |
| Mer | 288 | +$5 806 | +$20 | 57% |
| Jeu | 296 | +$12 406 | +$42 | 53% |
| Ven | 253 | +$137 | +$1 | 50% |

Vendredi n'est plus la catastrophe de la v1 (–$4 057 → +$137 avec les nouveaux params + filtres). Aucun blackout DOW nécessaire — le moteur n'en expose pas de toute façon.

### F. Daily limits — sans effet positif

Testé `intra_bar` et `after_close` avec 6 combinaisons (±500/700, ±400/500, ±800/1200, etc.). Meilleur résultat : `intra_bar +$500/-$700` → PnL=$34 824 / DD=$2 839 / P/DD=12.27. **Dégrade** la config sans-limits. Les daily limits coupent les bons jours en plus des mauvais ; sur cette stratégie le PnL est lisse (winrate 56 %), donc les jours `+$500` sont fréquents et coupés trop tôt.

---

## 5. Démarche (8 étapes)

1. **Baseline** ([sweeps/01_baseline.py](sweeps/01_baseline.py)) — TF 7m et 10m, v3 defaults vs prev_winner_overrides, blackout 22-23:59 seul. M7 + overrides = P/DD 5.09 (baseline de départ).
2. **Filter activation** ([sweeps/02_filter_activation.py](sweeps/02_filter_activation.py)) — `block_loss_exit_before_partial=True` identifié comme lift unique (P/DD 5.09 → 6.01).
3. **Strategy params 1D** ([sweeps/03_strategy_params.py](sweeps/03_strategy_params.py)) — 16 hyperparams × 4-7 valeurs. Winners : `hma1=9`, `max_sl=100`, `hma_pol_bars=2`, `tick_buffer=1`. Combo ([sweeps/03b_combos.py](sweeps/03b_combos.py)) confirme `hma1=9 + max_sl=100 + tick_buffer=1` additif (P/DD = 8.46).
4. **Risk + daily limits** ([sweeps/04_risk_and_daily_limits.py](sweeps/04_risk_and_daily_limits.py)) — large grid risk + DL en intra_bar/after_close. Risk sweet spot identifié, DL toujours dégradant.
5. **Hour analysis** ([sweeps/05_hour_analysis.py](sweeps/05_hour_analysis.py)) — bucketisation par heure et DOW. Toxic clair : H=11 ; suspects : H=03, H=17.
6. **Blackout sweep** ([sweeps/06_blackout_sweep.py](sweeps/06_blackout_sweep.py), [sweeps/06b_blackout_extra.py](sweeps/06b_blackout_extra.py), [sweeps/06c_blackout_triples.py](sweeps/06c_blackout_triples.py)) — découverte de l'effet "DD-reducer" des heures neutres 06, 07, 09. Best 5BO = 11+06+07+03+09 → P/DD 15.56-18.80 selon risk.
7. **Fine-tune** ([sweeps/07_finetune.py](sweeps/07_finetune.py), [sweeps/07b_5bo_fine.py](sweeps/07b_5bo_fine.py)) — grille fine risk × blackouts. Winner : 5BO + risk=0.47 %.
8. **Validation finale** ([sweeps/08_final_validation.py](sweeps/08_final_validation.py)) — winner + 5 alternatives + 2 closest failures + référence v1.

Tous les logs dans [`logs/`](logs/).

---

## 6. Risques & idées pour la prochaine itération

### Risques d'overfit

- **Sweet spot risk=0.47 % très étroit** : 0.46 % et 0.50 % fail le DD goal. Marche d'arrondi sur les contrats. À tester en walk-forward — la solidité hors-sample est l'inconnue principale.
- **5 blackouts cumulés** : trois sont contre-intuitifs (06, 07, 09 ont PnL positif sur la période). Risque que ces heures aient été "DD-reducers" sur la période 2025-2026 par hasard du timing des grosses pertes. Cohérent avec les buckets mais à valider sur sous-périodes.
- **Période unique** (17 mois). Pas de walk-forward.

### Idées concrètes

1. **Walk-forward analysis** — splitter la période en 4 (≈ trimestres) et re-fitter les paramètres et blackouts par fenêtre. Mesurer la dégradation hors-fold.
2. **Audit `block_loss_exit_before_partial`** — comprendre **pourquoi** ce flag (qui passe `block_loss_canal_exit_before_tp1=True` au simulateur) réduit autant le DD ici alors qu'il était dormant en v1. Lecture du code simulateur recommandée pour confirmer le mécanisme.
3. **Audit `ssl_mult`** — déterminer si ce paramètre est dead-code ou simplement mal sweepé.
4. **Pousser le `hma1_len`** — la v3 ne permet pas hma1 > hma2, mais combo `hma1=9 / hma2=34` est le winner. Tester `hma1=11` ou `hma2=42` (en gardant ratio).
5. **Tester un blackout asymétrique long/short** — H=11 est-elle perdante seulement en long (US-open) ? Le moteur ne le permet pas actuellement.
6. **Multi-asset (MGC + MNQ)** — partager le DD entre les deux pour exploiter la non-corrélation. Le winner MNQ v2 (P/DD = 15.5) et MGC v2 (P/DD = 18.8) côte à côte donneraient une combinaison robuste.
7. **Bayesian/Optuna sweep** — la non-monotonie risk × blackouts × `tick_buffer` suggère qu'un grid 1D-only manque des poches optimales.

---

## 7. Reproduction

```bash
# Vérifier le preset (doit afficher ✅ MATCH)
python scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/verify_preset.py

# Re-générer le preset depuis zéro
python scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/build_winner.py

# Visualiser dans l'UI
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
# (autre terminal)
cd frontend && npm run dev -- --port 3001 --host
# → http://localhost:3001 → page Favoris → preset "[Auto] HMASSLOsciV3 — MGC 7m v2 …"
```

Le preset est inséré en tête de `data/presets.json` et visible dans la page Favoris.
