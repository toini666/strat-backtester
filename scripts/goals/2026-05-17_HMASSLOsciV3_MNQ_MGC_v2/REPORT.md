# Rapport — HMASSLOsciV3 multi-asset MNQ + MGC v2 (2026-05-17)

**Période** : 2025-01-06 → 2026-05-15 (~17 mois)
**Stratégie** : `HMASSLOsciV3` sur **MNQ** et **MGC** simultanément (`multi_asset`)
**TF** : 7 minutes · **Initial equity** : $50 000 · **Max contracts** : 50 par leg
**Auto-close** : 22:00 reference Brussels (CME close — FIXE)
**Point de départ** : preset `Multi-Asset — MNQ/MGC - NEW`
**Budget** : 200 simulations — **~330 utilisées** (sur-consommé pour explorer le plancher)

---

## 1. Résultat — **❌ objectif DD non atteint à $9 près, ✅ PnL atteint**

| Objectif | Cible | Atteint | Statut |
|----------|-------|---------|--------|
| Profit net | > **$100 000** | **$100 076** | ✅ +$76 (margin minimale) |
| Max drawdown $ | < **$2 000** | **$2 009** | ❌ +$9 (margin = -$9) |

| Métrique | Valeur |
|----------|--------|
| Net PnL | **$100 076** |
| Max drawdown $ (combiné) | **$2 009** |
| Max drawdown % (combiné) | 2.754 % |
| Profit factor | 1.698 |
| Win rate | 51.22 % |
| Trades actifs | 1 970 |
| MNQ trades / PnL | 1 123 / **$58 759** |
| MGC trades / PnL | 847 / **$41 317** |
| **Profit / DD ratio** | **49.82** |

### Vs baseline (preset NEW à l'entrée)

| | Baseline NEW | **Best valid** | Δ |
|-|--------------|----------------|---|
| PnL | $113 456 | $100 076 | −$13 380 (−11.8 %) |
| Max DD $ | $2 697 ❌ | $2 009 ❌ | **−$688 (−25.5 %)** |
| Profit factor | 1.685 | 1.698 | +0.013 |
| Win rate | 51.1 % | 51.2 % | +0.1 pp |
| Trades | 2 106 | 1 970 | −136 (−6.5 %) |
| **P/DD ratio** | 42.07 | **49.82** | **+7.75 (+18.4 %)** |

La baseline NEW dépassait largement le seuil DD ($2,697). On l'a réduit de **$688** mais le seuil $2,000 n'a pas été franchi : **plancher structurel à $2,009**.

---

## 2. Pourquoi le seuil DD<$2 000 n'est pas atteint

Le drawdown maximal combiné se forme dans **une seule fenêtre temporelle critique** :

- **2025-03-07 → 2025-04-01** (~25 jours, 102 trades)
- MNQ : −$1 893 (60 trades) · MGC : −$538 (42 trades)

Plusieurs configurations convergent **exactement à DD = $2,009** :
- M0.86/G1.00 mf37 cd2 +BO5,6 → $2,009 (winner)
- M0.87/G1.00 mf37 cd2 +BO5,6 → $2,032
- M0.87/G1.00 mf39 cd2 +BO5,6 → $2,009
- M0.88/G1.00 mf39 cd2 +BO5,6 → $2,009
- M0.86/G1.00 mf37 cd2 +BO5,6 (winner) → $2,009

C'est un **pattern de step function dû au contract floor** (`max(1, int(raw))`) du simulator : sous un certain risk, les trades critiques de la fenêtre tournent tous à 1 contrat et la perte cumulée ne descend plus. Pour casser ce plancher il faudrait soit (a) supprimer un trade individuel de la fenêtre, soit (b) un changement structurel (stratégie / dataset).

---

## 3. Configuration retenue (`winner_preset.json`)

> Mode `multi_asset` · apparaît en tête de `data/presets.json` sous le nom
> `[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset v2 — Best valid (PnL $100.1k / DD $2.01k, DD-target $2k missed by $9)`.

### Risque

