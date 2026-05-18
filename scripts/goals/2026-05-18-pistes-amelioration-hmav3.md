# Pistes d'amélioration HMASSLOsciV3 — synthèse des campagnes

**Date** : 2026-05-18
**Objet** : Bilan de ~10 campagnes d'optimisation menées entre le 15 et le 17 mai 2026 sur la stratégie HMASSLOsciV3 (MNQ + MGC), et identification des leviers d'amélioration restants.

---

## Avant de lire — lexique rapide

Pour rendre le rapport lisible, voici les termes qui reviennent partout :

| Terme | Ce que c'est, en clair |
|-------|------------------------|
| **PnL** | Profit & Loss — le gain net en dollars sur la période de backtest |
| **DD** (drawdown) | La plus grosse baisse d'equity vécue. Plafond de risque qu'on s'impose. |
| **P/DD** (ratio profit/drawdown) | Combien de dollars on gagne pour chaque dollar de perte max acceptée. Plus haut = meilleur edge. |
| **WR** (win rate) | % de trades gagnants |
| **R** | Multiple de risque. 1R = la perte si SL est touché. 2R = on a gagné deux fois le risque pris. |
| **MAE** | Maximum Adverse Excursion — la pire perte flottante vécue avant la sortie. Indique "à quel point on a saigné" pendant le trade. |
| **MFE** | Maximum Favorable Excursion — le plus gros profit flottant qu'on a vu. Indique "ce que le trade a valu à son meilleur moment". |
| **Canal Exit** | Sortie déclenchée par le moteur HMA (canal qui se retourne / HMA rapide qui croise / Hyperwave qui croise). C'est la sortie "normale" d'un trade gagnant. |
| **Auto-Close** | Fermeture forcée à 22:00 (clôture CME). Quelques trades par mois survivent jusque-là. |
| **HW** (Hyperwave) | Un des oscillateurs de la stratégie. Quand il croise, ça déclenche les sorties. |
| **Cluster de SL** | Plusieurs Stop Loss consécutifs (typiquement en marché latéral) |
| **Walk-forward** | Méthode de validation : on "fit" sur la première moitié de la période, on teste sur la seconde. Si ça tient out-of-sample, la stratégie est moins overfittée. |

---

## 1. État des lieux — où on en est aujourd'hui

Après une dizaine de campagnes, les deux **meilleures configurations actuelles** sont :

### MNQ — V5 (winner du 17 mai)
- **PnL** : +$68 765 sur 17 mois (Q1 2025 → Q2 2026)
- **DD max** : $1 579 (sous le plafond de $2 000)
- **Ratio P/DD** : **43.55** — c'est excellent
- 1 241 trades, WR 48.3 %

### MGC — V3 (winner du 17 mai)
- **PnL** : +$44 692 sur la même période
- **DD max** : $1 944 (très près du plafond de $2 000 — margin de seulement $56)
- **Ratio P/DD** : **22.99**
- 865 trades, WR 55.1 %

### Décomposition du PnL sur 4 850 trades cumulés (3 presets analysés)

| D'où ça vient | Trades | PnL | WR | Ce que ça veut dire |
|---------------|-------:|----:|---:|---------------------|
| **Canal Exit** (sortie HMA normale) | 2 994 | **+$435 754** | 74.5 % | C'est la machine à profit. Quasi tout le PnL net vient de là. |
| **Auto-Close (gagnant)** | 253 | +$45 399 | 97.6 % | Quand un trade survit jusqu'à 22:00, il est presque toujours gagnant. 5 % des trades = 17.5 % du PnL. À préserver absolument. |
| **Auto-Close (perdant)** | 169 | −$10 761 | 0 % | Petite perte. Tenir jusqu'à la cloche reste +EV. |
| **Stop Loss** | 1 432 | **−$272 989** | 0 % | **C'est la seule source structurelle de perte.** ~100 % du DD vient des SL. |

**Implication directe** : pour améliorer la stratégie, on a deux leviers possibles :
1. **Réduire ou mieux gérer les Stop Loss** (côté pertes)
2. **Mieux timer les Canal Exit ou préserver les Auto-Close** (côté gains)

Modifier les TP partiels (le fait de sortir 25 % de la position à un certain moment) n'est PAS la veine principale — les 3 winners ont tous `hw_partial_pct=0`, c'est-à-dire qu'ils ne font aucun TP partiel.

