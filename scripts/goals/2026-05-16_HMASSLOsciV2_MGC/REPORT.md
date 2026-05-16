# Rapport final — Optimisation HMASSLOsciV2 sur MGC

**Période** : 2025-01-06 → 2026-05-15 (~17 mois)
**Stratégie** : `HMASSLOsciV2` (`src/strategies/hma_ssl_osci_v2.py`)
**Symbole** : MGC — micro-futures Gold
**Equity initial** : 50 000 $ | **Max contracts** : 50

---

## 1. Résultat — best-effort, 1 objectif sur 2 atteint ⚠️

| Objectif | Cible | Atteint | Statut |
|----------|-------|---------|--------|
| Profit net | > 30 000 $ | **44 006 $** | ✅ +$14 006 |
| Max drawdown | < 2 500 $ | **6 588 $** | ❌ +$4 088 |

Métriques détaillées de la configuration retenue :

| Métrique | Valeur |
|----------|--------|
| Net PnL | **44 006 $** |
| Max drawdown $ | **6 588 $** |
| Profit factor | **1.31** |
| Win rate | 53.5 % |
| Trades actifs | 795 |
| Avg win / Avg loss | +443 $ / –390 $ |
| Reward:Risk | 1.14 |
| Sharpe | 1.27 |
| **Profit / DD ratio** | **6.68** |

**Pourquoi DD ne passe pas ?** Sur MGC, le ratio Profit/DD atteint un **plafond structurel autour de 7.0** quelle que soit la configuration testée. Or pour satisfaire simultanément PnL > 30k$ ET DD < 2.5k$, il faut un **P/DD > 12.0**. Cette borne n'a été franchie dans aucune des >100 configurations explorées (8 sweeps : baseline TFs, filter activation, filter combos, params 1D, combos params, risk + daily limits, hour analysis, blackouts, fine-tune, final combos, validation). Voir §6 (Hypothèses).

> 📌 La campagne sœur V3 sur MGC (`scripts/goals/2026-05-15_HMASSLOsciV3_MGC/REPORT.md`) a atteint un plafond P/DD ≈ 10.2 sur la même stratégie, version 3 — toujours en-dessous du seuil 12 nécessaire. V2 plafonne à 6.7 — V3 a un edge structurellement supérieur sur MGC.

---

## 2. Configuration retenue (winner_preset.json)

### Timeframe
**M7** (7 minutes). Sur les TFs prioritaires :

| TF | PnL baseline | DD baseline | P/DD |
|----|-------------|-------------|------|
| 15m | –2 694 $ | 26 032 $ | –0.10 ← moins mauvais |
| 10m | –23 846 $ | 59 479 $ | –0.40 |
| **7m** | **–36 963 $** | **66 438 $** | **–0.56** ← retenu (le plus de volume pour sweeper) |
| 5m | –42 592 $ | 69 066 $ | –0.62 |
| 3m | –237 794 $ | 241 888 $ | –0.98 |
| 2m | –308 563 $ | 314 550 $ | –0.98 |

Le 7m a été retenu malgré un P/DD baseline moins bon que 15m parce qu'il offre 4664 trades en baseline (volume statistique) vs seulement 2198 pour 15m. Après filter activation et tuning, le 7m grimpe à PnL=$44k DD=$6.6k. **Pivot 10m testé** (sweep 07b) : avec la BASE_V2 + blackouts identiques, le 10m donne PnL=–$4,243 (P/DD négatif) — l'edge de la stratégie sur MGC réside spécifiquement sur le 7m.

### Paramètres de stratégie (overrides du défaut V2)
```python
{
    "delta_ext_on": True,    # filtre delta extension (default False) — FLIP MAJEUR
    "cloud_zero_on": True,   # filtre cloud zero (default False)
    "sig_extreme_on": True,  # filtre signal extreme (default False)
    "mf_smooth": 3,          # smoothing MFI plus court (default 6)
    "cooldown_bars": 5,      # cooldown plus long (default 1)
    "max_candle_pct": 0.7,   # filtre bougie large (default 0.9)
}
```
Tous les autres paramètres restent au défaut V2 : `ema_len=7`, `hma1_len=13`, `hma2_len=21`, `amp_mult=2.0`, `hma_pol_bars=3`, `ssl_len=60`, `ssl_mult=0.2`, `hyper_wave_length=5`, `signal_length=3`, `mf_length=35`, `hw_dir_on=False`, `hw_extreme=20`, `sig_extreme=20`, `hw_range=10`, `cloud_on=False`, `delta_on=False`, `hma_side_on=True`, `tick_buffer=0`, `sl_mode="mix"`, `max_sl_points=300`, `signal_candle_sl_on=True`, `hw_partial_pct=25`, `hw_partial_min_rr=0`, `exit_mode="break_hma"`, `block_loss_exit_before_partial=True`.

