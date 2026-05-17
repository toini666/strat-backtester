# REPORT.md — Évolution mono-pilier du mécanisme de sortie de HMASSLOsciV3

**TL;DR.** Sur les 6 hypothèses retenues post-observation (3 EX, 3 PT, dont 4
issues des losers + 1 W+L + 1 W), **aucune ne bat les baselines V3 sur le
critère cross-asset strict de la mission** (ΔP/DD ≥ 0 sur MNQ_v5 ET MGC_v3 sur
la période FULL). La sortie en deux temps de V3 (HMA rapide / SSL → HW) est un
édifice net-positif : sur 1340 setups où la séquence se déclenche, attendre la
HW après le cross rapide ajoute +$23,248 cumulés (+$17.35 mean / trade,
median 0). Aucun `winner_v<N+1>_<asset>.json` n'est produit ce cycle. Une
hypothèse (H2 « HW only if profit » au sens littéral du brief) est marquée
**NOT TESTED** car non implémentable sans modification du simulateur (V3 Canal
Exit fire avant le partial slot — détaillé en § Limites). Le résultat négatif
est explicitement permis par la mission ; les pistes pour itération suivante
sont documentées en § 7.

---

## 1. Cadrage

| | MNQ_v5 | MGC_v3 |
|-|--------|--------|
| Strategy | HMASSLOsciV3 | HMASSLOsciV3 |
| Période | 2025-01-06 → 2026-05-15 (≈16 mois) | idem |
| TF | 7m | 7m |
| Equity | $50,000 | $50,000 |
| Risk / trade | 0.48 % | 0.52 % |
| `final_exit_mode` | « HMA rapide/SSL → HW » | idem |
| `block_loss_exit_before_partial` | False | True |
| **PnL** | **$68,765** | **$44,692** |
| **Max DD ($)** | **$1,579** | **$1,944** |
| P/DD | 43.6 | 23.0 |
| Trades | 1,241 | 865 |
| Win rate | 48.3 % | 55.1 % |

Mission : identifier 5-9 améliorations *du mécanisme de sortie uniquement* (final
exit + partial), motivées par l'observation chiffrée et validées par A/B sweep.
Périmètre interdit : entrées, SL, sizing. Auto-close 22:00 (Brussels ref) FIXE.

---

## 2. Phase 1 — Observation des sorties (génération d'hypothèses)

Script : `phase1_observation/run_analysis.py`. Outputs : `outputs/exits_*.csv`,
`outputs/summary.json`, `OBSERVATIONS.md`.

### Findings cross-asset stables

| Métrique | MNQ_v5 | MGC_v3 | TOTAL |
|----------|-------:|-------:|------:|
| Trades total | 1241 | 865 | 2106 |
| Trades avec séquence fast→HW (analysable) | 789 | 551 | 1340 |
| **% HW a payé** (Δ HW − fast > 0) | 36.0 % | 33.2 % | 34.9 % |
| **% HW a coûté** (Δ < 0) | 29.5 % | 22.1 % | 26.5 % |
| % HW neutre (|Δ| < 1) | 34.7 % | 44.6 % | 38.8 % |
| Mean Δ HW − fast ($) | +$16.84 | +$18.08 | +$17.35 |
| **Sum Δ HW − fast ($)** | **+$13,287** | **+$9,962** | **+$23,249** |
| Mean Δ when fast in profit ($) | +$19.73 | +$21.37 | +$20.40 |
| Mean Δ when fast in loss ($) | +$11.41 | +$12.02 | +$11.67 |
| % trades give-back (MFE ≥ 0.5R puis fin négatif) | 20.1 % | 13.9 % | 17.5 % |
| Mean PnL des trades give-back ($) | −$176 | −$183 | −$178 |
| Trades avec contra-flip canal pendant la vie | 360 | 211 | 571 |
| **Sum Δ flip_alt − real ($)** | **−$10,844** | **−$16,115** | **−$26,960** |

**Lecture** :

1. La séquence V3 fast→HW est **net-positive** sur les 2 presets cumulés (+$23k).
   La distribution est *long-tail* à droite (médian = $0). Couper l'attente HW
   en blanket sacrifie le tail des gros gagnants.
