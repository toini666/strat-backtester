# Rapport final — Évolution empirique HMASSLOsciV3 (campagne 2026-05-17)

## 1. Cadrage

- **Période** : 2025-01-06 → 2026-05-15 (~17 mois — H25 → M26 contracts).
- **Stratégie source** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`).
- **Stratégie Lab dérivée** : `HMASSLOsciV3Labv1` (`src/strategies/hma_ssl_osci_v3_lab_v1.py`),
  hérite de V3, 6 paramètres ajoutés (un par hypothèse), defaults = comportement V3 strict.
- **Sanity test obligatoire** : ✅ passe (`Lab(defaults) == V3` exactement sur les 2 baselines).
- **Auto-close** : 22:00 reference Brussels (invariant — jamais touché).
- **Budget** : ~88 backtests utilisés (sanity 4 + Phase 1 replay 2 + Phase 2 sweeps 60 + Phase 2 reruns 12 + Phase 3 combos 5 + Phase 4 wf 8 + verify 1). Sur les 150-250 budgétés.

### Baselines

| Asset | Preset | PnL | DD $ | Trades | WR | PF | P/DD |
|-------|--------|-----:|-----:|-------:|---:|---:|-----:|
| MNQ_v5 | `2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json` | $68,765 | $1,579 | 1,241 | 48.3% | 1.70 | **43.55** |
| MGC_v3 | `2026-05-17_HMASSLOsciV3_MGC_v3/winner_preset.json` | $44,692 | $1,944 | 865 | 55.1% | 1.66 | **22.99** |

## 2. Phase 1 — Observation

2,106 trades analysés (1,241 MNQ + 865 MGC). MAE/MFE en R calculés sur 1m bars
entre `entry_execution_time` et `exit_execution_time`. Indicateurs au bar
d'entrée capturés via `debug_frame` (canal_width, last_hw_value, mfi, osc_sig,
canal_green, candle_pct, two_bar_body_pct). `shadow_hw_bars` (distance au
prochain HW adverse depuis entry) calculé.

**Key findings (winners + losers, 3 piliers) :**

| Pilier | Insight | Source pour hypothèse |
|--------|---------|-----------------------|
| A — entry | MGC : bars 3+ après slow-cross ont WR 65-68% vs 54% à bar 0/1 (mais 79% du volume est à bar 0/1) | H-A1 |
| A — entry | Distance SL très petite (<23 pts MNQ) → WR 36% mais total PnL $+35,854 via taille de position (bigger size compensates) | H-A3 (ambigu) |
| A — entry | MNQ H=6 toxique ($-2,112, WR 30.8%, SL rate 53.8%) ; MGC H=22 toxique ($-891, WR 33%) | H-A4 |
| A — observation contraire | Candles agressives à l'entrée → MEILLEUR WR (57-65 % top quintile) — confirme `max_candle_pct=0.9` actuel comme good ceiling. | (renseigne H-B1 a priori) |
| B — SL avoidance | 39 % des SL MNQ surviennent en ≤3 bars ($-31k = 39 % des SL loss) ; SL trades ont MAE=1.38R / MFE=0.61R (la moitié ne dépasse jamais 0.3R) | H-B1, H-B2 |
| B — SL avoidance | Médiane shadow_hw_bars : SL=2.0 / Canal Exit=3-4 → un HW adverse précoce est signature loser | H-B2 |
| C — TP optim | MNQ H=18-21 auto-close profitable (+$7,367 net AC) → Canal Exit late intercept des trades qui auraient atteint 22:00 | H-C1 |

Détail complet : [`phase1_observation/OBSERVATIONS.md`](phase1_observation/OBSERVATIONS.md).
CSVs : [`phase1_observation/outputs/`](phase1_observation/outputs/).

## 3. Phase 2 — A/B tests par hypothèse

Verdicts détaillés dans [`HYPOTHESES.md`](HYPOTHESES.md).

### H-A1 — `lab_entry_min_bars` ∈ {1, 2, 3, 4} — **REJECT**

Pousser l'entrée au bar N≥1 après le slow-cross **détruit le PnL sur les 2 presets**
(−$18k à −$37k MNQ ; −$24k à −$37k MGC) avec DD en hausse. Le bar 0 capte des
setups uniques (la *condition* d'entrée se croise au bar même du slow-cross),
les bars suivants sont des opportunities différentes. La WR plus haute à bar 3
masquait un effet de sélection (n petit).

### H-A3 — `lab_min_sl_points` ∈ {5, 10, 15, 20, 30} — **REJECT**

Filtrer les SL très tight (small SL distance) **sacrifie du PnL massivement**.
À 10pts sur MGC le DD baisse à $1,245 mais le PnL chute de −$16k (P/DD presque
neutre −0.59). Les small-SL trades sont gros contributeurs PnL via la taille
de position — ce sont les "leveraged winners". À 30pts, PnL −$37k. L'ambiguïté
de Phase 1 est tranchée : la PnL contribution domine.

### H-A4 — `lab_entry_blocked_hours` — **MIXED (KEEP MGC)**

| Preset | Variant | ΔPnL | ΔDD | ΔP/DD | Verdict |
|--------|---------|-----:|----:|------:|---------|
| MNQ_v5 | (6,) | +$944 | +$996 | −16.48 | REJECT — DD explose |
| MNQ_v5 | (6, 12) | +$570 | +$996 | −16.63 | REJECT |
| MNQ_v5 | (6, 4) | +$669 | +$700 | −13.08 | REJECT |
| **MGC_v3** | **(22, 20)** | **+$1,622** | **−$15** | **+1.01** | **KEEP** |
| MGC_v3 | (22,) | +$1,258 | +$0 | +0.65 | KEEP secondaire |
| MGC_v3 | (22, 17) | +$1,213 | +$677 | −5.47 | REJECT — H=17 DD-amplifier |

Effet asymétrique : sur MNQ, retirer les heures toxiques élargit les drawdown
streaks (la stratégie compense par les heures profitables) — DD-amplifier
inverse. Sur MGC les heures sont bien des "purement perdantes" sans
compensation, on les coupe proprement.

### H-B1 — `lab_max_2bar_body_pct` ∈ {0.5, 0.7, 1.0, 1.5} — **REJECT**

Aucune valeur n'améliore P/DD. À 0.5 sur MGC le DD passe à $2,563 (+$619), PnL
−$6,096. Confirme l'observation Phase 1 : les candles agressives sont des
**signaux de momentum confirmés**, pas des entrées "overheated". Filtre
contre-productif.

### H-B2 — `lab_no_hw_flip_kill_bars` — **NOT TESTED** (contrainte moteur)

Deux mécanismes essayés (V1 : kill si pas de HW favorable dans N bars ; V2 : kill
si HW adverse dans N bars). **Les deux échouent structurellement** car le mode
`v3_fast_hma_ssl` ferme la position sur le **prochain HW cross dans l'une OU
l'autre direction** une fois `pending_final_exit` armé (voir
`src/engine/simulator.py:1200-1206`). Injecter notre kill arme l'exit, qui se
déclenche alors souvent sur un HW favorable (= une sortie sur le mini-rebond
que les winners patients utilisent comme tremplin).

Sans modification du simulateur (`v3_fast_hma_ssl` n'est pas conçu pour des
exits défensifs externes), l'hypothèse n'est pas testable proprement. Marquée
NOT TESTED conformément à la mission §5 escape-clause.

### H-C1 — `lab_disable_canal_exit_from_hour` — **MIXED (KEEP MGC à 21)**

V1 du mécanisme (neutraliser `canal_lower/upper`) → no-op sur le mode
`v3_fast_hma_ssl` (qui n'utilise pas canal_lower/upper pour son exit principal).
V2 (correct) : **supprimer `fast_hma_exit_long/short` après l'heure X**.

| Preset | from_hour | ΔPnL | ΔDD | ΔP/DD | Verdict |
|--------|----------:|-----:|----:|------:|---------|
| MNQ_v5 | 18 | −$1,767 | +$1,802 | −23.73 | REJECT |
| MNQ_v5 | 19 | −$1,864 | +$954 | −17.14 | REJECT |
| MNQ_v5 | 20 | −$716 | +$0 | −0.45 | REJECT marginal |
| MNQ_v5 | 21 | −$332 | +$0 | −0.21 | REJECT marginal |
| MGC_v3 | 18 | +$771 | +$159 | −1.37 | REJECT |
| MGC_v3 | 19 | +$452 | +$179 | −1.73 | REJECT |
| MGC_v3 | 20 | +$2 | +$343 | −3.45 | REJECT |
| **MGC_v3** | **21** | **+$1,064** | **+$0** | **+0.55** | **KEEP** |

L'observation MNQ "auto-close H=18-21 = $+7,367 net" n'a pas transféré : la
suppression de fast-HMA arming late prive le SL-trailing implicite (V3 sortait
de positions tournant in-loss via fast-HMA → Canal Exit fallback), donc le DD
augmente. Sur MGC l'effet est inversé à `from_hour=21` : pas de DD impact, gain
PnL réel.

## 4. Phase 3 — Combinaison gagnante (MGC seulement)

| Preset | Variant | PnL | DD | P/DD | ΔP/DD vs baseline |
|--------|---------|----:|---:|-----:|------------------:|
| MGC_v3 | OFF (baseline V3) | $44,692 | $1,944 | 22.99 | +0.00 |
| MGC_v3 | ALONE entry_blocked_hours=(22,20) | $46,314 | $1,929 | 24.01 | **+1.01** |
| MGC_v3 | ALONE disable_canal_exit_from_hour=21 | $45,756 | $1,944 | 23.54 | +0.55 |
| MGC_v3 | **PAIR (winner V4 MGC)** | **$47,164** | **$1,971** | **23.93** | **+0.93** |

Le **pair (winner V4)** capture +$2,472 PnL (presque la somme additive des
singletons : +$1,622 + +$1,064 = +$2,686). Le DD bouge de +$27 ($1,944 → $1,971),
ce qui dégrade légèrement le ratio vs la singleton (22,20) (+0.93 < +1.01)
mais maximise le PnL absolu.

Choix WINNER V4 = **PAIR** (max PnL, walk-forward neutre out-of-fold — cf §5).
Singleton (22,20) listé comme ALT plus conservatif (meilleur P/DD ratio, margin
DD plus large $71 vs $29).

Le PnL final reste proche de la barre $2k DD : margin $29 — uncomfortable.

### Pourquoi pas de winner V4 pour MNQ

Sur les 6 hypothèses testées, **aucune n'a amélioré P/DD MNQ**. Pourquoi ?

1. **Baseline V5 dans un local optimum dense** — P/DD 43.55 est l'un des
   plus hauts de la lignée des campagnes HMASSLOsciV3. Tout filtre additionnel
   exclut des trades dont la disparition crée des séquences (win-then-loss
   compensées) qui amplifient le DD.
2. **H-A4 (toxic hour H=6)** : retirer H=6 → DD passe de $1,579 à $2,575
   (+63 %). H=6 a 53.8 % de SL rate mais est compensé par les heures
   adjacentes. L'effet "DD-amplifier" inverse documenté.
3. **H-B2 NOT TESTED** — où on aurait pu attaquer les SL early MNQ.
4. **H-C1** — la suppression de fast-HMA arming late prive le SL-trailing
   implicite, donc DD ↑.

Conclusion : la V5 MNQ utilise toutes les heures comme "shock absorbers"
mutuels. Sans modification structurelle du moteur ou refonte des indicateurs,
les leviers proposés n'ont pas d'angle d'attaque sur ce setup.

## 5. Phase 4 — Walk-forward (MGC)

Split temporel 50/50 :
- **train** : 2025-01-06 → 2025-10-10 (~9 mois)
- **test**  : 2025-10-10 → 2026-05-15 (~7 mois)

| Variant | Train P/DD | Test P/DD | Verdict per-fold |
|---------|-----------:|----------:|------------------|
| Baseline (V3 defaults) | 8.65 | 20.15 | — |
| H-A4 (22,20) seul | **9.86** ↑ | 19.56 ↓ | MIXED — train robuste, test légère dégradation |
| H-C1 (=21) seul | 8.52 ↓ | **21.69** ↑ | MIXED — inversé |
| **COMBO H-A4+H-C1 (winner V4)** | **9.70** ↑ | **20.11** ≈ | **NEUTRAL out-of-fold, KEEP train** |

**Lecture critique** : le test fold (Oct 2025+) est *plus profitable que le train*
(P/DD baseline 20.15 vs 8.65). Cela suggère un régime de marché plus favorable à
HMASSLOsciV3 sur la seconde moitié — où les heures toxiques (20, 22) de Q1-Q3 2025
ont peut-être disparu. H-A4 perd donc son edge sur la seconde moitié.

Le COMBO neutralise ce phénomène (test P/DD 20.11 ≈ baseline 20.15) car H-C1
compense en augmentant sur la seconde moitié.

**Risque d'overfit du COMBO** : modéré. Le PnL gain plein-période vient à 75 %
du train half. Mais comme test reste *neutre*, le combo ne "casse" pas
out-of-fold ; il ne fait que continuer à fonctionner. Acceptable comme winner
mais à surveiller en production.

Détail : [`logs/phase4_walkforward.log`](logs/phase4_walkforward.log).

## 6. Limites & risques

1. **Hypothèse B la plus prometteuse non-testée** — l'idée "kill early SL trades"
   est observationnellement très forte (39 % des SL MNQ en ≤3 bars, MFE médian
   0.3R), mais le simulateur n'expose pas de mécanisme d'exit défensif clean
   sans accès au runtime MAE/MFE et sans collision avec `v3_fast_hma_ssl`.
2. **Marge DD étroite** : winner MGC V4 a margin $29 sous le cap $2,000 (V3
   avait $56). Une variance de régime de marché peut tipper au-dessus.
3. **2 baselines seulement** — quota mission "min 1, max 3" respecté mais le
   cross-preset signal n'est pas robuste à un n=2.
4. **Walk-forward simple** (split 50/50) — pas de rolling-window. La forte
   différence de régime entre train et test masque potentiellement de
   l'overfit que le rolling exposerait.
5. **`lab_entry_blocked_hours` est asset-specific** (MGC=(22,20)). Ce n'est
   pas un filtre stratégie universel — il porte l'ADN de MGC late-session.
6. **Pas de winner MNQ** — la V5 baseline est trop optimisée pour bénéficier
   des hypothèses testées. Une itération suivante devrait attaquer
   structurellement (indicator-level tweaks, multi-asset blending, ou refonte
   du `v3_fast_hma_ssl` exit pour exposer un kill-on-MAE).

## 7. Pistes pour itération suivante

1. **Refonte simulateur — kill-on-MAE optionnel**.
   Ajouter `early_kill_if_mae_r_above_at_bar_n` au simulator : si MAE en R au
   bar entry+N dépasse un seuil, fermer. Permettrait de tester H-B2 (et plus)
   proprement. Effort estimé : ~1 jour.
2. **Audit `loss_exit_blocked` fallback** — H-C1 mécanisme V1 a montré un effet
   marginal côté MGC (+1.31 P/DD à h=18) via `loss_exit_blocked` + canal_lower
   neutralized. Comprendre ce sentier pourrait débloquer une variante H-C1.
3. **MNQ — sweep dans le sens INVERSE** :
   - **Étendre** les heures actives au lieu de les bloquer (V5 a 4 BO active ;
     en désactiver une ?).
   - **Réduire** `entry_window_bars` (= 3 sur V5) — testé à 1 ou 2.
   - **Modifier `signal_length=4`** sweet spot ou non-monotone ?
   Hypothèses à ajouter dans la stratégie Lab v2.
4. **Walk-forward rolling** — fenêtre 6 mois glissante au pas mensuel,
   re-fit MGC `(lab_entry_blocked_hours, lab_disable_canal_exit_from_hour)`
   à chaque fenêtre. Mesure de stabilité.
5. **DOW filter** — la corrélation Mon/Wed faibles vs Tue/Thu/Fri forts est
   un signal connu (V5 §4-D). Ajouter `BlackoutWindowSettings.days_of_week`
   au moteur permettrait de tester.
6. **Cross-asset transfert** — MGC winner V4 (22,20 + canal=21) à appliquer
   sur MES, M2K, MYM. Si la recette transfère, c'est un pattern structurel
   plutôt qu'un fit MGC.
7. **Filtre `risk_dist_points` top quintile** sur MGC (>$18.6pts WR=64%) —
   ALORS QUE H-A3 a échoué côté inverse, le filtre INVERSE (refuser SL trop
   LARGES) pourrait améliorer le ratio.

## 8. Reproduction

```bash
source venv/bin/activate

# 1) Sanity test — DOIT être ✅ MATCH
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase2_hypotheses/00_sanity_lab_equals_v3.py

# 2) Phase 1 — observation
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase1_observation/run_analysis.py
# → outputs/ avec trades_*.csv et summary.json

# 3) Phase 2 — sweeps (un par hypothèse)
for f in scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase2_hypotheses/0[1-6]*.py; do
  python "$f" 2>&1 | tee "scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase2_hypotheses/logs/$(basename $f .py).log"
done

# 4) Phase 3 — pairs + winner combo
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase3_combinations/01_pairs.py
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase3_combinations/02_winner_combo.py
# → winner_v4_MGC.json

# 5) Phase 4 — walk-forward
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/phase4_walkforward.py

# 6) Verify winner
python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/verify_winner_v4.py
# → DOIT afficher ✅ MATCH
```

UI : preset `[Auto] HMASSLOsciV3Labv1 — MGC 7m v4 (PnL $47.2k / DD $2.0k)`
inséré en tête des favoris (`data/presets.json`). Chargeable depuis l'écran
Favorites.
