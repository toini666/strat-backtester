# HMASSLOsciV3 — analyse post-mortem & pistes d'évolution

**Date** : 2026-05-17
**Objectif** : comprendre ce qui cause les SL, comment les TP pourraient être améliorés, et quelles nouvelles façons d'interpréter les indicateurs valent d'être testées. Aucune modification de stratégie existante.

**Sources analysées** (3 presets gagnants, replay déterministe — PnL match exact des rapports) :

| Preset | Trades | Net PnL | Win-rate |
|--------|-------:|--------:|---------:|
| MNQ_v4 (single) | 1 389 | $50 770 | 46.1 % |
| MGC_v2 (single) | 1 142 | $44 711 | 55.9 % |
| MNQ_MGC (multi-asset) | 2 319 | $101 921 | 51.7 % |
| **Cumul** | **4 850** | **$197 402** | 51.0 % |

Outputs détaillés : `outputs/trades_*.csv`, `outputs/summary.json`. Le présent rapport synthétise les **9 insights actionnables** issus de la lecture trade-par-trade.

---

## Cadrage : où vient le PnL, où vient le DD ?

Décomposition des 4 850 trades par cause de sortie (cumul 3 presets) :

| Statut | n | PnL net | Avg / trade | WR | Avg bars in trade |
|--------|--:|--------:|------------:|---:|------------------:|
| Canal Exit | 2 994 | **+$435 754** | +$146 | 74.5 % | 11.5 |
| Auto-Close (profit) | 253 | +$45 399 | +$179 | 97.6 % | 21.3 |
| Auto-Close (loss) | 169 | −$10 761 | −$64 | 0 % | 18.1 |
| Stop Loss | 1 432 | **−$272 989** | −$191 | 0 % | 9.0 |
| End of Data | 2 | −$1 | — | — | — |

* **Canal Exit fait tout le PnL.** Le R moyen y est ~0.76 ; le WR 74.5 %.
* **Stop Loss est l'unique source de perte structurelle** ; +99 % du DD cumulé. R systématique = −1.0 (peu/pas de slippage).
* **Auto-Close (profit) génère $45 k bonus** quand un trade tient jusqu'à 22:00. WR = 97.6 % → c'est un compartiment de trades "tendance qui dure" extrêmement fiable.
* **Auto-Close (loss) ne pèse que −$11 k** → tenir un trade jusqu'à la cloche, même en flottant négatif modeste, est largement +EV.

Conclusion d'angle : **toutes les pistes d'amélioration doivent se mesurer en (réduction-SL) ou (Canal-Exit-mieux-timés).** Toucher aux TP partiels (`hw_partial_pct=0` dans les 3 winners) n'est pas la veine principale.

---

## Insight 1 — "Attendre 1 HW de plus avant de sortir" n'aide PAS

**Question utilisateur testée littéralement** : remplacer la sortie au prochain HW par la sortie au HW *suivant*.

**Mesure** : pour chaque Canal Exit, on calcule le R qu'aurait donné une sortie au close du premier HW APRÈS la sortie réelle ("shadow exit").

| Preset | n CE | ΔR moyen | Δ$ total si appliqué | Losers récupérés | Winners qui rendent |
|--------|----:|---------:|---------------------:|-----------------:|--------------------:|
| MNQ_v4 | 839 | +0.018 | **+$1 430** | 84 / 256 (33 %) | 262 / 583 (45 %) |
| MGC_v2 | 714 | −0.033 | **−$4 987** | 21 / 116 (18 %) | 308 / 598 (52 %) |
| MNQ_MGC | 1 441 | −0.002 | **−$2 328** | 96 / 342 (28 %) | 530 / 1 099 (48 %) |

* Sur MGC, attendre fait perdre **0.04R/trade**. Sur MNQ, gain quasi-nul (+$1.7/trade) noyé dans la variance.
* Le rapport est asymétrique : pour ~25 % de losers sauvés, ~48 % de winners donnent de la marge. La distribution écrase l'effet.

**Caveat méthodologique** : le `shadow_exit_r` suppose que le trade survit intact jusqu'au prochain HW — il ignore que le SL initial reste armé entre les deux HWs. Une partie des "losers récupérés" auraient en réalité été stoppés avant d'atteindre le HW suivant. Le biais joue dans le sens de **surestimer la récupération** ; la conclusion ("attendre ne paie pas") reste donc *a fortiori* valide, mais ne pas anchorer sur le chiffre "33 % récupérés".