2. Sortir au flip canal contra serait **net-negative** vs le PnL réel
   (−$27k cumulés sur 571 trades) — le flip cap le tail.
3. Le give-back est mesurable (17.5 % des trades, −$178/trade) mais leur
   capture par MFE-floor sacrifie davantage de gros gagnants — voir Phase 2 H4.

Les hypothèses retenues sont listées dans `OBSERVATIONS.md` avec leur source
chiffrée (obs-EX.W.1 → H6, obs-EX.L.1 → H1/H2, obs-EX.L.2 → H4/H7, etc.).

---

## 3. Phase 2 — A/B tests (cœur du travail)

Tous les sweeps tournent **HMASSLOsciV3LabExitV1** avec un seul flag toggleable
entre OFF (= V3 strict, sanity test au cent près) et ON. Les baselines ne sont
**jamais** modifiées entre OFF et ON. Logs : `phase2_hypotheses/logs/NN_*.{log,json}`.

### H1 — `lab_exit_fast_cross_only` (EX, angle L)

**Mécanisme.** OR `hw_cross_over/under` aux bars `fast_hma_exit_long/short` →
V3 chain (arm + hw_cross) fire la fermeture sur la même bar.

| Preset | OFF PnL | OFF DD | ON PnL | ON DD | ΔPnL | ΔDD | ΔP/DD | ΔWR | N off/on |
|--------|--------:|-------:|-------:|------:|-----:|----:|------:|----:|---------:|
| MNQ_v5 | $68,765 | $1,579 | $56,731 | $3,786 | **−$12,033** | +$2,207 | −28.6 | −1.4 % | 1241/1308 |
| MGC_v3 | $44,692 | $1,944 | $36,888 | $2,051 | **−$7,804** | +$108 | −5.0 | +0.4 % | 865/869 |

**Verdict : REJECT.** Couper l'attente HW détruit l'edge sur les 2 presets ;
le DD MNQ explose (× 2.4). Confirme obs-EX.L.1 mais réfute le scénario optimiste.

### H2 — `lab_exit_hw_only_if_profit` (EX, angle L) — **NOT TESTED**

Interprétation fidèle du brief : *« Attendre la HW (V3 default), à l'arrivée de
la HW, ne fermer que si in-profit, sinon laisser courir »*.

**Pourquoi non testable sans refonte moteur**. Le simulateur `v3_fast_hma_ssl`
mode :
- ferme la position à la séquence `fast_hma_exit → pending_final_exit → hw_cross_any`
  (`src/engine/simulator.py:1188-1206`),
- **avant** de regarder le slot `partial_close_long/short` (`simulator.py:1262`).

Le partial slot vérifie déjà « in profit » (`close_price > pos.entry_price`,
`simulator.py:1268`) — c'est le hook que le brief suggère d'exploiter. Mais
quand on injecte `partial_close |= hw_cross_*` avec `tp1_partial_pct = 1.0`,
la fermeture Canal Exit fire **avant** la vérification du partial à la même bar
et la position est déjà clôturée. L'injection est un no-op.

L'autre direction (désactiver `hw_cross_over/under` pour empêcher la Canal Exit
de fire, et déléguer entièrement la fermeture au partial slot) a été essayée
comme side-experiment ; elle casse la machine V3 de close (les trades en perte
restent ouverts jusqu'à l'auto-close 22:00) et perd **−$35,836 (MNQ)** /
**−$25,840 (MGC)** — chiffres dans `logs/02_ex_hw_only_if_profit.{log,json}`.
Ce side-experiment est un **vrai findings** : il quantifie que le path
in-loss-HW-close de V3 transporte ~$30k d'edge cross-asset.

**Statut HYPOTHESES.md** : NOT TESTED (hors quota). Implémentation propre =
ajouter un hook `block_in_loss_v3_close` dans le simulateur (mission interdit
de toucher au moteur). Candidate pour itération avec budget moteur.

### H3 — `lab_exit_on_canal_flip` (EX, angle L)

**Mécanisme.** OR `fast_hma_exit + hw_cross` aux bars `hma_flip_down/up` (contra
trade direction).