---

## 2. Ce qui a été testé et qui NE MARCHE PAS

Inutile de retester ces idées : elles ont été éprouvées sur des sweeps A/B rigoureux avec verdict clair. Voici la liste, avec en français simple ce que ça veut dire et pourquoi.

### Sur les conditions d'entrée

| Idée testée | Verdict | Pourquoi ça ne marche pas |
|-------------|---------|---------------------------|
| Attendre 1, 2 ou 3 bougies après le signal d'entrée pour confirmer | ❌ REJET | La toute première bougie capte des opportunités uniques qu'on ne retrouve pas en attendant. Tester ça enlève entre $18 000 et $37 000 de PnL. |
| Refuser les trades avec un Stop Loss trop serré | ❌ REJET | Contre-intuitif : les SL serrés permettent de prendre **plus de contrats** (le sizing s'adapte au risque). Couper ces trades enlève $13 000+ de PnL. |
| Filtrer les bougies trop "agressives" (gros corps) à l'entrée | ❌ REJET | Encore plus contre-intuitif : les bougies agressives sont **les meilleurs setups**. Le top quintile de l'agressivité a un WR de 57-65 %. Les filtrer dégrade tout. |
| Filtrer le cumul de corps sur 2 bougies | ❌ REJET | Même histoire, aucune valeur n'améliore. |

### Sur les sorties (exits)

| Idée testée | Verdict | Pourquoi ça ne marche pas |
|-------------|---------|---------------------------|
| Sortir immédiatement au croisement HMA rapide, sans attendre le Hyperwave | ❌ REJET | La séquence "HMA rapide → attente HW" rapporte $23 000 en plus sur 1 340 trades. Couper l'attente détruit cet edge. |
| Sortir au moment où le canal HMA se retourne contre nous | ❌ REJET | Ça plafonne les gros gagnants. On perd $27 000 cumulés en faisant ça. |
| Sortir une fois que le profit a atteint un certain seuil puis est redescendu (MFE-floor) | ❌ REJET | Ça récupère bien quelques "give-back" (trades qui auraient pu être pris en cours de route) mais ça coupe encore plus de gros gagnants. Net négatif sur toutes les variantes testées. |
| Prendre un partial profit au seuil MFE (au lieu de fermer 100 %) | ❌ REJET | Même problème : on tue le tail des très gros gagnants. |
| Prendre un partial au flip canal | ❌ REJET | Idem, on plafonne le tail. |
| Daily limits (stop trading après +X $ ou −Y $ dans la journée) | ❌ REJET | Coupe les jours de rebond. Toujours dégradant sur les 2 setups. |
| Augmenter le `tick_buffer` (acheter/vendre un peu plus loin du prix) | ❌ REJET | Ajoute du slippage sans bénéfice. |
| `cooldown_bars` > 3 (espacer les trades davantage) | ❌ REJET | Fait manquer des trades groupés profitables. |

### Conclusion sur ces rejets

**La stratégie est en équilibre statistique fragile.** Beaucoup d'heures, de patterns ou de signatures "qui ressemblent à des perdants" sont en réalité **compensés** par des trades adjacents. Par exemple, sur MNQ, l'heure 6h du matin a 53.8 % de SL — ça semble toxique — mais quand on la bloque, **le DD explose de +63 %** parce que les heures voisines amplifient les drawdowns au lieu de compenser.

**Moralité** : on ne peut pas améliorer la stratégie en "filtrant les mauvais trades" naïvement. Il faut soit (1) des filtres très spécifiques basés sur des signatures fines, soit (2) modifier l'architecture du moteur de simulation pour ouvrir des comportements actuellement impossibles.

---

## 3. Ce qu'on a appris — les vérités cross-asset

Ces observations sont **stables sur les 3 presets analysés** (MNQ_v4, MGC_v2, MNQ_MGC multi-asset). Elles forment la base solide pour comprendre la stratégie.

### 3.1 — La première bougie est un piège

| Bougies dans le trade | n | PnL net | WR |
|----------------------:|--:|--------:|---:|
| **≤ 1 bougie** | **187** | **−$25 944** | **6.4 %** |
| 2-3 bougies | 1 004 | −$56 359 | 35.2 % |
| 4-6 bougies | 1 229 | +$50 150 | 60.6 % |
| 7-12 bougies | 1 144 | +$78 093 | 51.7 % |
| > 24 bougies | 592 | **+$111 317** | **68.4 %** |

**Lecture en clair** : 187 trades meurent dès la première bougie après l'entrée (= 128 SL sur 187, soit 68 %). Ces trades sont **les plus toxiques de la stratégie** (WR 6.4 %, perte cumulée $26 k). À l'inverse, les trades qui survivent au-delà de 24 bougies ont un WR de 68 % et rapportent énormément.

**Ce que ça implique** : si on pouvait détecter et éviter (ou couper très tôt) ces 187 trades, on récupérerait potentiellement $20-30 k de PnL sans toucher au reste.

**Pourquoi ça n'a pas encore été corrigé** : c'est l'hypothèse "H-B2" qui n'a pas pu être testée car le moteur de simulation actuel ne permet pas un "early kill" propre sans casser le reste de la logique de sortie (voir section 4.1).

### 3.2 — Le canal qui se retourne pendant le trade est le signal clé

| Le canal HMA flippe-t-il pendant le trade ? | n | PnL moyen | WR |
|---------------------------------------------|--:|---------:|---:|
| **Non** (reste contre nous) | 1 958 | **−$40** | 35.5 % |
| **Oui** (flippe dans notre sens) | 2 892 | **+$93** | 63.2 % |

**Lecture en clair** : ~95 % du PnL net vient des trades où le canal change de couleur pendant qu'on est dedans. La stratégie est donc **fondamentalement "reversal"** : on entre alors que le canal est encore défavorable, et on profite de son retournement.

**Ce que ça implique** : si on pouvait détecter à l'entrée quels trades vont voir leur canal flipper rapidement vs ceux qui resteront "en contre", on aurait un filtre ultra-puissant. Aujourd'hui on ne sait pas le faire en avance, mais c'est une direction de recherche claire.

### 3.3 — La vitesse du prochain Hyperwave prédit la profitabilité

| Bougies avant le prochain HW après l'entrée | n | PnL moyen | WR |
|--------------------------------------------:|--:|---------:|---:|
| 1 | 771 | −$10 | 32 % |
| 2 | 1 279 | −$16 | 38 % |
| 3 | 1 240 | +$30 | 53 % |
| **4-5** | **1 224** | **+$98** | **67 %** |
| **6-8** | **310** | **+$254** | **84 %** |

**Lecture en clair** : si le Hyperwave (HW) croise très vite après l'entrée (1-2 bougies), c'est un signal de **renversement de momentum contre nous** = perte quasi-certaine. Si le HW met 6-8 bougies à arriver, c'est la preuve d'un **momentum soutenu** = grosse moyenne de gain.

**Ce que ça implique** : ajouter un filtre `hw_age_min` (= refuser l'entrée si un HW a crossé dans les 3-5 bougies précédentes) couperait probablement une fraction notable des trades pourris. Le filtre actuel `hw_dir_on=True` n'exige que la direction du dernier HW, sans contrainte d'âge.

### 3.4 — La pente du canal au moment de l'entrée a un sweet spot

Quand le canal HMA est **quasi plat ou très légèrement dans le sens du trade** au moment de l'entrée, le R moyen est **3 à 5 fois supérieur** aux autres zones de pente.

**Lecture en clair** : un canal très pentu **contre** notre trade = "on saute devant un train en marche", c'est risqué. Un canal très pentu **dans** notre sens = on arrive trop tard, le mouvement est presque fini. Le sweet spot est le canal "en transition" — c'est exactement le profil reversal de la stratégie.

⚠️ **Caveat** : ce sweet spot est observé sur seulement n=85-170 trades. La **direction** du signal est claire et stable cross-preset, mais la **magnitude** précise reste bruyante. À traiter comme une piste solide à tester en filtre, pas comme une vérité gravée.

### 3.5 — Asymétrie Long/Short marquée sur MNQ

| MNQ_v4 | Trades | PnL moyen | WR | R moyen |
|--------|-------:|---------:|---:|--------:|
| Long | 714 | +$23 | 47 % | 0.14 |
| **Short** | 675 | **+$51** | 45 % | **0.31** |

**Lecture en clair** : sur MNQ, les shorts rapportent en moyenne **2× plus** que les longs. Sur MGC c'est plus modeste mais existe aussi.

**Ce que ça implique** : on pourrait tester un **risque asymétrique** (par exemple risk_long = 0.7 × risk_short sur MNQ). Au pire on est neutre, au mieux on alloue plus de capital aux shorts plus rentables. Il faudrait aussi auditer si c'est dû à un filtre intrinsèque (le filtre `cloud_on=True` plus sélectif sur les longs ?) ou à un vrai biais structurel des 17 mois étudiés.

### 3.6 — Performance par jour de la semaine

| Jour | MNQ V4 baseline |
|------|----------------:|
| Lundi | +$2 000 |
| Mardi | +$12 400 |
| Mercredi | +$3 000 |
| Jeudi | +$17 200 |
| Vendredi | +$16 200 |

**Lecture en clair** : Mardi/Jeudi/Vendredi génèrent 4-6× plus de PnL que Lundi/Mercredi sur MNQ.

**Pourquoi ça n'a pas été exploité** : le moteur actuel ne supporte que des blackouts "heure de la journée", pas "jour de la semaine". Il faudrait l'étendre — c'est un dev d'~½ journée qui ouvrirait ce levier.

### 3.7 — Les bougies "tardives" dans la fenêtre d'entrée sont plus rentables

| Position dans la fenêtre d'entrée | n | PnL moyen | R moyen |
|----------------------------------:|--:|---------:|--------:|
| Bar 0 (entrée immédiate) | 1 322 | +$33 | 0.16 |
| Bar 1 | 434 | +$30 | 0.14 |
| **Bar 2** | **291** | **+$77** | **+0.41** |
| **Bar 3** | **206** | **+$103** | **+0.58** |

**Mais attention** : 57 % des trades se font en bar 0. Si on les filtre tous, on perd énormément de volume (et tester "attendre 2-3 bougies" a été REJETÉ — voir section 2). Le sweet spot est ailleurs : peut-être un **mix** où on prend bar 0 seulement si une condition supplémentaire est remplie.

---

## 4. Les vraies pistes à creuser — par priorité

Voici les 5 chantiers où il y a une vraie chance de débloquer de la performance, classés par ratio bénéfice / coût.

### 🥇 Priorité 1 — Permettre les "early kill" dans le moteur (impact estimé : +$10-15 k de PnL préservé)

**Ce qu'on veut faire** : ajouter dans le moteur de simulation un mécanisme qui ferme une position si elle saigne trop vite (par exemple : MAE > 0.7R au bout de 2 ou 3 bougies, sans attendre le SL classique).

**Pourquoi c'est important** : c'est l'hypothèse la plus prometteuse identifiée (la "H-B2"). On a vu en section 3.1 que les trades qui meurent en ≤3 bougies coûtent collectivement $32 k. Récupérer même 30-50 % de ces pertes ferait $10-15 k de PnL net préservé, et le DD baisserait en parallèle.

**Pourquoi ça n'a pas encore été fait** : le mode de sortie actuel du moteur (`v3_fast_hma_ssl`) ferme la position sur le **prochain croisement HW dans n'importe quelle direction** une fois qu'il est "armé". Donc si on injecte notre signal "kill", on arme la sortie, qui se déclenche ensuite sur le mini-rebond suivant — ce qui tue les trades patients (= les bons winners).

**Ce qu'il faudrait coder** : ~30 lignes dans `src/engine/simulator.py` pour ajouter une option `early_kill_if_mae_r_above_at_bar_n` qui ferme la position **sans** armer la séquence de sortie existante.

**Effort estimé** : ~1 jour de dev + 1 campagne de validation.

---

### 🥈 Priorité 2 — Permettre "HW only if profit" dans le moteur (impact à mesurer)

**Ce qu'on veut faire** : conserver la logique V3 (attendre le Hyperwave pour fermer), mais à l'arrivée du HW, ne fermer que si on est en profit. Sinon, laisser courir jusqu'au HW suivant.

**Pourquoi c'est intéressant** : on a découvert qu'environ 26.5 % des trades voient leur HW coûter de l'argent (le trade aurait fini mieux sans attendre le HW). Mais à l'inverse, désactiver totalement la fermeture in-loss-HW fait perdre $30 k cross-asset — donc ce path "ferme en perte au HW" transporte un edge important qu'il faut comprendre.

**L'idée fine** : ne pas dire "ne jamais fermer en perte" mais "ne fermer en perte que si une signature supplémentaire confirme". Ça demande d'abord de pouvoir tester la version simple proprement.

**Pourquoi ça n'a pas été testé** : même problème de moteur que ci-dessus. Il faudrait ajouter un flag `v3_in_loss_close_gate: bool` dans la config simulateur, et conditionner la fermeture sur `close_price > entry_price`.

**Effort estimé** : ~½ jour de dev + 1 campagne de validation.

---

### 🥉 Priorité 3 — Re-tester le "partial 10-25 % au fast cross" sur MNQ (impact validé en walk-forward)

**Ce qu'on veut faire** : prendre 10 à 25 % de la position au moment du croisement HMA rapide (avant l'attente du HW). C'est l'hypothèse H5 de la campagne exit_v1.

**Pourquoi c'est intéressant** : **c'est le seul signal positif identifié en walk-forward** sur toutes les campagnes. Sur la deuxième moitié de la période (Oct 2025 → Mai 2026, données "out-of-sample") :
- ΔPnL = **+$1 319** (positif)
- ΔDD = **−$154** (DD réduit aussi, ce qui est rare)

Sur la période complète, l'effet est mixte parce qu'un événement DD spécifique sur la première moitié pollue le résultat global. Mais sur la moitié récente, c'est clairement bénéfique.

**Pourquoi ça a été classé "REJECT" la dernière fois** : le critère de validation exigeait que ça marche cross-asset (MNQ ET MGC). Sur MGC ça ne marche pas. Mais ça ne veut pas dire que c'est mauvais sur MNQ.

**Ce qu'il faut faire** : campagne dédiée **MNQ uniquement**, avec une validation k-fold (k≥3, pas juste un split 50/50) et idéalement une période étendue de quelques mois. Bonus : tester en combinaison avec une restriction "short only" (puisqu'on a vu en section 3.5 que les shorts ont 2× plus d'edge sur MNQ).

**Effort estimé** : ~1 jour (pas de modif moteur nécessaire, c'est dans la stratégie Lab).

---

### 4ᵉ — Ajouter le filtre par jour de la semaine au moteur

**Ce qu'on veut faire** : permettre de bloquer le trading sur certains jours de la semaine.

**Pourquoi c'est intéressant** : on a vu en section 3.6 que Lundi et Mercredi sont 4-6× moins rentables que Mardi/Jeudi/Vendredi sur MNQ. Bloquer ces 2 jours pourrait shaver $5 k de PnL marginal mais surtout réduire le DD de $200-400, ce qui élargit la marge sous la cible de $2 000.

**Pourquoi ça n'a pas été fait** : le système actuel `BlackoutWindowSettings` ne gère que des fenêtres "heure de la journée", pas "jour de la semaine".

**Ce qu'il faudrait coder** : ajouter un champ `days_of_week: list[int]` au type Blackout, +20 lignes dans `simulator._is_blackout_active`. C'est mécanique.

**Effort estimé** : ~½ jour de dev + 1 sweep de validation.

---

### 5ᵉ — Campagne dédiée "filtres d'entrée raffinés"

**Ce qu'on veut faire** : implémenter 2-3 filtres d'entrée motivés par les observations cross-asset stables :

1. **`hw_age_min`** : refuser l'entrée si un HW a crossé dans les 3-5 bougies précédentes (cf. section 3.3 — un HW trop récent = renversement de momentum imminent).

2. **`canal_slope_zone`** : ne prendre les entrées que si la pente du canal est dans une zone proche de zéro (cf. section 3.4 — sweet spot de pente plate).

3. **Gate régime par couleur du canal à l'entrée** : moduler le comportement selon que le canal est "vert" ou "rouge" au moment de l'entrée. Sur MNQ, les entrées contre un canal rouge (`FAST_IN_RED`) génèrent $76.9 k vs $48.7 k pour les entrées en canal vert. La logique d'exit pourrait être différente selon le régime.

**Pourquoi ça mérite une campagne** : ces 3 filtres adressent directement les 3 signaux cross-asset les plus solides. Aucun n'a encore été testé proprement. Risque : couper trop de volume — il faudra sweeper en multi-valeurs et regarder le bénéfice net.

**Effort estimé** : ~2 jours (codage stratégie Lab + sweeps + validation walk-forward).

---

## 5. Sujets "à surveiller" — moins prioritaires mais intéressants

### A. Diagnostiquer les clusters de Stop Loss en latéralisation

Une campagne dédiée (`2026-05-17-strategy-evolution-hmav3-3-sl-cluster.md`) a été spécifiée mais pas encore exécutée. Elle vise à :
1. **Caractériser** : qu'est-ce qu'un "cluster de SL" statistiquement ? Est-ce plus fréquent que ce qu'on attendrait du WR observé ?
2. **Corréler** : à quels régimes de marché (largeur de canal HMA, MFI plat, oscillateur dans une bande, ATR bas) ?
3. **Traiter** : sizing dynamique (réduire la mise après 2 SL d'affilée), blackout dynamique (skip jusqu'à fin de session après K SL), filtre régime préventif.

La plupart des contre-mesures (familles X = exit défensif, L = replacement de SL) reposent sur le hook "kill-on-MAE" de la priorité 1 — donc il vaut mieux faire P1 d'abord, puis attaquer cette campagne.

### B. Auditer le code potentiellement "dead"

- **`final_exit_pct`** : 4 valeurs testées sur MGC, aucun effet observable. Probable code mort dans le mode `final_exit_mode="HMA rapide/SSL → HW"`. À tracer et soit brancher proprement, soit supprimer.
- **`ssl_mult`** : 5 valeurs donnent le même résultat sur MGC. À comprendre.

### C. Sweep multi-dimensionnel des paramètres non-monotones

Deux découvertes critiques des campagnes V5 et V3 :

1. **`mf_length` est non-monotone** : la fonction performance(mf_length) a des **vallées et des sweet spots**, pas une courbe en cloche. Sur MNQ, vallée à 25 (le défaut V4 !) et sweet spots à 20 et 31. Sur MGC, sweet spot à 29. **Risque** : il existe peut-être d'autres sweet spots cachés dans des zones non testées (12-19 ou 33-45).

2. **`risk_per_trade` est aussi non-monotone** à cause du floor entier sur les contrats (`max(1, int(...))`). Sur MNQ : risk=0.0058 donne DD $3 420, risk=0.0060 donne DD $1 961 (la transition d'un contrat à l'autre crée des discontinuités). Il existe potentiellement des "vallées d'arrondi" exploitables.

**Implication pratique** : un sweep 2-D fin sur `mf_length × mf_smooth` ou une optimisation bayésienne sur 4-5 variables pourrait débloquer un autre niveau de performance. **Mais attention** : ces sweet spots non-monotones sont fragiles à un changement marginal de régime. Toute amélioration découverte par ce biais doit être validée en walk-forward strict avant production.

### D. Tester le transfert cross-asset

Les recettes MNQ V5 (mf=31, ms=7, BO 8+12, r=0.48%) et MGC V3 (cloud_on=T, mf=29, ms=5, r=0.52%) **ne transfèrent pas directement** d'un asset à l'autre. Mais la **méthode** (activer cloud, sweeper mf en pas fin, push le risk avec le floor en tête) si.

Une campagne courte sur MES, M2K, MYM dirait si l'edge est structurel ou un fit asset-spécifique. Si l'edge transfère sur 2-3 autres assets, c'est un vrai pattern. Sinon, on est sur de l'overfit à maîtriser.

### E. Pré-blackout à 21:30 et "trail-to-close" mode

Idées de protection des Auto-Close gagnants (qui rapportent 17.5 % du PnL net) :

1. **Pré-blackout à 21:30** : refuser de nouvelles entrées dans la dernière demi-heure (les chances qu'un trade ouvert tard arrive in-profit à 22:00 sont minces). Sweep défensif simple.

2. **Trail-to-close** : si le canal flippe contre nous **après 18:00** mais qu'on est in-profit, **désactiver le Canal Exit** pour forcer l'auto-close. Cette logique a déjà été validée partiellement sur MGC (H-C1, `disable_canal_exit_from_hour=21`).

---

## 6. Garde-fous et pièges à éviter

Sur la base des erreurs vues dans les campagnes passées :

1. **Toujours valider en walk-forward avant production**. Le DD MGC tient à $56 sous le plafond — un changement marginal de régime peut faire basculer. Si tu trouves un sweet spot, sweep autour pour mesurer sa **largeur**, pas juste sa hauteur. Un sweet spot "étroit" est un piège.

2. **Méfie-toi des effets "DD-amplifier inverse"**. Une heure qui a 53 % de SL ressemble à un poison, mais bloquer cette heure peut **augmenter** le DD si les heures adjacentes amplifient les drawdowns sans cette compensation. Toujours tester l'ajout de blackouts avec le DD comme métrique principale.

3. **Le critère cross-asset strict (MNQ ET MGC ensemble) est trop sévère sur n=2 baselines**. Une hypothèse "MIXED" (positive sur un asset, négative sur l'autre) mérite d'être validée sur d'autres assets avant rejet définitif. C'est la cas de H5 (partial au fast cross) qui aurait été KEEP MNQ-only.

4. **Sample-size caveat**. Plusieurs insights cités (slope 0/+0.01 % n=85, bars 3-4 entry n=200-300, certaines heures n=9-18) ont des petits n. La **direction** est stable cross-preset, la **magnitude** précise non. Ne pas anchorer sur "R=1.18" mais sur "c'est mieux que le reste".

5. **Ne JAMAIS toucher l'auto-close à 22:00**. C'est pinned dans le CLAUDE.md du projet. C'est la clôture CME et c'est intouchable.

6. **Sortir du local optimum MNQ V5 demande probablement une refonte**, pas un tweak paramétrique. La V5 est ultra-dense : aucune des 6 hypothèses de la campagne d'évolution n'a amélioré son P/DD. Pour la dépasser, il faudra probablement le hook "kill-on-MAE" + des exits conditionnels au régime.

---

## 7. Synthèse en une page — par où commencer

Si tu as 1 semaine devant toi, voici l'ordre recommandé :

### Jour 1-2 — Extension moteur (déverrouille le reste)
- Ajouter `early_kill_if_mae_r_above_at_bar_n` au simulateur (priorité 1)
- Ajouter `v3_in_loss_close_gate` au simulateur (priorité 2)
- Ajouter `days_of_week` au type Blackout (priorité 4)

### Jour 3-4 — Campagnes "moteur étendu"
- Tester H-B2 (early kill) — récupérer les SL ≤3 bougies
- Tester DOW blackout sur MNQ (Lundi/Mercredi)
- Tester H2 (HW only if profit)

### Jour 5 — Campagne H5 MNQ-only (déjà actionnable)
- Re-tester partial 10-25 % au fast cross sur MNQ avec validation k-fold

### Jour 6-7 — Filtres d'entrée raffinés
- Implémenter `hw_age_min`, `canal_slope_zone`, gate régime canal_green
- Sweeps + walk-forward

### Au-delà
- Campagne SL-cluster (utilise le hook kill-on-MAE)
- Audit code mort (`final_exit_pct`, `ssl_mult`)
- Transfert cross-asset MES/M2K/MYM
- Sweep multi-D Bayésien sur les params non-monotones

---

## 8. Ce qu'il faut retenir — TL;DR en 7 points

1. **Le PnL vient à 100 % des Canal Exit**, le DD à 100 % des Stop Loss. Toute amélioration doit jouer là.

2. **Les Stop Loss "rapides" (≤3 bougies) sont le plus gros gisement** : 39 % des SL MNQ tombent là, pour −$31 k. Mais ce levier nécessite une extension du moteur de simulation.

3. **Les filtres d'entrée "naïfs" ne marchent pas** — la stratégie est en équilibre statistique, supprimer un sous-ensemble libère d'autres séquences DD plus longues.

4. **Le seul signal walk-forward positif identifié = partial 10-25 % au fast cross sur MNQ**. À re-tester en campagne dédiée MNQ-only avec k-fold étendu.

5. **Le winner MGC est fragile** (margin $56 sous le cap DD $2 000) — ses sweet spots non-monotones doivent être validés en walk-forward avant de pousser le risk.

6. **L'asymétrie Long/Short sur MNQ (shorts = 2× R des longs) n'est pas exploitée** — risk asymétrique mérite un sweep.

7. **Les territoires vierges les plus prometteurs** : (a) régime-conditional exits selon couleur du canal à l'entrée, (b) filtre `hw_age_min`, (c) filtre `canal_slope_zone`, (d) DOW filter Mon/Wed sur MNQ.

---

*Sources : campagnes `2026-05-17_HMASSLOsciV3_evolution`, `2026-05-17_HMASSLOsciV3_exit_v1`, `2026-05-17_HMASSLOsciV3_analysis`, `2026-05-17_HMASSLOsciV3_MNQ_v5`, `2026-05-17_HMASSLOsciV3_MGC_v3`, et autres dans `scripts/goals/`.*