**Proposition** : la règle "wait one more HW" en aveugle est mauvaise. Ce qui pourrait marcher : **wait IF specific condition** — p.ex. ne pas sortir au HW si le canal HMA pointe ENCORE dans notre sens (cf. Insight 5). À tester dans une **HMASSLOsciV4** (nouvelle classe, ne pas toucher v3) avec un toggle `delayed_exit_if_canal_aligned`.

---

## Insight 2 — La première barre est un piège : 187 trades ≤ 1 bar = −$26 k

| Bars in trade | n | PnL net | WR | Avg MFE_R | Avg MAE_R |
|--------------:|--:|--------:|---:|----------:|----------:|
| **≤ 1** | **187** | **−$25 944** | **6.4 %** | 1.32 | 1.21 |
| 2-3 | 1 004 | −$56 359 | 35.2 % | 0.48 | 0.74 |
| 4-6 | 1 229 | +$50 150 | 60.6 % | 0.96 | 0.67 |
| 7-12 | 1 144 | +$78 093 | 51.7 % | 1.42 | 0.74 |
| 13-24 | 694 | +$40 143 | 51.4 % | 1.39 | 0.79 |
| > 24 | 592 | +$111 317 | 68.4 % | 1.91 | 0.67 |

* **128 SL sur 187 (68 %)** des trades meurent dans la barre d'entrée.
* Avg MFE = 1.66R sur les SL ≤ 1 bar → le prix touche un wick favorable *avant* de revenir tuer le SL. Symptôme classique d'**entrée sur breakout puis fakeout intrabar**.
* Le bucket "2-3 bars" lui aussi est net négatif (WR 35 %). Tout ce qui se résout en ≤ 3 bars est statistiquement perdant.

**Proposition** :
1. **Cooldown effectif par sub-bar** : actuellement `cooldown_bars=1-3` mais le SL initial est posé sur la barre d'entrée. Tester un **filtre "wait-and-see"** : ne pas armer le SL avant le close de la barre d'entrée (déjà partiellement disponible via `tp1_execution_mode=bar_close_if_touched`, mais ce mode est inactif sur v3).
2. **Anti-chase filter** : refuser l'entrée si la barre courante a déjà bougé > X% (`max_candle_pct` existe mais à 0.9 % il filtre trop peu). Tester `max_candle_pct=0.3-0.5` dans une v4.

---

## Insight 3 — Le SL "court" est ce qui paye l'edge ; le SL "large" achète du WR mais pas de R

Quintiles de distance SL (en % du prix), tous trades confondus par preset :

**MNQ_v4** (sl_dist_pct):

| Bucket | n | Avg PnL | WR | Avg R exit |
|--------|--:|--------:|---:|-----------:|
| Q1 tight | 278 | **$88** | 34 % | **0.55** |
| Q2 | 278 | $13 | 42 % | 0.11 |
| Q3 | 277 | $29 | 47 % | 0.19 |
| Q4 | 278 | $21 | 50 % | 0.16 |
| Q5 wide | 278 | $32 | 57 % | 0.11 |

**MNQ_MGC** (combiné, cohérent) :

| Bucket | Avg PnL | WR | Avg R |
|--------|--------:|---:|------:|
| Q1 tight | **$98** | 42 % | **0.53** |
| Q2 | $22 | 47 % | 0.14 |
| Q5 wide | $42 | 60 % | 0.12 |