| Preset | OFF PnL | OFF DD | ON PnL | ON DD | ΔPnL | ΔDD | ΔP/DD | ΔWR |
|--------|--------:|-------:|-------:|------:|-----:|----:|------:|----:|
| MNQ_v5 | $68,765 | $1,579 | $47,215 | $3,782 | **−$21,549** | +$2,203 | −31.1 | −1.2 % |
| MGC_v3 | $44,692 | $1,944 | $26,390 | $2,624 | **−$18,301** | +$681 | −12.9 | −2.6 % |

**Verdict : REJECT.** Confirme obs-EX.L.3 : sortir au flip cap le tail. Pire que H1.

### H4 — `lab_exit_mfe_floor_r` + `_trigger_r` (EX, angle W+L, 5 variants)

**Mécanisme.** Tracker MFE bar-par-bar dans la stratégie. Une fois MFE ≥
`trigger_r` × initial_risk atteint, déclencher partial 100 % si le prix retombe
à `entry + floor_r × risk` (long) / `entry − floor_r × risk` (short).

| Preset | Variant | ΔPnL | ΔDD | ΔP/DD |
|--------|---------|-----:|----:|------:|
| MNQ_v5 | trig1.0_floor0.3 | −$6,084 | +$1,456 | −22.9 |
| MNQ_v5 | trig1.0_floor0.5 | −$6,254 | +$1,730 | −24.7 |
| MNQ_v5 | trig1.5_floor0.5 | −$7,068 | +$1,459 | −23.2 |
| MNQ_v5 | trig1.5_floor1.0 | −$5,966 | +$1,266 | −21.5 |
| MNQ_v5 | trig2.0_floor1.0 | −$8,193 | **+$0** | −5.2 |
| MGC_v3 | trig1.0_floor0.3 | −$6,909 | +$248 | −5.8 |
| MGC_v3 | trig1.0_floor0.5 | −$8,242 | −$76 | −3.5 |
| MGC_v3 | trig1.5_floor0.5 | −$5,030 | +$250 | −4.9 |
| MGC_v3 | trig1.5_floor1.0 | −$3,134 | −$3 | −1.6 |
| MGC_v3 | trig2.0_floor1.0 | **−$1,156** | +$126 | −2.0 |

**Verdict : REJECT.** L'intuition (capturer le give-back) est numériquement
correcte (les give-backs identifiés en Phase 1 sont coupés) mais le **coût des
winners coupés trop tôt** dépasse partout. Le variant trig2.0_floor1.0 maintient
le DD MNQ identique ($1,579) au prix de −$8k de PnL — preuve directe que la
queue droite (gros gagnants au-delà de 2R) est l'edge dominant et qu'on ne
peut pas la couper sans casser le ratio.

### H5 — `lab_pt_on_fast_cross_pct` (PT, angle W, 6 variants)

**Mécanisme.** Partial X % à `fast_hma_exit_*` (le simulateur gate sur in-profit).

| Preset | Variant | ΔPnL | ΔDD | ΔP/DD |
|--------|--------:|-----:|----:|------:|
| MNQ_v5 | 10 % | **+$1,684** | +$1,413 | −20.0 |
| MNQ_v5 | 15 % | +$1,435 | +$1,413 | −20.1 |
| MNQ_v5 | 20 % | +$1,285 | +$1,413 | −20.1 |
| MNQ_v5 | 25 % | +$1,225 | +$1,429 | −20.3 |
| MNQ_v5 | 50 % | +$240 | +$1,455 | −20.8 |
| MNQ_v5 | 75 % | −$862 | +$1,461 | −21.2 |
| MGC_v3 | 10 % | −$4,477 | +$334 | −5.3 |
| MGC_v3 | 25 % | −$4,737 | +$330 | −5.4 |
| MGC_v3 | 75 % | −$5,212 | +$150 | −4.1 |