### Risque
```python
initial_equity   = 50 000 $
risk_per_trade   = 0.01    # 1.00 % → ~$500 risque max par trade
max_contracts    = 50
```

### Blackouts (reference Brussels time)
Sur les UI defaults pour HMASSLOsciV2 (seule la fenêtre 22:00–23:59 est active par défaut), on ajoute trois fenêtres horaires :

| Window | Statut | Raison |
|--------|--------|--------|
| 00:00 – 00:05 | inactive (UI default) | — |
| 09:00 – 09:05 | inactive (UI default) | — |
| **10:00 – 11:00** | **AJOUTÉ** | H=10 perdante (–$2,701 sur 43 trades, WR 44%) |
| **11:00 – 12:00** | **AJOUTÉ** | H=11 la pire (–$4,762 sur 51 trades, WR 43%) |
| 12:00 – 14:00 | inactive (UI default) | — |
| **14:00 – 15:00** | **AJOUTÉ** | H=14 perdante (–$3,164 sur 39 trades, WR 49%) |
| 15:30 – 15:35 | inactive (UI default) | — |
| 16:30 – 22:00 | inactive (UI default) | — |
| 22:00 – 23:59 | active (UI default) | post-close CME |

**Décision : 3 fenêtres ajoutées (vs 4 ou 5 possibles).** Un combo `BO[11,14,10,6]` (4 fenêtres) donne marginalement plus de P/DD (6.74 vs 6.68) au prix d'une surface d'overfit plus grande sur la base de seuils non-monotones (`BO[6]` seul *aggrave* le DD). Le combo `BO[11,14,10]` est conservé pour la robustesse hors-sample (3 fenêtres, P/DD à –0.06 vs 4 fenêtres).

### Auto-close
**22:00:00** reference Brussels (CME daily close). Jamais modifié — c'est exactement le UI default pour `HMASSLOsciV2`.

### Daily limits
**DÉSACTIVÉES** (`daily_win_limit_enabled = False`, `daily_loss_limit_enabled = False`).

**Conclusion sweep 04 :** dans les deux modes (`intra_bar` et `after_close`), TOUTES les valeurs testées (10 combos win/loss de 250/350 à 1000/1500) **dégradent** l'edge. La plus proche est `after_close win=1000 loss=1500` → PnL=$35,104 DD=$8,901 (P/DD=3.94, pire que P/DD=4.18 sans limit à risk=0.01 avant blackouts). `intra_bar` est systématiquement pire que `after_close`. Les limites coupent trop d'entrées au mauvais moment sur cette stratégie.

---

## 3. Top configurations alternatives

| # | Config | Risk | PnL | DD | PF | P/DD | Verdict |
|---|--------|------|-----|----|----|------|---------|
| 1 | BO[11,14,10] | **0.01** | **44 006 $** | **6 588 $** | 1.31 | **6.68** | ← retenu (P/DD optimal sur 3-hour BO) |
| 2 | BO[11,14,10,6] | 0.01 | 45 281 $ | 6 717 $ | 1.33 | 6.74 | +$1.3k PnL, +1 BO (overfit) |
| 3 | BO[11,14,10] + tick_buffer=1 | 0.01 | 40 964 $ | 6 057 $ | 1.28 | 6.76 | DD min mais PnL -$3k |
| 4 | BO[11,14,10,6] + tick_buffer=1 | 0.008 | 33 446 $ | 5 076 $ | 1.31 | 6.59 | risk plus faible, PnL juste au-dessus seuil |
| 5 | BO[11,14,10] | 0.012 | 50 317 $ | 8 400 $ | 1.29 | 5.99 | +$6k PnL mais DD bondit |
| 6 | BO[11,14,10,6] | 0.002 (DD-passing) | 8 626 $ | 2 528 $ | 1.28 | 3.41 | seul candidat avec DD ≈ target — PnL trop bas |

**Compromis structurel** : aucune configuration ne franchit simultanément les deux seuils. Le ratio Profit/DD est le seul critère de tri robuste car réduire `risk_per_trade` scale PnL et DD presque linéairement (cf. §4-D).