* Les setups à **SL serré** (HW cluster compact) ont un WR plus bas mais un R moyen **3-5×** plus élevé.
* Les setups à SL large gagnent souvent un peu mais en $ comptent peu (le sizing les réduit).
* Sur MGC le pattern est plat (sa nature plus mean-reverting amortit l'asymétrie).

**Proposition** : tester `max_sl_points` *plus agressif* sur MNQ (actuellement 300 pts). Sur MNQ_v4, passer à 150-200 pts éliminerait ~Q4-Q5 (perte de volume) mais améliorerait le R moyen. À fitter en v4 — ce n'est *pas* un changement de stratégie, juste un resserrement du filtre existant.

---

## Insight 4 — La vitesse du prochain HW post-entrée prédit la profitabilité

| Bars to first HW after entry | n | Avg PnL | WR | Avg R exit |
|----------------------------:|--:|--------:|---:|-----------:|
| 1 | 771 | −$10 | 32 % | −0.03 |
| 2 | 1 279 | −$16 | 38 % | −0.08 |
| 3 | 1 240 | $30 | 53 % | 0.13 |
| **4-5** | **1 224** | **+$98** | **67 %** | **+0.49** |
| **6-8** | **310** | **+$254** | **84 %** | **+1.45** |
| 9-12 | 24 | +$208 | 79 % | +1.24 |

* Si le prochain HW arrive en **1-2 bars**, c'est presque toujours un retournement de momentum contre nous → perte.
* Si le prochain HW arrive en **6-8 bars**, c'est une preuve de momentum soutenu → R moyen 1.45.
* **Cette signature ne dépend ni de l'asset ni du preset.** Elle est identique sur MNQ et MGC.

**Proposition (lourde, mais structurelle)** :
1. **Filtre d'entrée** : refuser l'entrée si un HW a crossé dans les `K` (e.g. 2) bars précédant le signal. Aujourd'hui `hw_dir_on=True` exige juste la direction du *dernier* HW, sans contrainte d'âge.
2. **"Confirmation post-entry"** : armer une sortie défensive si aucun mouvement favorable (price > entry_price si long) n'est observé après 2 bars. Plus défensif que le `hw_dir_on` actuel.
3. Idée pour une v4 : ajouter `hw_age_min: int` (bars depuis le dernier HW) au filtre `hw_dir_on`. Sweep 3-5 bars.

---

## Insight 5 — Canal HMA qui flippe pendant le trade = signal majeur (WR 63 % vs 35 %)

| `canal_flipped` (couleur change entry→exit) | n | Avg PnL | WR | Avg R |
|--------------------------------------------|--:|--------:|---:|------:|
| **False** (canal reste contre nous) | 1 958 | **−$40** | 35.5 % | **−0.17** |
| **True** (canal flippe dans notre sens) | 2 892 | **+$93** | 63.2 % | **+0.48** |

* La quasi-totalité du PnL net (~$180 k sur les ~$197 k) vient des trades où le canal change de couleur.
* Conséquence : la stratégie est **fondamentalement reversal** — on entre quand le canal est encore défavorable et on profite de son retournement.

**Proposition** :
1. Tester une **règle de Canal Exit conditionnelle** : si à l'instant du HW de sortie le canal NE s'est PAS encore retourné (`canal_green` n'a pas flippé depuis l'entrée), **différer** la sortie au prochain HW (= variant ciblé de la "wait one more HW" qui ne s'applique que dans ces cas).
2. **Filtre d'entrée pessimiste** : `min_bars_until_canal_flip_expected = ...` — refuser si la pente du canal indique que le flip prendrait > N bars (= reversal "lent" peu probable). Difficile à implémenter sans regarder dans le futur ; alternative : se restreindre à des canaux dont la pente actuelle pointe déjà vers le flip (cf. Insight 6).

---

## Insight 6 — Canal slope au près de zéro = sweet-spot d'entrée

Pente du canal (moyenne sur 5 bars avant entrée), exprimée signée par rapport à la direction du trade (positive = dans le sens du trade) :

**MNQ_v4** :

| Slope bucket (%/bar) | n | Avg PnL | WR | Avg R |
|----------------------|--:|--------:|---:|------:|
| < −0.05 % (fort contre) | 166 | +$54 | 55 % | 0.23 |
| −0.05 / −0.01 % | 723 | +$14 | 45 % | 0.11 |
| −0.01 / 0 % | 396 | +$34 | 44 % | 0.22 |
| **0 / +0.01 % (plat)** | **85** | **+$202** | 45 % | **+1.18** |
| > +0.01 % (fort dans le sens) | 19 | +$43 | 47 % | 0.28 |

**MNQ_MGC** (combiné) :

| Slope bucket | n | Avg PnL | Avg R |
|--------------|--:|--------:|------:|
| **0 / +0.01 %** | 170 | **+$126** | **+0.69** |
| Reste | ~2 100 | $20-50 | 0.1-0.2 |

* La zone **canal quasi-plat ou légèrement dans le sens du trade** sort un R 3-5× supérieur aux autres zones.
* Mécanisme probable : un canal très pentu (fort contre) signifie qu'on saute devant un train en marche ; un canal plat indique une transition possible — exactement le sweet-spot reversal.

**Caveat sample-size** : le bucket "0/+0.01 %" représente **n=85 sur MNQ_v4** et **n=170 sur MNQ_MGC** (le multi inclut les MNQ singles → n indépendant effectif ≈ 85-170, pas leur somme). La **direction** du signal (canal plat > canal pentu) est cohérente sur les 3 presets, mais la **magnitude** (R=1.18) reste très bruitée à ce volume. À traiter comme "signal directionnel à tester", pas comme "R=1.18 garanti".

**Proposition (signal directionnel, magnitude à valider)** :
1. Créer dans une **v4** un filtre `entry_slope_zone` avec deux paramètres : `slope_min_pct_per_bar`, `slope_max_pct_per_bar`. À fitter pour matcher ce sweet-spot.
2. Alternative plus simple : **filtre `canal_max_abs_slope`** qui rejette les entrées avec |slope| > 0.05 %/bar — coupe les setups "chase".

---

## Insight 7 — Entrer plus tard dans la fenêtre = R plus élevé

Position dans `entry_window_bars` (combiné MNQ_MGC, similaire en single) :

| bars depuis setup_bar | n | Avg PnL | WR | Avg R |
|----------------------:|--:|--------:|---:|------:|
| 0 (entrée immédiate) | 1 322 | +$33 | 53 % | 0.16 |
| 1 | 434 | +$30 | 48 % | 0.14 |
| **2** | **291** | **+$77** | 47 % | **+0.41** |
| **3** | **206** | **+$103** | 60 % | **+0.58** |
| 4-5 | 66 | +$22 | 52 % | 0.12 |

* L'entrée immédiate (`bar 0`) capture **57 % des trades** mais ne génère que **+$0.16/R**.
* Attendre 2-3 bars de confirmation après le slow-cross multiplie le R par 3-4×.
* Au-delà de 3 bars, le signal s'éteint.

**Proposition** : sweep `entry_window_min_bars: 2` (= n'entrer qu'à partir du 2ᵉ bar après le setup). Combiné à un `entry_window_bars=3-4`, on capturerait ~500 trades par preset au lieu de 1 400 mais avec un R moyen ~0.5 → profil PnL probablement supérieur et beaucoup moins de SL ≤ 1 bar (Insight 2).

---

## Insight 8 — Asymétrie Long/Short marquée sur MNQ : le Short rapporte 2× plus

| Preset | Side | n | Avg PnL | WR | Avg R | Avg MFE_R |
|--------|------|--:|--------:|---:|------:|----------:|
| MNQ_v4 | Long | 714 | +$23 | 47 % | 0.14 | 1.12 |
| MNQ_v4 | Short | 675 | **+$51** | 45 % | **0.31** | **1.43** |
| MNQ_MGC | Long (MNQ+MGC) | 1 168 | +$33 | 53 % | 0.16 | 1.01 |
| MNQ_MGC | Short (MNQ+MGC) | 1 151 | **+$55** | 50 % | **0.29** | 1.29 |
| MGC_v2 | Long | 570 | +$32 | 57 % | 0.16 | 0.92 |
| MGC_v2 | Short | 572 | +$46 | 54 % | 0.22 | 1.12 |

* Sur MNQ, le short a un R moyen **2× supérieur** au long.
* La MFE moyenne des shorts est nettement plus haute → les shorts capturent des mouvements plus amples.
* Sur MGC l'écart est plus modeste mais existe.

**Proposition** : pas urgent pour un nouveau filtre, mais permet une **idée de tuning** :
1. Tester un **risk asymétrique** : `risk_long = 0.7 × risk_short` sur MNQ. Au pire neutre, au mieux laisse plus de capital sur les shorts.
2. Auditer si l'asymétrie vient d'un filtre intrinsèque (`cloud_on=True` pour MNQ_v4 : la condition `cloud_long_ok` est plus sélective qu'on ne pense ?) ou d'une vraie skew structurelle des Q1-Q2 2025 → walk-forward pour vérifier la stabilité.

---

## Insight 9 — Auto-Close à 22:00 est un compartiment ultra-profitable à préserver

| Statut | n | PnL | Avg/trade | WR |
|--------|--:|----:|----------:|---:|
| Auto-Close (profit) | 253 | +$45 399 | +$179 | 97.6 % |
| Auto-Close (loss) | 169 | −$10 761 | −$64 | 0 % |
| **Net Auto-Close** | 422 | **+$34 638** | +$82 | 58.5 % |

* 253 trades sur 4 850 (5.2 %) produisent **17.5 %** du PnL net total.
* Ces trades sont en moyenne ouverts depuis 21 bars (~2h30 sur M7) avec un mouvement favorable persistent.
* Les Auto-Close perdants ont une perte 3× plus petite que les Auto-Close gagnants (effet stop-loss intra-bar non déclenché — momentum tellement faible que le SL initial est resté loin).

**Proposition** : **ne pas réduire l'auto-close** (déjà CLAUDE.md-pinné à 22:00 réf Bruxelles). Mais une idée intéressante :
1. **Pré-blackout à 21:30** : refuser de nouvelles entrées dans la dernière demi-heure (le potentiel d'arriver "in profit" à 22:00 est mince). Sweep défensif.
2. **"Trail-to-close" mode** : si le canal flippe après 18:00 et que le trade est in-profit, désactiver le Canal Exit pour forcer l'auto-close (capture les fins de session trending). Variant à tester.

---

## Pistes hors-bonus mineures (non comptées dans les 9)

* **HW value at entry** : entrer avec |HW| ≤ 5 sort un R = 0.46-0.51 contre 0.09-0.12 dans la zone 15-20. Le filtre actuel (`hw_extreme=20`) coupe les vrais extrêmes mais pas le quart moyen. Tester `hw_extreme=10` pour MNQ.
* **Canal width** : Q1 narrow et Q5 wide sortent les meilleurs PnL sur MNQ — pattern en U ; les canaux moyens sont les plus piégeux. À explorer plus finement.
* **Canal Exit losers** : avg MFE = 0.39R, MAE = 0.57R. **77 %** n'ont jamais dépassé +0.5R. Un "early kill if MFE < 0.3R after 5 bars" pourrait sauver une partie de ces $89 k — à tester dans une v4 (`min_mfe_check`).

---

## Synthèse des 4 hypothèses prioritaires pour une `HMASSLOsciV4`

Sans toucher v3, créer une nouvelle classe `HMASSLOsciV4(HMASSLOsciV3)` qui ajoute des paramètres optionnels (defaults = comportement v3) :

| # | Paramètre proposé | Hypothèse | Insights sources |
|--:|-------------------|-----------|------------------|
| 1 | `entry_window_min_bars: int = 0` | N'entrer qu'à partir du Nᵉ bar après slow-cross | 7 |
| 2 | `hw_age_min: int = 0` | Filtre : N bars min écoulés depuis le dernier HW | 4 |
| 3 | `canal_max_abs_slope: float = inf` | Filtre : reject si \|canal slope\| > X %/bar | 6 |
| 4 | `delayed_exit_if_canal_aligned: bool = False` | Différer le Canal Exit au HW suivant si le canal n'a pas encore flippé | 5, 1 |

* (1)+(2)+(3) sont des **filtres d'entrée** → diminuent le volume, augmentent la qualité.
* (4) est une **modification d'exit** ciblée — c'est l'exemple littéral de l'utilisateur, conditionné pour ne pas casser le PnL net.

Reproduction des analyses :

```bash
source venv/bin/activate
python scripts/goals/2026-05-17_HMASSLOsciV3_analysis/run_analysis.py
```

→ Régénère `outputs/trades_{MNQ_v4,MGC_v2,MNQ_MGC,ALL}.csv` et `outputs/summary.json`.

Le `trades_ALL.csv` (4 850 lignes × 38 colonnes) est l'**input prêt-à-l'emploi** pour toute analyse complémentaire (ex. notebook Jupyter, pandas, jointures sur autres indicateurs).

---

## Garde-fous pour la prochaine itération

* **Toutes les propositions sont à valider en walk-forward** sur la même période. La sample = 1 période de 17 mois, sans validation out-of-sample.
* Les chiffres sont **issus du replay déterministe** (PnL match au cent près avec les rapports v4, MGC_v2, MNQ_MGC publiés).
* Les insights 4, 5, 6, 7 sont **stables sur les 3 presets** (cross-asset) → robustes a priori. Les insights 8 (asymétrie) et 3 (SL tight) sont **asset-spécifiques** (forts sur MNQ, plus faibles sur MGC).
* La v3 reste intacte : `src/strategies/hma_ssl_osci_v3.py` n'a pas été modifié. Les CSVs et le script d'analyse vivent uniquement dans ce dossier.