**Verdict consolidé : MIXED → REJECT (cross-asset strict).** Seule hypothèse à
produire un PnL positif sur MNQ FULL, mais la DD inflate de +$1,400 quel que
soit le pct (10-75 %) — événement structurel concentré sur **une bar** où le
partial-then-resume engendre un creux plus profond que V3. **Walk-forward
détaillé en § 5 ci-dessous : MNQ TEST_H2 (out-of-sample) donne ΔPnL = +$1,319
ET ΔDD = −$154** — les 2 positifs. À ré-investiguer dans une campagne avec
plus de données out-of-sample. MGC perd partout → cross-asset KO.

### H6 — `lab_pt_on_canal_flip_pct` (PT, angle L, 2 variants)

**Mécanisme.** Partial X % à `hma_flip_down` (long) / `hma_flip_up` (short),
in-profit gate.

| Preset | Variant | ΔPnL | ΔDD | ΔP/DD |
|--------|---------|-----:|----:|------:|
| MNQ_v5 | 25 % | −$2,832 | +$1,022 | −18.2 |
| MNQ_v5 | 50 % | −$3,842 | +$472 | −11.9 |
| MGC_v3 | 25 % | −$5,512 | +$797 | −8.7 |
| MGC_v3 | 50 % | −$5,801 | +$797 | −8.8 |

**Verdict : REJECT.** Le flip-as-partial conserve le défaut du flip-as-exit
(cap-le-tail) avec moins d'amplitude. Pire que ne rien faire.

### H7 — `lab_pt_on_mfe_r_pct` + trigger (PT, angle L, 4 variants)

**Mécanisme.** Tracker MFE ; quand MFE ≥ `trigger_r` × risk, partial X %.

| Preset | Variant | ΔPnL | ΔDD | ΔP/DD |
|--------|---------|-----:|----:|------:|
| MNQ_v5 | 25 % @ 0.5R | −$6,524 | +$1,879 | −25.6 |
| MNQ_v5 | 25 % @ 1.0R | −$2,773 | +$2,081 | −25.5 |
| MNQ_v5 | 50 % @ 1.0R | −$4,079 | +$2,012 | −25.5 |
| MNQ_v5 | 50 % @ 1.5R | −$2,496 | +$1,171 | −19.5 |
| MGC_v3 | 25 % @ 0.5R | −$18,947 | +$503 | −12.5 |
| MGC_v3 | 25 % @ 1.0R | −$7,878 | +$300 | −6.6 |
| MGC_v3 | 50 % @ 1.0R | −$8,254 | +$218 | −6.1 |
| MGC_v3 | 50 % @ 1.5R | −$5,769 | +$227 | −5.1 |

**Verdict : REJECT.** Locker au MFE seuil sacrifie le run des gros winners ;
le tail de PnL > la queue défensive sur les 2 presets.

---

## 4. Phase 3 — Combinaisons

Avec **aucune hypothèse KEEP**, le périmètre des combos est restreint. Tests
réalisés :

1. **Finer sweep H5 (10/15/20 %)** — voir § H5 ci-dessus. Le DD inflate de
   manière constante (+$1,413) sur MNQ → événement structurel non éliminable
   par la valeur du pct.
2. **Combo H5 25 % + H7 50 %@1.5R** sur les 2 presets :
   - MNQ : ΔPnL = −$3,860 / ΔDD = +$1,079 → REJECT.
   - MGC : ΔPnL = −$8,960 / ΔDD = +$63 → REJECT.

**Aucun `winner_v6_MNQ.json` / `winner_v4_MGC.json` produit.** La mission le
permet (« sinon le rapport explique pourquoi aucune combinaison ne bat les
baselines »). Justification : (a) chaque hypothèse seule détruit le ratio P/DD
sur ≥1 preset, (b) les combos additionnent les dégradations sans synergie
positive observée, (c) le walk-forward (§ 5) confirme que le seul candidat
moins-mauvais (H5 25 % MNQ) n'est pas robuste cross-asset.

---

## 5. Phase 4 — Validation walk-forward

Split 50/50 chaque période (TRAIN_H1 / TEST_H2). Le seul candidat avec un
signal PnL positif sur la période FULL (H5 25 % MNQ) est validé.