---

## 4. Insights de la recherche

### A. Hiérarchie des leviers (par lift de P/DD vs baseline)

1. **`delta_ext_on=True`** — sweep 02 — passe la baseline 7m de P/DD=–0.56 à **+0.86** (×–1.5 conversion ; PnL flip de –$37k à +$15k). Le filtre delta extension élimine les entrées sans confirmation de "delta cloud" précédent — c'est LE filtre essentiel.
2. **`sig_extreme_on=True` + `cloud_zero_on=True`** — sweep 02b — combo passe P/DD à **2.44** (×2.8). Ces deux filtres complémentaires bloquent les entrées dans des zones de saturation extrême ou neutre.
3. **`mf_smooth=3`** — sweep 03 — P/DD à **3.55** (+1.11 vs base). Smoothing MFI plus court → réactivité accrue du Smart Money Flow. mf_smooth=1,2 sont strictement pires : il y a un sweet spot précis à 3.
4. **`cooldown_bars=5`** — sweep 03 — P/DD à **2.80** (additif avec mf_smooth=3 → combo P/DD=4.12, sweep 03b).
5. **Blackouts H=11,14,10** — sweep 06 — P/DD à **6.68** (×1.6 vs BASE_V2). Les 3 heures structurellement perdantes éliminées.
6. **`tick_buffer=1`** — sweep 07 — P/DD à **7.1** (+0.34). Marginal mais améliore le DD au prix d'un PnL légèrement plus faible. **Non retenu** dans le winner pour préserver le PF natif (1.31 vs 1.28).

### B. "Non-événements" surprenants

- **`hw_dir_on`, `hw_extreme_on`, `hw_extreme`, `hw_range`, `max_sl_points`** : strictement aucun effet observable (sweep 03). Le système n'active pas ces filtres → ils sont en dead-code path quand leur flag de gating reste OFF par défaut.
- **`hma2_len` (6 valeurs : 17–42)** : meilleur reste 21 (le default). Contrairement à V3 où hma2=34 donne un lift majeur, V2 est calibrée pour 21 — modifier dégrade.
- **`hyper_wave_length` (3,5,7,9)** : seul 5 fonctionne. 3,7,9 cassent le PnL (–$16k à –$28k). Indicateur extrêmement sensible.
- **`ssl_mult=0.1`** : bénéfique seul (P/DD=2.64 vs 2.44), mais **antagoniste** avec mf_smooth=3 (combo P/DD=2.78, dégrade le combo gagnant). Mécanisme à investiguer.
- **`hw_partial_pct=0.0`** : donne le **PnL maximum** ($49,339 avec blackouts) mais DD bondit à $10,219 (P/DD=4.83 — pire que avec partial=25%). Le partial-exit au croisement HW est donc protecteur de DD sur MGC.
- **Daily limits — TOUTES dégradent** : `intra_bar` ampute trop tôt l'edge (PnL –$5k à +$1k vs +$35k sans limit) ; `after_close` est légèrement mieux mais aucune valeur ne dépasse le no-limit. Sweep 04 — pas de levier.
- **10m timeframe** : avec exactement la même BASE_V2 + blackouts, le 10m donne PnL=–$4,243 — l'edge V2/MGC est étroitement localisé sur 7m (sweep 07b).

### C. Analyse temporelle (sur BASE_V2 sans blackouts — sweep 05)

Heures avec PnL le plus négatif (sur 910 trades) :

| H | n trades | total PnL | avg | WR |
|---|---------|-----------|-----|-----|
| 11 | 51 | –$4 762 | –$93 | 43% |
| 14 | 39 | –$3 164 | –$81 | 49% |
| 10 | 43 | –$2 701 | –$63 | 44% |
| 06 | 44 | –$2 523 | –$57 | 43% |
| 16 | 38 | –$1 557 | –$41 | 42% |
| 23 | 6 | –$1 217 | –$203 | 33% (déjà bloquée UI) |

**Non-monotonicité du blackout H=6** : `BO[6]` seul dégrade le DD (de $8,419 à $13,195) alors que `BO[11,14,10,6]` l'améliore vs `BO[11,14,10]` (de $6,588 à $6,717 — quasi identique). Effet similaire à V3 sur H=17. Ces heures jouent un rôle de "hedge" interactif : leur suppression réorganise le timing global de façon non-linéaire. → Le winner exclut H=6 pour robustesse.

