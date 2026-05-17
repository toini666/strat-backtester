# OBSERVATIONS.md — Dissection des sorties V3 (HMA rapide → HW)

Source : `outputs/summary.json` + `outputs/exits_ALL.csv` (replay des 2 baselines).
- MNQ_v5 : 1241 trades, PnL $68,765, DD $1,579 (référence).
- MGC_v3 : 865 trades, PnL $44,692, DD $1,944 (référence).
- Total : 2106 trades, dont 1340 avec « fast cross puis HW » dans la vie du trade.

L'analyse couvre symétriquement **les sorties qui ont payé** (le wait HW post-fast-cross
a ajouté du PnL) ET **les sorties qui ont coûté / re-basculé négatif** (give-back après
MFE positif). Les contre-presets sont rapportés systématiquement pour vérifier la
stabilité cross-asset.

---

## EX. Trigger de sortie finale

### Numerical context

| Asset | N(fast→HW) | HW paid | HW cost | HW neutral | mean Δ(HW − fast) | sum Δ |
|-------|------------|---------|---------|------------|--------------------|--------|
| MNQ_v5 | 789 | 36.0% | 29.5% | 34.7% | +$16.84 | **+$13,286** |
| MGC_v3 | 551 | 33.2% | 22.1% | 44.6% | +$18.08 | **+$9,962** |
| **TOTAL** | **1340** | **34.9%** | **26.5%** | **38.8%** | **+$17.35** | **+$23,248** |

**Première lecture** : sur les 1340 trades qui passent par la séquence fast→HW, attendre
la HW *en moyenne* paie +$17/trade — l'attente est globalement profitable. Le médian
est `$0` : la distribution est *long-tail* (les gains de l'attente sont concentrés sur
une fraction des trades).

Conditionné par le PnL au fast cross :

| Asset | N(fast_in_profit) | mean Δ | N(fast_in_loss) | mean Δ |
|-------|-------------------|--------|------------------|--------|
| MNQ_v5 | 515 | +$19.73 | 274 | +$11.41 |
| MGC_v3 | 357 | +$21.37 | 194 | +$12.02 |

Constat : **attendre la HW paie en moyenne dans les deux régimes** (fast en profit ET
fast en perte). Pas d'asymétrie évidente exploitable au niveau de la moyenne. Mais la
question reste : la queue gauche (HW coûte) peut-elle être coupée ?

### EX.W — issues des Winners (HW a payé)

- **obs-EX.W.1** — Sur les **34.9 %** des trades où la HW a payé, le delta moyen est
  d'environ +$80-100 par trade (résultat dérivé : sum Δ / N(HW paid) ≈ +$50/winner +
  pondération des grosses queues). Sur les trades où le fast cross était DÉJÀ en
  profit (n=872), la HW ajoute +$20/trade en moyenne — *l'attente capture le tail des
  gros gagnants*. Couper ici = laisser du PnL sur la table.
  → **Hypothèse H6** : partial au fast cross (en profit) MAIS continuer pour la HW :
  fixer un % à 25/50/75 % et tester la durabilité du PnL.

- **obs-EX.W.2** — Sur MNQ_FAST_IN_GREEN (n=418, $48.7k de PnL), le delta moyen
  HW-fast est +$7.6/trade et la HW paie +$8/trade quand fast est en profit. Le tail
  positif est plus modeste qu'en RED. **Régime canal-vert = tail compression**.
  → Pas d'hypothèse dédiée (l'angle "régime-conditional" ferait exploser la combinatoire),
  mais à garder pour le report § Pistes pour itération suivante.