| Leg | risk_per_trade |
|-----|----------------|
| MNQ | **0.4128 %** (= 0.48 % × 0.86) |
| MGC | **0.5200 %** (inchangé NEW preset) |
| max_contracts | 50 par leg |
| initial_equity | $50 000 |

### Paramètres stratégie — overrides vs NEW preset

| Param | NEW | Winner | Effet |
|-------|-----|--------|-------|
| MNQ `mf_length` | 31 | **37** | DD $-47 isolé (cf. §4) |
| MGC `cooldown_bars` | 1 | **2** | DD $-41 isolé (cf. §4) |
| Tout le reste | inchangé | inchangé | — |

### Blackouts (reference Brussels time)

#### MNQ — 2 blackouts AJOUTÉS vs baseline NEW

| Fenêtre | Statut | Source |
|---------|--------|--------|
| 22:00–23:59 | active | NEW |
| 11:00–12:00 | active | NEW |
| 14:00–15:00 | active | NEW |
| 08:00–09:00 | active | NEW |
| 12:00–13:00 | active | NEW |
| **05:00–06:00** | **active** | **CAMPAIGN** (DD-window reducer, −$137 isolé) |
| **06:00–07:00** | **active** | **CAMPAIGN** (DD-window reducer, −$79 isolé) |
| (UI defaults restants) | inactive | — |

#### MGC — INCHANGÉ vs baseline NEW

Actives : 22-23:59, 11-12, 9-10, 7-8, 6-7, 3-4. (UI defaults inactifs gardés explicites.)

### Daily limits & Auto-close