| Asset | Fold | V3 PnL | V3 DD | H5_25 ΔPnL | H5_25 ΔDD | H5_10 ΔPnL | H5_10 ΔDD |
|-------|------|-------:|------:|-----------:|----------:|-----------:|----------:|
| MNQ_v5 | FULL | $68,765 | $1,579 | +$1,225 | +$1,429 | +$1,684 | +$1,413 |
| MNQ_v5 | TRAIN_H1 | $41,683 | $1,579 | −$93 | +$1,429 | +$755 | +$1,413 |
| **MNQ_v5** | **TEST_H2** | $27,082 | $2,337 | **+$1,319** | **−$154** | **+$930** | **−$154** |
| MGC_v3 | FULL | $44,692 | $1,944 | −$4,737 | +$330 | −$4,477 | +$334 |
| MGC_v3 | TRAIN_H1 | $17,109 | $1,944 | −$3,658 | +$330 | −$3,380 | +$334 |
| MGC_v3 | TEST_H2 | $27,583 | $1,997 | −$1,079 | −$28 | −$1,097 | −$28 |

**Lecture critique.**

- **MNQ TEST_H2** : H5 25 % et H5 10 % améliorent à la fois PnL et DD sur la
  seconde moitié. L'événement DD problématique de la période FULL est concentré
  dans **TRAIN_H1**. Si cet événement n'est pas représentatif du futur,
  H5 deviendrait KEEP sur MNQ. **Mais c'est une déduction, pas une preuve** —
  la fold unique 50/50 n'est pas une validation out-of-sample suffisante.
- **MGC** : H5 perd dans les 3 folds (PnL), DD à peu près stable. Pas
  d'ambiguïté → REJECT MGC.
- Le critère cross-asset strict reste violé (MGC échoue partout). Verdict
  consolidé : **REJECT**, avec recommandation de re-tester H5 en isolation
  MNQ-seule dans une campagne dédiée si plus de données out-of-sample
  deviennent disponibles.

---

## 6. Limites & risques

1. **H2 non implémentable sans modif moteur.** Le hook nécessaire serait un
   flag `gate_v3_close_on_in_profit` dans `SimulatorConfig`, conditionnel à
   `pos.side` et `close_price` vs `pos.entry_price` à la bar `hw_cross_any`.
   La mission interdit de toucher au moteur. Candidate pour campagne moteur
   dédiée.

2. **`get_simulator_settings` collapse de H5 et H7 en combo.** L'implémentation
   actuelle (`hma_ssl_osci_v3_lab_exit_v1.py:122-136`) prend `max(h5_pct, h7_pct)`
   pour `tp1_partial_pct`. Quand H5 25 % et H7 50 % @ 1.5R sont actifs ensemble,
   le partial slot tire 50 % à *chaque* trigger (fast cross OU MFE seuil), pas
   25 % + 25 %. La combo testée en Phase 3 est donc « partial 50 % sur
   l'union {fast_cross, MFE ≥ 1.5R} », pas un vrai mix de pourcentages
   différents. Le simulateur ne supporte qu'un seul `tp1_partial_pct`. Non
   corrigé car aucune combo MIXED-MIXED candidate ne le requérait. Documenter
   pour itération future.

3. **MFE tracking strategy-side (H4, H7) over-counts.** Le tracker MFE dans
   la stratégie suppose qu'un signal d'entrée = une position ouverte ; il
   ignore les blackouts, cooldowns, et lock multi-strat. Le simulateur a
   l'autorité finale via `partial_close + in_profit gate`, donc les
   faux-positifs ne dégradent pas les baselines (vérifié par sanity test),
   mais ils peuvent faire fire un partial sur une « ombre » de trade que le
   simulateur n'aurait pas ouvert. Effet faible (les sweeps montrent un
   nombre de trades quasi identique à V3, +1 à +25 selon variant), mais
   non nul.

4. **Asymétrie H1/H3 cross-preset.** MNQ a `block_loss_exit_before_partial=False`
   (close inconditionnel), MGC `=True` (gating in-loss). Le Lab ne modifie pas
   ce param — donc H1/H3 sur MGC restent partiellement gated par V3 (canal
   break fallback prend le relais). Documenté en OBSERVATIONS.md ; non corrigé
   car toucher à `block_loss_exit_before_partial` est un tuning V3, hors
   périmètre Lab.