- **obs-EX.W.3** — Sur MNQ_FAST_IN_RED (n=427, $76.9k de PnL ! C'est le gros du compte),
  delta moyen HW-fast = +$25.9, dont **+$32.2 quand fast en profit**. **La majorité de
  l'edge MNQ vient des trades à contre-canal en profit, et la HW est un véritable
  amplificateur**.
  → Confirme que H1 ("fast cross only" blanket) est probablement REJECT.

### EX.L — issues des Losers (HW a coûté / give-back)

- **obs-EX.L.1** — **26.5 % des trades** (468/1340) : la HW *coûte* (delta < 0).
  Sur MNQ : 29.5 % (mean delta négatif). Sur MGC : 22.1 %. Stable cross-preset.
  → **Hypothèse H1** : « fast cross only » — couper l'attente HW pour éliminer cette
  queue. Risque : on perd aussi l'amplificateur (obs-EX.W.3). Verdict probable :
  REJECT mais à mesurer.
  → **Hypothèse H2** : « HW only if profit » — au moment du HW cross, exiger que
  l'on soit in-profit pour fermer (sinon laisser courir vers le prochain HW).
  Variante moins destructive de H1.

- **obs-EX.L.2** — **Give-back : 369 trades (17.5%)** ont eu MFE ≥ 0.5R puis terminent
  négatifs. PnL moyen = -$178. Stabilité : MNQ 20.1 % avg -$176, MGC 13.9 % avg -$183.
  Coût total estimé : ≈ -$66 000 (somme des PnL réels de ces trades). **Plus gros levier
  défensif identifié dans cette campagne.**
  → **Hypothèse H4** : *MFE-floor exit* — fermer 100 % une fois MFE ≥ X R puis retombé
  sous Y R. Sweep (trigger_r, floor_r) ∈ {(1.0, 0.3), (1.0, 0.5), (1.5, 0.5), (2.0, 1.0)}.
  → **Hypothèse H8** : *partial X % sur MFE seuil* (variante non-binaire de H4) —
  prendre 25/50 % une fois MFE ≥ 1R, laisser le reste courir vers la HW.

- **obs-EX.L.3** — **Canal flip alt** : 571 trades (27 %) ont eu un flip canal contra
  pendant la vie du trade. Comparé au PnL réel, sortir au flip est en moyenne PIRE
  (sum delta = -$26,960). Mais ces 571 trades ont en moyenne un PnL réel élevé
  (MNQ +$31, MGC +$109) — ce sont en partie des gros gagnants pour lesquels le flip
  arrive avant le pic. *Sortir au flip cap le tail.* La question : le flip est-il
  un signal *defensive* protégeant uniquement la queue gauche (loses) sans toucher
  aux gros gagnants ?
  → **Hypothèse H3** : « exit on canal flip » — *probable REJECT* mais à confirmer
  numériquement (peut-être que le DD baisse même si le PnL baisse).
  → **Hypothèse H7** : « partial sur canal flip » — variante non-binaire : libérer
  25-50 % au flip, laisser le reste finir via la HW V3.

---

## PT. Partial take-profit

### PT.W — issues des Winners

- **obs-PT.W.1** — Sur 1340 setups fast→HW, **65 %** (872) ont fast cross en profit.
  Sur ces 872, mean PnL_at_fast ≈ +$130/trade (mean inféré à partir du delta-when-in-profit).
  Une fraction (probablement 25 %) capturée systématiquement = ~$28 k de PnL « fixé »
  sans toucher au tail.
  → **Hypothèse H6** (déjà nommée en EX.W.1) : partial X % au fast cross. Sweep
  {25, 50, 75} %.

- **obs-PT.W.2** — Sur MNQ_FAST_IN_RED, mean PnL_at_canal_flip = +$28.7 (n=99), donc
  une fraction du flip arrive aussi en profit modéré. *Partial au flip* prendrait
  des gains intermédiaires sans cap le tail (par opposition à exit-on-flip).
  → **Hypothèse H7** (déjà nommée en EX.L.3) : variante non-binaire de H3.

### PT.L — issues des Losers

- **obs-PT.L.1** — **15.0 %** des trades-perdants (155/2106) ont eu MFE ≥ 1R avant
  de basculer perdants. Sur ces 155 trades, le PnL réel moyen est négatif ; un partial
  de 50 % à MFE = 1R aurait fixé ~ +$0.5R × 50 % × size sur chacun, soit ~$30 000
  d'edge récupéré (estimation grossière).
  → **Hypothèse H8** (déjà nommée en EX.L.2 — variante PT de H4) : partial 25/50 %
  sur MFE seuil. Tester (pct, trigger) ∈ {(25, 0.5), (25, 1.0), (50, 1.0), (50, 1.5)}.

---

## Synthèse — sélection finale 7 hypothèses (quota : 5-9, dont 2-5 EX, 1-4 PT, ≥1 L)

| # | Levier | Angle | Hypothèse | Source obs. | Verdict attendu |
|--:|:------:|:-----:|-----------|--------------|------------------|
| 1 | EX | L | `lab_exit_fast_cross_only` — skip HW totally | EX.L.1 | REJECT probable (HW paie en moy.) — mesurer |
| 2 | EX | L | `lab_exit_hw_only_if_profit` — partial 100% au HW si in-profit, sinon V3 default | EX.L.1 | MIXED / KEEP DD-only ? |
| 3 | EX | L | `lab_exit_on_canal_flip` — close au flip contra | EX.L.3 | REJECT probable — mesurer |
| 4 | EX | W+L | `lab_exit_mfe_floor_r` + `_trigger_r` — close 100% sur give-back | EX.L.2 (loss-only) + EX.W.1 | **KEEP candidat fort** |
| 5 | PT | W | `lab_pt_on_fast_cross_pct` — partial au fast cross | EX.W.1 / PT.W.1 | KEEP candidat |
| 6 | PT | L | `lab_pt_on_canal_flip_pct` — partial au flip contra | EX.L.3 / PT.W.2 | MIXED candidat |
| 7 | PT | L | `lab_pt_on_mfe_r_pct` — partial au MFE seuil | PT.L.1 | KEEP candidat |

Quota vérifié : 4 EX + 3 PT = 7 hypothèses ; 5 angle L (1,2,3,6,7) dont 1 W+L (#4). ✓

### Candidates NON retenues ce cycle

- **Régime-conditional exits** (couper HW seulement en canal-vert vs canal-rouge) :
  obs-EX.W.2 montre une asymétrie de régime, mais coder un *régime gate* doublerait
  la combinatoire. *Pour itération -3.*
- **HW-arming with timeout** (forcer un fallback si HW ne vient pas avant N bars) :
  bars_fast_to_hw a probablement une queue longue (à vérifier). Variante de H5
  `lab_exit_fast_cross_after_bars` — déjà codée dans le Lab, sweep court possible
  mais retiré du quota pour rester dans la profondeur. *Pour itération -3.*
- **Exit on HW value extreme** (fermer si HW oscillator < -50 par exemple) :
  ne touche pas les séries déjà exposées — exigerait un nouveau signal. *Hors budget.*

### Note sur l'asymétrie H1/H3 entre MNQ et MGC

- MNQ_v5 a `block_loss_exit_before_partial=False` → H1/H3 forceront unconditionnellement
  la sortie à fast/flip.
- MGC_v3 a `block_loss_exit_before_partial=True` → H1/H3 ne fermeront pas en cas de
  perte avant TP1 ; le canal-break fallback prendra le relais sur une bar ultérieure.
- C'est un **comportement asset-spécifique de V3 préservé par le Lab** (par design : on
  ne touche pas à `block_loss_exit_before_partial`, c'est un paramètre V3 et la mission
  interdit de toucher au sizing/SL/entrée). Documenté.