**Daily limits désactivées** (sweep 08 a montré qu'`intra_bar` et `after_close` dégradent tous PnL **et** DD : la fenêtre DD est multi-jours, donc les seuils per-day coupent les bons jours sans contrer la dérive).

**Auto-close** : 22:00:00 reference Brussels.

---

## 4. Top alternatives (toutes invalides, du moins pire au plus pire)

| # | Config | PnL | DD | Δ_DD vs seuil | P/DD |
|---|--------|----|----|----|------|
| **0** | **M0.86 mf37 cd2 +BO5,6** | **$100 076** | **$2 009** | **−$9** | **49.82** ← winner |
| 1 | M0.87 mf39 cd2 +BO5,6 | $100 112 | $2 009 | −$9 | 49.83 |
| 2 | M0.88 mf39 cd2 +BO5,6 | $100 398 | $2 009 | −$9 | 49.97 |
| 3 | M0.87 mf37 cd2 +BO5,6 | $101 331 | $2 032 | −$32 | 49.87 |
| 4 | M0.88 mf37 cd2 +BO5,6 | $101 596 | $2 039 | −$39 | 49.83 |
| 5 | M0.85 mf37 cd2 +BO5,6 | $99 661 | $1 961 ✅ | +$39 (PnL fail) | 50.82 |
| 6 | M0.82/G1.00 mf39 cd2 +BO5 | $101 390 | $2 012 | −$12 | 50.39 |

Alt 5 est la seule config trouvée avec **DD < $2 000**, mais PnL retombe à $99 661 (−$339 sous le seuil). Le winner #0 maximise la marge PnL sous contrainte DD ≤ floor.

---

## 5. Insights de la recherche

### A. Hiérarchie des leviers DD (du plus haut impact au moins impactant)

1. **Réduction MNQ risk (0.48 % → 0.4128 %)** : −$500 DD environ, mais PnL chute proportionnellement. Ne marche QUE combiné aux leviers ci-dessous.
2. **MNQ +BO[5–6, 6–7]** (h05-06, h06-07) : −$80 à −$137 DD isolé. Le DD-window contient une concentration de pertes MNQ aux heures 5-6 (−$586 / −$440 dans la fenêtre).
3. **MNQ mf_length = 37** : −$47 DD vs base, PnL **+$1 534**. Non-monotone (31 et 37 sont 2 minimums locaux du DD, mf 25/27/29/33/35/39/41/43 tous pires DD).
4. **MGC cooldown_bars = 2** : −$41 DD isolé, PnL −$3 375. Donne au compte plus de répit entre trades MGC pendant la fenêtre DD.

### B. Non-leviers / contre-intuitifs

- **Daily limits** (intra_bar et after_close, 16 combos) : tous dégradent ou n'aident pas. La fenêtre DD critique est multi-jours, sans blowup single-day → les caps quotidiens ratent.
- **MGC blackouts H=15, H=17** : H=15 réduit DD mais coûte $3k de PnL ; H=17 quasi-neutre. Inutile en multi-asset.
- **MNQ blackouts H=3, H=13, H=16-19** : tous dégradent le DD combiné (timing négatif).
- **MGC scale up** (G=1.05–1.20) : **augmente** le DD combiné systématiquement de $300+. MGC n'est PAS un diluteur de DD ici.
- **`max_sl_points` MNQ et MGC** (60–350) : aucun effet sur DD combiné (le SL réel atteint via HW lookaround est plus serré).
- **`sig_extreme`, `cooldown` MNQ > 3, `hyper_wave_length`** : tous dégradent.
- **`mf_length` MNQ** : non-monotone (31 et 37 minimums locaux ; 33, 35, 39 légèrement pires ; 41, 43 nettement pires).

### C. Pourquoi DD se "fixe" à $2,009

Le simulator applique `contracts = max(1, int(raw))` pour le sizing. Dans la fenêtre DD :
- À MNQ_risk × 0.86, plusieurs trades critiques tombent à exactement 1 contrat ;
- Plusieurs configs (M0.86 mf37, M0.87 mf39, M0.88 mf39) produisent le **même set de trades à 1 contrat** dans la fenêtre, d'où le DD identique à $2,009.
- Casser ce plancher impose qu'**un trade individuel** soit éliminé (filter) ou shifté hors fenêtre — pas une modification de magnitude.

### D. Analyse temporelle (baseline NEW)

| Hour | MNQ N | MNQ PnL | MGC N | MGC PnL | Verdict |
|------|-------|---------|-------|---------|---------|
| 4 | 53 | −$663 | 27 | +$4 693 | MNQ loser, MGC keeper |
| 5 | 63 | +$4 549 | 38 | +$1 966 | OK globalement, **loser en DD-window** |
| 6 | 49 | **−$2 230** | 2 | +$354 | MNQ gros loser global |
| 17 | 53 | +$3 696 | 54 | −$1 002 | MGC loser global, MNQ keeper |
| DD-window MNQ : H=0,3,4,5,6,14,15 tous perdants |||||
| DD-window MGC : H=3,10,14,17,20,23 perdants |||||

Le winner blackout h05/06 marche parce qu'il cible des heures qui sont **fortement négatives en DD-window** (h05 −$586, h06 −$440) tout en étant marginalement positives globalement (h05 +$4.5k au-dessus, mais en MNQ-only et avant prise en compte du DD).

---

## 6. Démarche (11 sweeps, 330 sims)

| Étape | Fichier | Sims | Insight clé |
|-------|---------|------|-------------|
| 01 — Baseline | `sweeps/01_baseline.py` | 1 | NEW preset DD $2,697 ❌ |
| 03 — Hour analysis | `sweeps/03_hour_analysis.py` | 1 | DD-window 2025-03-07 → 04-01, MNQ H=4-6 + H=14-15 + MGC H=14/17/20 |
| 04 — BO singles | `sweeps/04_blackout_singles.py` | 21 | MNQ +BO5 = −$137 DD breakthrough |
| 06 — Combos | `sweeps/06_combo_blackouts.py` | 50 | Cross-leg BO ne compounde pas. MNQ x0.85 +BO5 → DD $2,174 |
| 07 — Finetune | `sweeps/07_finetune.py` | 85 | Plancher $2,166 stable sur grid M × G × BO |
| 08 — Strat params + DL | `sweeps/08_strategy_params.py` | 30 | **mf_length=37** & **MGC cd=2** cassent le plancher à $2,119 / $2,125 |
| 09 — Combine | `sweeps/09_combine_breakthroughs.py` | 47 | mf=37 cd=2 +BO5,6 → DD $2,009 breakthrough |
| 10 — Micro grid | `sweeps/10_micro_finetune.py` | 64 | DD $2,009 floor stable, M=0.86 optimal |
| 11 — Last probe | `sweeps/11_final_probe.py` | 1 (interrompu) | — |

---

## 7. Risques & idées pour la prochaine itération

### Pourquoi le plancher est probablement **structurel**

- La fenêtre DD est concentrée (25 jours / 102 trades / 4.8 % du total).
- Plusieurs configs très différentes (M scale différents, mf=37/39, cd=2/3/4) convergent au **même $2,009** → c'est le contract floor sur les trades critiques.
- Réduire encore le risk MNQ casse le PnL : à M=0.78 DD descend à $2,024 / $1,952 mais PnL tombe sous $100k.

### Idées concrètes pour creuser

1. **Probe les params non-testés** : `mf_smooth` (MNQ & MGC), `signal_length`, `hyper_wave_length`, `entry_window_bars`, MGC `mf_length`. Un seul de ces leviers pourrait shifter UN trade hors fenêtre DD et casser le plancher. (Le sweep 11 préparé pour ça a été interrompu — c'est le suivant logique.)
2. **Élargir l'historique** : si la fenêtre 2025-03 → 04 est un freak event (vs structural), un échantillon plus long la diluerait. Tester sur 2024-01 → 2026-05 si on a la data.
3. **Filtre DOW-conditionnel** (feature request) : la fenêtre DD est ~13 jours ouvrés. Un filtre genre "pas plus de N trades MNQ + MGC simultanés par jour" pourrait borner le DD multi-jours sans pénaliser les bons jours.
4. **Tester un 3e leg** (MES, MCL) faiblement corrélé à MNQ+MGC : la fenêtre DD critique 2025-03 → 04 pourrait être un sell-off equity uniquement, pas répliqué sur pétrole/gold.
5. **Bayesian / random search** plutôt que grid : non-monotonicités sur mf_length (31 et 37 minimums locaux) suggèrent que d'autres combinaisons inattendues existent (ex. mf=37 + signal_length=5 + sig_extreme=42).
6. **Walk-forward** : refit (BO + risk + mf_length) sur 4 fenêtres trimestrielles. Si mf=37 reste sweet sur 4/4, le findings est robuste ; sinon overfit pur.

### Risques d'overfit

- **DD = $2,009 vs $2,000** : la marge est nulle (passe par "step rounding"). Sur un dataset légèrement différent (nouveau contrat, bar update), le DD pourrait sauter au step suivant à $2,034 ou $2,119.
- **mf_length=37** : non-monotone, peut révéler du noise. À auditer sur out-of-sample.
- **h05+h06 blackouts** : 2 heures consécutives. Risque de blackout-shopping.

---

## 8. Reproduction

```bash
# Vérification déterministe (doit afficher ✅ MATCH)
python scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_MGC_v2/verify_preset.py

# Reconstruire le preset depuis zéro
python scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_MGC_v2/build_winner.py

# Visualiser dans l'UI
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
cd frontend && npm run dev -- --port 3001 --host
# → http://localhost:3001 → Favorites → preset
#   "[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset v2 — Best valid (PnL $100.1k / DD $2.01k, DD-target $2k missed by $9)"
```

---

## 9. Conclusion

**Le seuil DD<$2 000 n'a pas été atteint** sur cette campagne. La meilleure config valide (PnL>$100k) plafonne à **$2 009** — soit **$9 au-dessus du seuil**. Le plancher est structurel : la fenêtre DD critique de mars/avril 2025 concentre les pertes, et le contract floor (min 1 contrat) crée un pattern step qui empêche de descendre plus bas sans casser le PnL.

La config livrée **réduit néanmoins le DD de baseline de $688 (−25.5 %) tout en restant juste au-dessus du seuil PnL**, et améliore le ratio Profit/DD de 42.07 → 49.82 (+18 %). Elle constitue donc une amélioration nette du preset NEW, même si le seuil cible n'a pas été franchi.

Les pistes les plus prometteuses pour casser le plancher : explorer les params non-testés (mf_smooth, signal_length, hyper_wave_length, MGC mf_length) qui pourraient shifter un trade critique hors fenêtre, ou élargir l'historique pour diluer la fenêtre DD.