5. **2 presets de référence seulement.** Le critère cross-asset strict
   demandé par la mission est très exigeant sur n=2. Une hypothèse MIXED sur
   un sample n=2 reste potentiellement valide sur d'autres assets non testés
   ici (MES, MGC alt configs, etc.). Pour pousser plus loin il faudrait
   répliquer la campagne avec ≥ 4 presets de référence ; ce n'est pas le
   périmètre actuel.

6. **Sample size variants H4/H7.** Les variants extrêmes (H7 25 % @ 0.5R) firent
   beaucoup de partials (1241 → 1270 trades MNQ ; 865 → 887 MGC) — l'effet
   pourrait être dominé par quelques trades pivots. Non explicitement vérifié
   par bootstrap ; les sweeps multi-valeurs adjacent (25 % @ 1.0R, 50 % @ 1.5R)
   convergent dans la même direction → on n'est pas sur un pic isolé.

---

## 7. Pistes pour itération suivante

1. **H5 sur MNQ uniquement, avec out-of-sample plus large.** La signature
   walk-forward TEST_H2 (ΔPnL +$1,319, ΔDD −$154) est le seul signal positif
   identifié dans cette campagne. À re-tester en cross-validation k-fold
   (k ≥ 3) avec une période étendue (ex. + 1 mois post-end). Si robuste → un
   `winner_v6_MNQ.json` avec H5 10-25 % serait justifié.

2. **Hypothèse H2 « HW only if profit » sur version moteur 2.0.** Ajouter
   `SimulatorConfig.v3_in_loss_close_gate: bool`. Coût d'implémentation
   estimé : ~30 lignes dans `_process_close_based_exits`, + 1 entrée dans la
   factory. Validation : doit reproduire V3 exact quand False (sanity).

3. **Régime-conditional exits** (obs-EX.W.2). MNQ_FAST_IN_RED capture l'edge
   dominant ($76.9k vs $48.7k FAST_IN_GREEN). Une hypothèse conditionnelle
   sur `canal_green` au moment de l'entrée pourrait moduler l'exit (ex.
   garder HW wait en RED, autoriser fast-only en GREEN). Combinatoire ×2
   par hypothèse → réservé à une campagne dédiée.

4. **Time-based exit** (H5/H2 hybride avec timeout). Si bars_fast_to_hw a une
   queue longue (à vérifier dans `exits_ALL.csv`), forcer un fallback au cross
   rapide après N bars depuis l'arming pourrait couper la queue gauche sans
   perdre le tail droit. Le flag `lab_exit_fast_cross_after_bars` est déjà
   présent dans le Lab (default = 0) — sweep possible dans une itération
   suivante.

5. **Asymétrie long/short.** MNQ_SHORT (n=595, $49k de PnL) a un Δ HW − fast
   moyen de **+$25.2** vs MNQ_LONG (n=646, $20k, +$8.5). L'amplificateur HW est
   majoritairement sur SHORT. Une hypothèse `lab_exit_*_short_only` pourrait
   sélectionner où H5/H1 s'applique. Non couvert ce cycle.

---

## 8. Reproduction

```bash
source venv/bin/activate

# Sanity (obligatoire avant toute autre étape) :
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase2_hypotheses/00_sanity_lab_equals_v3.py

# Phase 1 (dump des trades enrichis) :
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase1_observation/run_analysis.py

# Phase 2 (un sweep par hypothèse) :
for f in scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase2_hypotheses/0[1-9]_*.py; do
    python "$f"
done

# Phase 3 (combos) :
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase3_combinations/01_h6_fine_sweep.py

# Phase 4 (walk-forward) :
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase4_walkforward.py

# Vérification que Lab(defaults) reproduit V3 au cent près :
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/verify_winner.py
```

Tous les artefacts sont dans `scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/`.
La stratégie Lab dans `src/strategies/hma_ssl_osci_v3_lab_exit_v1.py` n'a
**aucun** flag ON par défaut (= V3 strict). Le fichier `hma_ssl_osci_v3.py` n'a
pas été modifié. Le simulateur `src/engine/simulator.py` n'a pas été modifié.