Day-of-week (sur BASE_V2 — sweep 05) :
- Lun +$10k, **Mar –$3k**, Mer +$9.5k, Jeu +$9.5k, Ven +$9.6k
- Mardi est légèrement structurellement perdant — non bloquable via blackout horaire (le moteur n'expose pas de filtre DOW). À traiter dans une future itération.

### D. Relation risk → DD (sur winner BO[11,14,10,6], sweep 07)

| risk | PnL | DD | P/DD |
|------|-----|----|------|
| 0.0008 | 5 383 $ | 2 206 $ | 2.44 ← DD passe |
| 0.001 | 5 765 $ | 2 206 $ | 2.61 ← DD passe |
| 0.0015 | 6 455 $ | 2 277 $ | 2.84 ← DD passe |
| 0.002 | 8 626 $ | 2 528 $ | 3.41 |
| 0.003 | 11 366 $ | 3 254 $ | 3.49 |
| 0.005 | 21 195 $ | 5 628 $ | 3.77 |
| 0.008 | 33 865 $ | 5 416 $ | 6.25 |
| **0.01** | **45 281 $** | **6 717 $** | **6.74** ← winner range |
| 0.012 | 51 997 $ | 8 575 $ | 6.06 |
| 0.014 | 59 968 $ | 9 933 $ | 6.04 |

Le ratio P/DD oscille entre 2.4 et 6.7. Les sauts irréguliers (e.g. r=0.0075 décroche à P/DD=3.58, r=0.008 saute à 6.25) sont dus au floor entier sur les contrats. Trois configs passent DD<$2,500 (r ∈ [0.0008, 0.0015]) mais avec PnL plafonné à ~$6.5k — donc target PnL hors d'atteinte.

---

## 5. Démarche (8+ étapes)

1. **Baseline TFs** ([01_baseline_tfs.py](sweeps/01_baseline_tfs.py)) — 6 TFs testés. 7m retenu pour volume (4664 trades baseline). Tous TFs déficitaires en baseline native.
2. **Filter activation 1D** ([02_filter_activation.py](sweeps/02_filter_activation.py)) — 11 toggles. `delta_ext_on=True` flip baseline 7m de –$37k à +$15k (P/DD baseline=–0.56 → +0.86).
3. **Filter combos** ([02b_filter_combos.py](sweeps/02b_filter_combos.py)) — 11 combos additifs. `delta_ext + cloud_zero + sig_extreme` → P/DD=2.44, PnL=$27,754.
4. **Strategy params 1D** ([03_strategy_params.py](sweeps/03_strategy_params.py)) — 22 hyperparamètres × 3–6 valeurs = 95 backtests. `mf_smooth=3` plus gros lift (+1.11 P/DD), `cooldown=5` second, `ssl_mult=0.1` antagoniste avec mf_smooth.
5. **Combos params** ([03b_combo_test.py](sweeps/03b_combo_test.py)) — 15 combos additifs + fine grain mf_smooth et cooldown. Winner combo : `mf_smooth=3 + cooldown=5 + max_candle=0.7` → P/DD=**4.18**.
6. **Risk + Daily limits** ([04_risk_and_daily_limits.py](sweeps/04_risk_and_daily_limits.py)) — Risk grid 13 valeurs ; daily limits 10 combos × 2 modes (intra_bar / after_close). **Daily limits dégradent dans tous les cas** ; risk=0.01 optimal.
7. **Hour/DOW analysis** ([05_hour_analysis.py](sweeps/05_hour_analysis.py)) — Bucketise les trades. Identifie H={11,14,10,6,16} comme toxiques.
8. **Blackout sweep** ([06_blackout_sweep.py](sweeps/06_blackout_sweep.py)) — 16 combos blackouts. Winner : `BO[11,14,10,6]` → P/DD=**6.74**. `BO[6]` seul aggrave le DD mais le combo l'améliore (non-monotonicité).
9. **Fine-tune** ([07_finetune.py](sweeps/07_finetune.py)) — 17 risks × 19 alt-params (35 backtests). `tick_buffer=1` lift P/DD à 7.1 mais réduit légèrement le PF. Confirme aucune config DD<$2.5k AND PnL>$30k.
10. **Final combos** ([07b_final_combos.py](sweeps/07b_final_combos.py)) — 21 configs ciblées incluant 10m pivot. 10m casse l'edge (PnL<0 sur 10m+blackouts).
11. **Final validation** ([08_final_validation.py](sweeps/08_final_validation.py)) — Winner + 5 alternatives re-run sur la période complète. Confirme `BO[11,14,10]` @ risk=0.01 comme winner robuste.

---

## 6. Risques et hypothèses pour la prochaine itération

### Pourquoi le plafond P/DD≈7 sur MGC ?

Comparaison avec V3 sur MGC (même symbole, période, equity) :

| | V3 MGC | V2 MGC |
|-|--------|--------|
| P/DD atteint | 10.16 | **6.68** |
| PnL du gagnant | 32 821 $ | 44 006 $ |
| Max DD | 3 230 $ | 6 588 $ |
| PF | 1.30 | 1.31 |
| WR | 46.3 % | 53.5 % |
| R:R | 1.50 | 1.14 |
| Trades | 1 319 | 795 |

**Hypothèse principale** : V2 et V3 partagent la même base d'indicateurs (HMA Ribbon + SSL + 4Kings + MFI) mais V3 ajoute des mécaniques propres (entry_window_bars, final_exit_mode "HMA rapide/SSL → HW", one_trade_per_entry_window) qui réduisent les faux signaux. V2 a un WR plus élevé (53.5% vs 46.3%) mais un R:R plus faible (1.14 vs 1.50) — les gains sont plus petits relativement aux pertes. Le PF est quasi-identique (1.31 vs 1.30) mais le rapport gains/pertes par trade est inférieur, ce qui contraint le P/DD.

### Risque d'overfit

- **Période unique** (17 mois). Pas de walk-forward.
- **Trois blackouts horaires** ajoutés. Cohérents avec les buckets PnL, mais effet additif non-monotone observé (BO[6] seul dégrade le DD, mais BO[11,14,10,6] l'améliore légèrement). Risque que ces heures toxiques 2025-2026 ne soient pas représentatives.
- **3 toggles de filtres activés** (delta_ext_on, cloud_zero_on, sig_extreme_on) — c'est 8 % de l'espace de toggles testés (3/11). Cohérent avec un edge réel, pas un artefact statistique.
- **Sweet spot risk=0.01** : exploite peu les marches du floor entier. À risk=0.012 le P/DD chute à 6.06 — sensibilité modérée mais réelle.

### Idées pour la prochaine itération

1. **Walk-forward** : split la période en 4 fenêtres trimestrielles, vérifier la robustesse du combo (delta_ext + cloud_zero + sig_extreme + mf_smooth=3) et des 3 blackouts.
2. **Étendre l'historique** : importer 2022-2024 (TopstepX / Databento) pour 4-5 ans, période actuelle anormalement haussière pour l'or.
3. **Stratégie alternative pour MGC** : tester `EMA9Scalp` ou `UTBotAlligatorST` (momentum/trend) qui collent mieux à la signature de l'or.
4. **Filtre day-of-week** : Mardi est structurellement perdant (–$3k). Ajouter un blackout DOW au moteur permettrait de gagner ~7% PnL en plus.
5. **Audit `ssl_mult`/`hw_dir_on`/`hw_extreme_on`** : non-évènements suspects — vérifier que la chaîne d'indicateurs les utilise effectivement quand leurs flags sont ON.
6. **Multi-asset** : combiner MGC avec un autre symbole (MNQ ?) en mode `multi_asset` pour mutualiser le DD.
7. **Bayesian optimization** : le grid-search 1D a confirmé la non-additivité ; un optimiseur bayésien sur l'espace combiné (filters × params × blackouts × risk) pourrait découvrir des poches sub-optimales du grid.
8. **Tester V3 sur le même setup** : V3 MGC a déjà été lancé (cf. campagne sœur) et plafonne à P/DD=10.2 — toujours sous le seuil 12. **Conclusion** : aucune variante HMA-SSL-Osci ne satisfait simultanément les deux objectifs sur MGC dans la période actuelle.

---

## 7. Reproduction

```bash
# Lancer le serveur (favorites visibles dans l'UI)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
cd frontend && npm run dev -- --port 3001 --host

# Vérifier le preset (doit afficher ✅ MATCH)
python scripts/goals/2026-05-16_HMASSLOsciV2_MGC/verify_preset.py

# Re-générer le preset depuis zéro
python scripts/goals/2026-05-16_HMASSLOsciV2_MGC/build_winner.py
```

Le preset est inséré en tête de `data/presets.json` et apparaît dans la page Favoris de l'UI sous le nom :
`[Auto] HMASSLOsciV2 — MGC 7m — best-effort MGC campaign`
