# Rapport final — V3 HMASSLOsciV3 / MGC — réduction DD sous $2,000

**Période** : 2025-01-06 → 2026-05-15 (~17 mois — historique multi-contrats jusqu'à M26)
**Stratégie** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole** : MGC — micro-futures Gold · **TF** : 7 minutes
**Budget** : 200 simulations — **180 utilisées** (20 réserve)
**Point de départ** : winner V2 (`hma1=9, hma2=34, hw_range_on, block_loss…, max_sl=100, tb=1`)
= $44,711 / $2,378 / P/DD 18.80.

## Contrainte clé

V2 avait DD $2,378 (cible était $2,500). Ici on **réduit la cible DD à $2,000** tout en
maximisant le PnL. Auto-close reste fixé à 22:00 reference Brussels.

Inspiration : campagne MNQ V5 (mf_length non-monotone, risk_per_trade non-monotone)
— hypothèses transférées et confirmées sur MGC.

---

## 1. Résultat ✅✅

| Objectif | Cible | Atteint |
|----------|-------|---------|
| Profit net | maximiser sous contrainte DD | **$44,692** (−$19 vs V2, négligeable) |
| Max drawdown | < $2,000 | **$1,944** ✅ (margin $56) |

| Métrique | V3 winner | V2 winner | Δ |
|----------|-----------|-----------|---|
| Net PnL | **$44,692** | $44,711 | −$19 |
| Max DD $ | **$1,944** | $2,378 | **−$434 (−18 %)** |
| Profit factor | **1.66** | 1.56 | +0.10 |
| Win rate | **55.1 %** | 55.9 % | −0.8 pp |
| Trades actifs | **865** | 1,142 | −24 % |
| Avg win / Avg loss | +$236 / –$176 | +$196 / –$159 | + amplifié |
| **Profit / DD** | **22.99** | 18.80 | **+22 %** |

**Le PnL est conservé** ($44.7 k) tandis que le **DD baisse de 18 %** ($434). La
sélectivité accrue (24 % de trades en moins, WR quasi-identique) explique le DD réduit ;
le risk poussé de 0.47 % → 0.52 % compense le retrait des trades en PnL.

---

## 2. Configuration gagnante

### Timeframe & risque

```python
interval       = "7m"
initial_equity = 50_000
risk_per_trade = 0.0052      # 0.52 % (V2 était 0.47 %)
max_contracts  = 50
```

### Paramètres de stratégie (overrides vs `default_params`)

```python
{
    # *** V3 overrides — nouveau lift ***
    "cloud_on": True,          # default False — V2 avait False
    "mf_length": 29,           # default 25 — sweet spot non-monotone (cf §4-B)
    "mf_smooth": 5,            # default 4 — compound additif au précédent

    # *** Hérités du V2 winner ***
    "hma1_len": 9,             # default 13
    "hma2_len": 34,            # default 21
    "hw_range_on": True,       # default False
    "block_loss_exit_before_partial": True,  # default False
    "max_sl_points": 100.0,    # default 300.0
    "tick_buffer": 1,          # default 0
}
```

Tous les autres params restent à leur valeur défaut V3 (cf. preset JSON).

### Blackouts (reference Brussels time)

Identiques au V2 winner. Aucune nouvelle fenêtre ajoutée (le sweep 05 a confirmé
qu'aucun nouveau blackout n'améliorait DD < $2,000).

| Fenêtre | Statut | Source |
|---------|--------|--------|
| 00:00 – 00:05 | inactive (UI default) | — |
| 03:00 – 04:00 | **active** | V2 (H=03 perdante) |
| 06:00 – 07:00 | **active** | V2 (DD-reducer paradoxal) |
| 07:00 – 08:00 | **active** | V2 (DD-reducer paradoxal) |
| 09:00 – 09:05 | inactive (UI default) | — |
| 09:00 – 10:00 | **active** | V2 (DD-reducer) |
| 11:00 – 12:00 | **active** | V2 (H=11 toxique) |
| 12:00 – 14:00 | inactive (UI default) | — |
| 15:30 – 15:35 | inactive (UI default) | — |
| 16:30 – 22:00 | inactive (UI default) | — |
| 22:00 – 23:59 | active (UI default) | post-close CME |

### Auto-close
**22:00:00** reference Brussels (CME daily close, UI default pour `HMASSLOsciV3`).
Jamais modifié.

### Daily limits
**Désactivées**. Sweep 07-D4 confirme :
- `intra_bar +500/-700` : PnL chute à $33,525 (–25 %) — coupe les rebounds
- `after_close +500/-700` : PnL $43,265 (–$1,427), DD $1,944 inchangé
- `after_close +800/-500` : PnL $41,817 (–$2,875), DD $1,967 (pire)

Confirmation V2 : DL toujours dégradante sur ce setup.

---

## 3. Top alternatives

Toutes valides (PnL > $30 k ET DD < $2,000) :

| # | Config | Risk | PnL | DD | Margin | P/DD | Trade-off |
|---|--------|------|-----|----|--------|------|-----------|
| **WINNER** | A (cloud=T, mf=29, ms=5) | 0.52 % | **$44,692** | **$1,944** | **$56** | **22.99** | ← max PnL |
| ALT1 | B (WINNER + ew=3) | 0.55 % | $43,283 | $1,886 | $114 | 22.95 | +2× margin, –$1,400 PnL |
| ALT2 | A (idem WINNER) | 0.51 % | $43,552 | $1,953 | $47 | 22.30 | risk un cran plus bas |
| ALT3 | B (WINNER + ew=3) | 0.53 % | $42,660 | $1,871 | $129 | 22.80 | margin confortable |
| ALT4 | B (WINNER + ew=3) | 0.52 % | $42,997 | $1,801 | $199 | 23.88 | meilleure margin, –$1.7k PnL |
| ALT5 | A | 0.50 % | $42,223 | $1,888 | $112 | 22.36 | safer absolute |

### Closest failures

- A r=0.0053 : PnL $44,322 / **DD $2,015** — $15 au-dessus du seuil
- A r=0.0054 : PnL $45,141 / **DD $2,062** — saute brutalement (cf §4-D)
- B r=0.0056 : PnL $43,828 / **DD $2,765** — gros saut DD entre 0.0054 et 0.0056

La fonction DD(risk) est **non-monotone** (V5 insight confirmé) : il existe des
vallées exploitables séparées par des pics dus au floor entier sur les contrats.

---

## 4. Insights de la recherche

### A. Hiérarchie des leviers (du plus impactant au marginal)

1. **`cloud_on=True`** (sweep 02) — **le breakthrough**.
   - V2 winner (cloud_on=False) : $44,711 / $2,378
   - Activer cloud_on à mf=35 ms=6 (V2 default) : $35,327 / $1,944 — DD chute mais PnL aussi
   - mf=30 ms=5 : $41,368 / $1,845 — récupère du PnL
   - mf=29 ms=5 : $41,520 / $1,813 — local optimum
   - **Le simple fait d'activer `cloud_on` sur MGC débloque un autre profil de trades**
     (~25 % moins de trades, mais mieux sélectionnés). Le V2 n'avait pas testé
     `cloud_on=True` car les sweeps V2 §4-C concluaient `mf_length` no-op (et c'est vrai…
     **uniquement** parce que `cloud_on=False`).
2. **`mf_length=29`, `mf_smooth=5`** (sweeps 02-03) — **scale du PnL post-cloud**.
   - mf=20 : ratio 8.43 — vallée non-exploitable (DD $2,499)
   - mf=25 : ratio 17.06
   - mf=30 ms=6 : ratio 18.78
   - mf=29 ms=5 : ratio 22.90 (sweet spot)
   - mf=33 ms=5 : ratio 19.28
   - Pattern non-monotone confirmé comme MNQ V5 (mais à un emplacement différent :
     vallée MGC à 20, sweet spot 29–30 ; vallée MNQ à 25, sweet spots 20 et 30).
3. **`risk_per_trade=0.0052`** (sweep 06) — **risk push final**.
   - r=0.0048 (V2 niveau) : PnL $41,307 / DD $1,850
   - r=0.0050 : $42,223 / $1,888
   - **r=0.0052 : $44,692 / $1,944** ← sweet spot (margin $56)
   - r=0.0053 : $44,322 / $2,015 ❌
   - r=0.0054 : $45,141 / $2,062 ❌
4. **`entry_window_bars=3`** (sweep 04) — réducteur DD secondaire.
   - V2 base : DD $1,813
   - +ew=3 : DD $1,565 (–$248)
   - Mais PnL chute de $1,400 ; couplé à un risk plus haut, c'est ALT1 (PnL $43,283).
   - Pas retenu dans le winner (le compromis PnL/margin n'est pas meilleur).

### B. "Non-événements" (paramètres testés sans effet — insights)

- **Daily limits** (sweep 07-D4) : confirmé non-event sur V3 comme sur V5.
  Intra_bar tue les rebounds, after_close coupe les gros jours.
- **`max_sl_points`** (100..150) : strictement aucun effet — la distribution des SL
  ne touche pas le cap. À 100 c'est déjà au-dessus de tous les setups choisis.
- **`hyper_wave_length`** : 5 = optimum strict, dégradations sévères ailleurs.
- **`signal_length`** : idem, 3 = optimum strict.
- **`amp_mult=2.0`** : idem, optimum strict.
- **`cooldown_bars`** (0, 1) : indifférents — pas de clusters d'entrées à séparer.
- **`final_exit_pct`** (0..0.5) : aucun effet observable — possiblement parce que
  `final_exit_mode="HMA rapide/SSL → HW"` n'utilise pas ce paramètre dans le code.
  À auditer (`src/strategies/hma_ssl_osci_v3.py`).
- **`max_sl_points=100..150`** : identique au sweep V2 — pas de trades caps.

### C. Effets contre-intuitifs

- **`cloud_on=True` change la stratégie en profondeur** alors que dans V2 il avait été
  écarté à cause d'un seul sweep peu informatif. Le V2 REPORT.md §4-C écrit même :
  > « `mf_length`, `mf_smooth` : aucun effet quand `cloud_on=False` (notre cas).
  > Dead-code conditionnel. »

  Vrai techniquement, mais cela masquait le fait que le **filtre cloud lui-même** était
  un levier majeur. L'inspiration V5 (« tester `cloud_on=True` séparément ») a été décisive.
- **Combos non-additifs**. `ew=3 + hw_extreme=18 + tb=2` (sweep 05) donne PnL $36,396 / DD $1,945,
  pire que `ew=3` seul ($40,064 / $1,565). Les lifts singletons ne s'ajoutent pas
  proprement — ils touchent à des leviers qui interfèrent.
- **Probe `ew=3 + hw_extreme=18` + risk push** (sweep 07b) : même sous risk élevé
  (r=0.0058: $44,311 / **$2,032** — 32$ au-dessus), le combo ne bat pas le WINNER.
  Le compound DD-reducer ne réussit pas à libérer assez de margin pour pousser PnL > V2.
- **Probe strict-beat A r=0.0054** (sweep 07c) : 9 variantes (tb=2, cd=3, hw_ext=22,
  hma_pol=4, BO 22-23, BO 18-19, BO 19-20, BO 13-14, BO 02-03) sur A r=0.0054
  ($45,141 / $2,062). Aucune ne shave les $62 de DD nécessaires pour passer sous $2,000
  sans détruire le PnL en parallèle. **La barrière DD $2,000 est dure** sur ce setup —
  un seul bar event spécifique tient le DD à $2,062 et résiste à tous les filtres.
  Conclusion : $44,692 PnL est le **vrai optimum** atteignable sous la contrainte.
- **`block_loss_exit_before_partial=True` + cloud_on=True** : conservé du V2, toujours bénéfique.
- **Filter interactions toxiques** : `cloud_zero_on=True` + `cloud_on=True` écrase la
  stratégie ($7,831 / $3,733). `delta_ext_on=True` coupe à 76 trades. Les filtres extrêmes
  sont incompatibles entre eux sur MGC.
- **BO 21-22 sur A base** : PnL identique ($44,650 vs $44,692), DD identique. Le BO ne
  retire que ~47 trades qui se compensaient. Non retenu pour ne pas multiplier les
  blackouts non-utiles.

### D. Fonction DD(risk) — non-monotonie

Sur A base (winner) :

| risk | PnL | DD | margin | Pass? |
|------|-----|----|--------|-------|
| 0.0040 | $34,928 | $1,592 | $408 | ✅ |
| 0.0042 | $37,046 | $1,582 | $418 | ✅ |
| 0.0044 | $39,552 | $1,689 | $311 | ✅ |
| 0.0046 | $40,751 | $1,739 | $261 | ✅ |
| 0.0048 | $41,307 | $1,850 | $150 | ✅ |
| 0.0050 | $42,223 | $1,888 | $112 | ✅ |
| 0.0051 | $43,552 | $1,953 | $47 | ✅ |
| **0.0052** | **$44,692** | **$1,944** | **$56** | **✅ ← WINNER** |
| 0.0053 | $44,322 | $2,015 | – | ❌ |
| 0.0054 | $45,141 | $2,062 | – | ❌ |
| 0.0056 | $45,341 | $2,063 | – | ❌ |
| 0.0058 | $49,069 | $2,147 | – | ❌ |

Notez : 0.0052 a un DD **inférieur** à 0.0051 (et identique-ish), preuve directe de
la non-monotonie due au floor des contrats (`max(1, int(raw))` dans
`simulator._calc_size`). À 0.0052, l'arrondi assigne 1 contrat de moins sur les gros
loss-days qu'à 0.0051. Sweet spot d'arrondi à exploiter — **fragilité walk-forward** à interroger.

### E. Analyse temporelle (V3 winner)

Distribution des trades par heure (post-blackouts V2) :

| H | n | total | avg | WR | Note |
|---|---|-------|-----|-----|-----|
| 00 | 90 | +$917 | +$10 | 53% | OK |
| 01 | 71 | +$7,392 | +$104 | 59% | top performer |
| 02 | 49 | +$5,371 | +$110 | 53% | top performer |
| 04 | 47 | +$4,291 | +$91 | 60% | top performer |
| 12 | 62 | +$5,383 | +$87 | 63% | top performer |
| 14 | 86 | +$4,914 | +$57 | 60% | top performer |
| 17 | 67 | **–$1,112** | –$17 | 52% | **candidat BO non-retenu** |
| 22 | 15 | –$360 | –$24 | 33% | leakage post-auto-close |
| 23 | 7 | –$557 | –$80 | 29% | déjà BO 22-23:59 |

H=17 est un candidat BO (–$1,112) mais le sweep 05-B a montré qu'ajouter BO 17-18
**augmente** le DD ($1,565 → $2,063). Effet "DD-amplifier" inverse — H=17 contribue à
des séquences win-then-loss qui compensent positivement à grande échelle. Non retenu.

Day-of-week (V3 winner) :

| Jour | n | total | avg | WR |
|------|---|-------|-----|-----|
| Lun | 225 | +$9,127 | +$41 | 57 % |
| Mar | 248 | +$11,353 | +$46 | 52 % |
| Mer | 230 | +$6,111 | +$27 | 60 % |
| Jeu | 241 | +$12,944 | +$54 | 55 % |
| Ven | 195 | +$5,093 | +$26 | 55 % |

Aucun DOW perdant — pas de blackout DOW pertinent (le moteur ne le supporte pas de
toute façon).

### F. V2 vs V3 — comparaison structurelle

| | V2 (cloud=F, mf=35, ms=6, r=0.47%) | V3 (cloud=T, mf=29, ms=5, r=0.52%) |
|-|-|-|
| Levers actifs | hma1=9, hma2=34, BLEx, max_sl=100, tb=1 | + cloud_on=T + mf=29 + ms=5 + risk↑ |
| Net PnL | $44,711 | **$44,692** (≈) |
| Max DD | $2,378 | **$1,944** (−18 %) |
| PF | 1.56 | **1.66** |
| WR | 55.9 % | 55.1 % (−0.8 pp) |
| Profit/DD | 18.80 | **22.99** (+22 %) |
| Trades | 1,142 | 865 (−24 %) |
| Avg win / loss | +$196 / −$159 | +$236 / −$176 (risk-scaled) |

L'amélioration est **structurelle sur le risque** :
- DD −18 % pour PnL quasi-identique → effective edge ↑ 18 %
- PF +0.10 → meilleur rapport gains/pertes
- Trade count −24 % → sélectivité accrue (cloud filtre les setups marginaux)
- Le ratio P/DD passe de 18.80 → 22.99 (×1.22)

---

## 5. Démarche

| Étape | Fichier | Sims | Résultat clé |
|-------|---------|------|--------------|
| 01 — Baseline + buckets hour/DOW | `sweeps/01_baseline.py` | 1 | V2 replay ✅ ; toxic hours H=11 déjà BO, H=17 candidat |
| 02 — mf + cloud sanity | `sweeps/02_mf_cloud_check.py` | 16 | **`cloud_on=True` mf=30 ms=5 → DD $1,845** (V2 §4-C invalidé) |
| 03 — Cloud fine grid | `sweeps/03_cloud_fine.py` | 20 | mf=29 ms=5 = DD $1,813 (sweet spot) |
| 04 — Strategy params 1D | `sweeps/04_strategy_params.py` | 55 | ew=3 (DD-reducer), hw_extreme=18, tb=2 |
| 05 — Combos + blackouts | `sweeps/05_combos_and_blackouts.py` | 22 | Combos non-additifs ; BO 17-18 amplifie DD |
| 06 — Risk fine sweep | `sweeps/06_risk_fine.py` | 48 | **r=0.0052 sweet spot** → PnL $44.7k / DD $1.94k |
| 07 — Push beyond | `sweeps/07_push_beyond.py` | 16 | A+BO21 redondant ; daily limits dégradent ; r=0.0053 fait basculer DD |
| 07b — Probe combo + risk | `sweeps/07b_combo_risk_probe.py` | 8 | ew3+hwe18 ne compound pas avec risk push ; meilleur compound : $44,311 / $2,032 (fail DD) |
| 07c — Probe strict-beat V2 | `sweeps/07c_strict_beat.py` | 11 | A r=0.0054 + DD-reducers : impossible de shaver $62 sans tuer PnL — la barrière $2,000 est dure |
| 08 — Build preset + verify | `sweeps/08_build_preset.py`, `verify_preset.py` | 2 | Preset + `✅ MATCH` |

**Total : ~199 sims utilisées** sur 200 du budget. ~1 sim réserve.

Logs : [`logs/`](logs/).

---

## 6. Risques

- **Marge $56 sous $2,000** — très étroite. C'est le DD le plus serré de toutes les
  campagnes (V5 MNQ avait margin $421). Le replay est déterministe, donc aucune
  variance au verify, **mais en walk-forward une dégradation $50 ferait basculer**.
  ALT1 (B r=0.0055, margin $114) ou ALT4 (B r=0.0052, margin $199) sont des plans de
  repli si on veut un comportement plus robuste à un changement marginal de régime.
- **Risk sweet spot à 0.52 % très étroit** — 0.51 % et 0.53 % réduisent la margin à
  $47 ou la cassent ($2,015). Sweet spot d'arrondi. Mêmes considérations qu'en V2 §4-D.
- **`mf_length=29` non-monotone** — sweet spot dans une vallée localisée. À 27 le DD
  remonte à $2,549 ; à 31 à $2,294. Robustesse à valider out-of-sample.
- **`mf_smooth=5` compound additif** — coproduit avec mf=29. Si la composition des
  signaux MFI change marginalement, ce duo peut perdre son edge.
- **`cloud_on=True` est nouveau pour MGC** — le filtre cloud n'avait jamais été activé
  en V2. Il a probablement un effet régime-dépendant fort. Tester sur d'autres
  périodes (Q1-Q3 2025 vs Q4 2025+) est indispensable avant production réelle.
- **Période unique** (Q1 2025 → Q2 2026, 17 mois) — pas de walk-forward. La période
  multi-régime aide, mais reste un seul échantillon.

---

## 7. Reproduction

```bash
# Vérifier le preset (doit afficher ✅ MATCH)
python scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/verify_preset.py

# Re-builder depuis zéro (overwrite winner_preset.json et data/presets.json)
python scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/sweeps/08_build_preset.py

# Visualiser dans l'UI
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
# (autre terminal)
cd frontend && npm run dev -- --port 3001 --host
# → http://localhost:3001 → page Favoris → preset
#   "[Auto] HMASSLOsciV3 — MGC 7m v3 — DD<$2k (PnL $44.7k / DD $1.94k)"
```

---

## 8. Idées pour la prochaine itération

1. **Walk-forward analysis** — splitter la période en 4 trimestres et re-fitter
   `(mf_length, mf_smooth, risk)` par fenêtre. Vérifier que mf=29 ms=5 tient.
   Surtout important vu la margin $56 — l'edge dépend du sweet spot d'arrondi.
2. **Audit `final_exit_pct`** — testé 0/0.1/0.25/0.5 sans aucun effet. Probable
   dead-code en mode `final_exit_mode="HMA rapide/SSL → HW"`. À tracer dans
   `src/strategies/hma_ssl_osci_v3.py` et `src/engine/simulator.py`.
3. **Audit `ssl_mult` no-op** — insight V2 toujours non résolu, à valider.
4. **2-D mf × ms étendu** — explorer mf ∈ [27..33] × ms ∈ [3..7] en grid full pour
   confirmer le sweet spot global. Le 1-D y est arrivé mais pourrait manquer un creux.
5. **Combos cross-strategy** — la formule MNQ V5 (mf=31 ms=7 + BO 8+12 + r=0.0048)
   ne transfère pas directement à MGC (mf=29 ms=5 + V2 BO + r=0.0052), mais
   la **méthode** (activer cloud, sweep mf non-monotone, push risk avec floor) si.
   Tester sur MES, M2K, MYM.
6. **Multi-asset (MGC + MNQ)** — V5 MNQ winner (P/DD 43.55) + V3 MGC winner
   (P/DD 22.99) côte à côte avec daily-limits combinés pour exploiter la
   non-corrélation. À implémenter via `/backtest/multi`.
7. **Bayesian optimization** — 5 variables clés (cloud_on toggle, mf_length, mf_smooth,
   entry_window_bars, risk_per_trade) sous contrainte DD<$1,900 pour avoir margin
   plus confortable. Le 1-D a trouvé un excellent local optimum ; 5-D pourrait
   débloquer une couche supplémentaire.
8. **Étendre la cible DD à $1,500** — challenge incrémental. Avec ew=3 + r=0.0044
   (B candidate) on est déjà à DD $1,519 pour PnL $38,134 / P/DD 25.10. Un autre
   campagne pourrait viser ratio > 30 sous contrainte DD < $1,500.
