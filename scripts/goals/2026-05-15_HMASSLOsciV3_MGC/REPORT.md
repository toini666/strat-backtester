# Rapport final — Optimisation HMASSLOsciV3 sur MGC

**Période** : 2025-01-06 → 2026-05-15 (≈ 17 mois — historique multi-contrats jusqu'à M26)
**Stratégie** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole** : MGC — micro-futures Gold
**Contrainte spécifique** : daily win/loss limits **désactivées** sur toute la campagne (instruction utilisateur — aucun sweep des daily limits, les deux flags restent off).

---

## 1. Résultat — best-effort, 1 objectif sur 2 atteint ⚠️

| Objectif | Cible | Atteint | Statut |
|----------|-------|---------|--------|
| Profit net | > 30 000 $ | **32 821 $** | ✅ +$2 821 |
| Max drawdown | < 2 500 $ | **3 230 $** | ❌ +$730 |

Métriques détaillées de la configuration retenue :

| Métrique | Valeur |
|----------|--------|
| Net PnL | **32 821 $** |
| Max drawdown $ | **3 230 $** |
| Profit factor | **1.30** |
| Win rate | 46.3 % |
| Trades actifs | 1 319 |
| Avg win / Avg loss | +236 $ / –157 $ |
| Reward:Risk | 1.50 |
| **Profit / DD ratio** | **10.16** |

**Pourquoi DD ne passe pas ?** Sur MGC, le ratio Profit/DD atteint un **plafond structurel autour de 10.0–10.2** quelle que soit la configuration testée (>150 configurations sur 7 sweeps, dont 1 sweep 1D × 16 hyperparamètres, 2 sweeps combos additifs, 1 sweep blackouts, 1 sweep risk, 1 sweep exit modes alternatifs, 1 sweep max_contracts × hw_partial_pct, 1 sweep fine risk grid). Or pour satisfaire simultanément PnL > 30k$ ET DD < 2.5k$, il faut un **P/DD > 12.0**. Cette borne n'a été franchie dans **aucune** configuration explorée. Voir §6 (Hypothèses).

> 📌 La campagne de référence MNQ (`scripts/goals/2026-05-15_HMASSLOsciV3_MNQ_v2/REPORT.md`) a atteint P/DD = 15.5 sur la même stratégie. Le différentiel suggère un edge structurellement moindre de la stratégie HMA-SSL-Osci sur la signature de prix de l'or (cf. §6).

---

## 2. Configuration retenue (winner_preset.json)

### Timeframe
**M7** (7 minutes). Sur les TFs prioritaires explorés en baseline :

| TF | PnL baseline | DD baseline | P/DD |
|----|-------------|-------------|------|
| 7m | +10 316 $ | 19 012 $ | **0.54** ← meilleur |
| 10m | +9 086 $ | 19 995 $ | 0.45 |
| 15m | –3 639 $ | 23 031 $ | –0.16 |
| 3m | –127 579 $ | 153 576 $ | –0.83 |
| 5m | –86 018 $ | 93 858 $ | –0.92 |
| 2m | –161 504 $ | 174 022 $ | –0.93 |

Les TFs courts (≤5m) sont catastrophiques sur MGC (PnL et DD explosent) — le bruit microstructure noie l'edge des indicateurs de la stratégie.

### Paramètres de stratégie (overrides du défaut v3)
```python
{
    "hw_range_on": True,    # filtre "range osc" activé (default False) — +PnL et PF
    "hma2_len": 34,         # HMA lente plus longue (default 21) — gros lift de P/DD
}
```
Tous les autres paramètres restent au défaut v3 : `hma_pol_bars=3`, `entry_window_bars=5`, `hma1_len=13`, `ssl_len=60`, `ssl_mult=0.2`, `hyper_wave_length=5`, `signal_length=3`, `mf_length=35`, `mf_smooth=6`, `hw_dir_on=True`, `hw_extreme=20`, `sig_extreme=35`, `hw_range=10`, `cloud_on=False`, `delta_on=True`, `max_sl_points=300`, `cooldown_bars=1`, `one_trade_per_entry_window=True`, `final_exit_mode="HMA rapide/SSL → HW"`, etc.

### Risque
```python
initial_equity   = 50 000 $
risk_per_trade   = 0.0052  # 0.52 %  →  ~$260 risque max par trade
max_contracts    = 50
```

### Blackouts (reference Brussels time)
Sur les UI defaults pour HMASSLOsciV3 (seule la fenêtre **22:00–23:59** est active par défaut), on ajoute trois fenêtres horaires :

| Window | Statut | Raison |
|--------|--------|--------|
| 00:00 – 00:05 | inactive (UI default) | — |
| 03:00 – 04:00 | **AJOUTÉ** | H=03 perdante (–$5,362 sur 77 trades en baseline) |
| 08:00 – 09:00 | **AJOUTÉ** | H=08 perdante (–$6,188 sur 64 trades) |
| 09:00 – 09:05 | inactive (UI default) | — |
| 11:00 – 12:00 | **AJOUTÉ** | H=11 catastrophique (–$8,125 sur 80 trades, WR 32%) |
| 12:00 – 14:00 | inactive (UI default) | — |
| 15:30 – 15:35 | inactive (UI default) | — |
| 16:30 – 22:00 | inactive (UI default) | — |
| 22:00 – 23:59 | active (UI default) | post-close CME |

### Auto-close
**22:00:00** reference Brussels (CME daily close). Jamais modifié — c'est exactement le UI default pour `HMASSLOsciV3`.

### Daily limits
**DÉSACTIVÉES** sur cette campagne (`daily_win_limit_enabled = False`, `daily_loss_limit_enabled = False`). Instruction explicite de l'utilisateur — non swept.

---

## 3. Top configurations alternatives

| # | Config (overrides) | Risk | PnL | DD | PF | P/DD | Verdict |
|---|--------------------|------|-----|----|----|------|---------|
| 1 | hma2=34, hw_range_on, 3 BO | **0.0052** | **32 821 $** | **3 230 $** | 1.30 | **10.16** | ← retenu (PnL passe, DD à +$730) |
| 2 | idem, +cloud_on | 0.005 | 26 087 $ | 2 689 $ | 1.29 | 9.70 | DD à +$189 mais PnL à –$3.9k |
| 3 | hma2=34, hw_range_on, 3 BO | 0.0058 | 36 293 $ | 3 600 $ | 1.29 | 10.08 | PnL fort mais DD pire |
| 4 | hma2=34, hw_range_on, 3 BO | 0.003 | 20 304 $ | 2 027 $ | 1.28 | 10.02 | DD passe, PnL à –$10k |
| 5 | idem +max_sl=100 | 0.005 | 31 493 $ | 3 331 $ | 1.30 | 9.45 | PnL passe, DD pire |

**Compromis structurel** : aucune configuration ne franchit simultanément les deux seuils. Le ratio Profit/DD est le seul critère de tri robuste car réduire `risk_per_trade` scale PnL et DD presque linéairement (cf. §4-D).

---

## 4. Insights de la recherche

### A. Hiérarchie des leviers (par lift de P/DD vs baseline)

1. **`hma2_len`** — extension de 21 → 34 : passe de P/DD≈0.5 à 6.3 (×12). La HMA lente plus longue filtre les retournements faux.
2. **`hw_range_on=True`** (filtre "range osc") : +0.5 → 2.1 (×4). Empêche les entrées dans des zones d'oscillation neutre.
3. **Blackouts H=11, H=08, H=03** : 6.3 → 9.85 (×1.6). Suppriment trois fenêtres horaires structurellement perdantes.
4. **Fine-tuning de `risk_per_trade` autour de 0.0052** : 9.2 → 10.16 — l'augmentation de 0.5 % → 0.52 % bouge légèrement les contrats arrondis, ce qui décale les seuils de DD.
5. **`cloud_on=True`** (filtre MFI cloud) : seul autre delta qui RÉDUIT légèrement le DD (mais coûte $4k de PnL → P/DD baisse à 9.70).

### B. "Non-événements" surprenants

- **`mf_length` et `mf_smooth` (10 valeurs combinées)** : strictement aucun effet quand `cloud_on=False`. Probable lien : ces deux paramètres ne pilotent que le MFI cloud, donc dead-code quand `cloud_on=False`. Logique mais à vérifier.
- **`ssl_mult` (5 valeurs)** : aucun effet observable. Probable que `ssl_mult` ne pilote que les bornes du canal SSL et que la stratégie utilise plutôt le `bbmc` (baseline) — il faudrait auditer la chaîne d'indicateurs.
- **`hw_partial_pct` (15 valeurs avec rr_min varié, sweep 07d-A)** : toutes les valeurs **dégradent** PnL et DD vs default 0. Conclusion : le mécanisme de partial-exit au croisement HW ne génère pas d'edge sur MGC.
- **`max_contracts` cap (8 valeurs, sweep 07d-B)** : aucun effet sur DD au risque actuel (0.005). Le cap n'est pas binding parce que les contraintes de sizing sur ce TF/risk donnent des positions de 1-3 contrats — bien en deçà de 50.
- **`final_exit_mode="% du prix d'entrée en profit"`** (sweep 07c) : toutes les valeurs (0.05 → 0.30 %) **dégradent** vs le mode `"HMA rapide/SSL → HW"` par défaut.
- **Combinaisons 1D** : la combinaison des trois meilleurs gains 1D (`hma2=34 + hyper_wave=7 + entry_window=2`) **dégrade** drastiquement le PnL (de +52k à –3.9k). Les leviers ne sont pas additifs — chaque filtre supplémentaire restreint le set de trades de façon non-linéaire (cf. `logs/03b_combo_test.log`).

### C. Analyse temporelle (sur la base hma2=34)

Heures avec PnL le plus négatif :

| H | n trades | total PnL | avg | WR |
|---|---------|-----------|-----|-----|
| 11 | 80 | –$8 125 | –$102 | 32% |
| 08 | 64 | –$6 188 | –$97 | 38% |
| 03 | 77 | –$5 362 | –$70 | 40% |
| 17 | 69 | –$3 842 | –$56 | 43% |
| 23 | 10 | –$2 390 | –$239 | 20% |

**Surprise** : ajouter le blackout H=17 **dégrade** le DD (de $6.5k à $9.9k) malgré son PnL net perdant. Hypothèse : certains trades de H=17 jouent un rôle de hedge contre des trades H=13–16 ; leur suppression désaligne le timing global et expose à des pertes plus grandes ailleurs. Non investigué plus profondément.

Day-of-week (sur hma2=34) :
- Lun +$10k, Mar +$21k, Mer +$5k, Jeu +$27k, **Ven –$11k**
- Vendredi est structurellement perdant — non bloquable via blackout horaire (le système n'expose pas de filtre day-of-week). À traiter dans une future itération du moteur.

### D. Relation risk → DD (sur winner + 3 BO)

| r | PnL | DD | P/DD |
|---|-----|----|------|
| 0.001 | 14 799 $ | 1 735 $ | 8.53 |
| 0.003 | 20 304 $ | 2 027 $ | 10.02 |
| 0.0050 | 30 648 $ | 3 331 $ | 9.20 |
| **0.0052** | **32 821 $** | **3 230 $** | **10.16** ← winner |
| 0.0055 | 33 967 $ | 4 174 $ | 8.14 |
| 0.0058 | 36 293 $ | 3 600 $ | 10.08 |
| 0.006 | 37 094 $ | 3 829 $ | 9.69 |
| 0.0075 | 47 006 $ | 5 101 $ | 9.22 |
| 0.010 | 64 005 $ | 6 528 $ | 9.81 |

Le ratio PnL/DD oscille entre 9.2 et 10.16 — c'est une **propriété structurelle de la stratégie sur MGC**, pas un paramètre tunable par le risk. Les sauts irréguliers (e.g. r=0.0055 décroche à P/DD=8.14) sont dus au floor entier sur les contrats (`max(1, int(raw))`), qui crée des marches dans la fonction de DD.

---

## 5. Démarche (8 étapes)

1. **Baseline TFs** ([sweeps/01_baseline_tfs.py](sweeps/01_baseline_tfs.py)) — 6 TFs testés. M7 retenu (P/DD=0.54).
2. **Filter activation** ([02_filter_activation.py](sweeps/02_filter_activation.py)) — `hw_range_on=True` et `hma_pol_bars=5` identifiés comme deltas positifs (P/DD ≈ 2.0).
3. **Strategy params 1D** ([03_strategy_params.py](sweeps/03_strategy_params.py)) — 16 hyperparamètres × 4-8 valeurs = 79 backtests. `hma2_len=34` plus gros lift (P/DD=6.32 seul). Le combo test ([03b_combo_test.log](logs/03b_combo_test.log)) montre que les 1D-winners ne sont pas additifs.
4. **Risk sweep** ([04_risk_sweep.py](sweeps/04_risk_sweep.py)) — risk de 0.001 à 0.01. P/DD oscille 9.0–10.0.
5. **Hour analysis** ([05_hour_analysis.py](sweeps/05_hour_analysis.py)) — Bucketise les trades par heure d'entrée. Identifie H=03, 08, 11, 17, 23 comme toxiques.
6. **Blackout sweep** ([06_blackout_sweep.py](sweeps/06_blackout_sweep.py)) — Combinaison 11h+08h+03h donne le meilleur P/DD (9.85). H=17 dégrade le DD malgré son PnL négatif.
7. **Finetune** ([07_finetune.py](sweeps/07_finetune.py), [07b_cloud_on_combos.py](sweeps/07b_cloud_on_combos.py), [07c_alt_exits_and_hma2.py](sweeps/07c_alt_exits_and_hma2.py), [07d_partial_and_caps.py](sweeps/07d_partial_and_caps.py)) — 22 deltas additifs, 35 combos cloud_on × blackouts × risk, 57 combos hma2-granular × exit-mode-alternatif, et 45 combos hw_partial × max_contracts × fine-risk-grid. Aucun ne franchit P/DD=12. La fine risk grid identifie **r=0.0052** comme sweet spot avec **PnL=$32,821 / DD=$3,230 / P/DD=10.16** — meilleur compromis avec PnL atteint.
8. **Final validation** ([08_final_validation.py](sweeps/08_final_validation.py)) — Re-run du winner et de 4 alternatives sur la période complète : confirme que le winner P/DD=10.16 (r=0.0052) est le meilleur compromis.

---

## 6. Risques et hypothèses pour la prochaine itération

### Pourquoi le plafond P/DD≈10 sur MGC ?

Comparaison avec la campagne MNQ_v2 (même stratégie, 17 mois) :

| | MNQ | MGC |
|-|-----|-----|
| Tick size | 0.25 | 0.10 |
| Tick value | 0.50 $ | 1.00 $ |
| Point value | 2.00 $ | 10.00 $ |
| Volatilité quotidienne typique | ~150 pts | ~10 pts |
| P/DD atteint | 15.5 | 10.16 |
| PF du gagnant | 1.51 | 1.30 |
| WR | 47.5 % | 46.3 % |
| R:R | 1.67 | 1.50 |

**Hypothèse principale** : la signature de prix de l'or (mouvements lents avec spikes news-driven sur GLD/COMEX) déstabilise les indicateurs d'oscillateur de la stratégie (4Kings/MFI/HMA), qui ont été calibrés sur des sous-jacents trend-followers de l'index (NASDAQ). Sur MGC, le ratio gain/perte par trade est intrinsèquement plus faible (R:R 1.50) vs MNQ (R:R 1.67). Avec un WR similaire (~46-47%), l'edge mathématique est plus mince — c'est ce qui contraint le P/DD à ne pas dépasser 10.

### Risque d'overfit

- **Période unique** (17 mois). Pas de walk-forward.
- **Trois blackouts horaires** ajoutés au-dessus de la pure baseline — cohérents avec les buckets PnL, mais risque que les heures toxiques de 2025-2026 ne soient pas représentatives.
- **Fine-tuning du risque (r=0.0052)** : exploite les marches du floor entier des contrats. À r=0.0050 le DD passe à $3,331 et à r=0.0055 il bondit à $4,174 — le sweet spot 0.0052 pourrait ne pas être robuste hors-sample.

### Idées pour la prochaine itération

1. **Walk-forward analysis** : split la période en 4-5 fenêtres et vérifier la robustesse de `hma2_len=34` et des blackouts sur chaque fenêtre.
2. **Étendre l'historique** : importer des données 2022-2024 (via TopstepX ou Databento) pour tester sur 4-5 ans. La période actuelle est anormalement haussière pour l'or.
3. **Stratégie alternative pour MGC** : tester une stratégie de momentum/trend (`EMA9Scalp`, `UTBotAlligatorST`) qui colle mieux à la signature de mouvement directionnelle de l'or.
4. **Filtre day-of-week au niveau moteur** : Friday est structurellement perdante (–$11k). Ajouter un blackout DOW au moteur permettrait de l'éliminer.
5. **Audit `ssl_mult`/`mf_length`/`mf_smooth`** : ces paramètres semblent ne pas avoir d'effet — vérifier que la chaîne d'indicateurs les utilise bien.
6. **Multi-asset** : combiner MGC avec un autre symbole en mode `multi_asset` pour partager le DD entre actifs non-corrélés.
7. **Bayesian optimization** : le grid-search 1D a confirmé la non-additivité ; une optim. bayésienne sur l'espace combiné (hma2 × hw_range × blackouts × risk) pourrait découvrir des poches sub-optimales du grid.

---

## 7. Reproduction

```bash
# Lancer le serveur (favorites visibles dans l'UI)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
cd frontend && npm run dev -- --port 3001 --host

# Vérifier le preset (doit afficher ✅ MATCH)
python scripts/goals/2026-05-15_HMASSLOsciV3_MGC/verify_preset.py

# Re-générer le preset depuis zéro
python scripts/goals/2026-05-15_HMASSLOsciV3_MGC/build_winner.py
```

Le preset est inséré en tête de `data/presets.json` et apparaît dans la page Favoris de l'UI sous le nom :
`[Auto] HMASSLOsciV3 — MGC 7m — best-effort MGC campaign`
