# Rapport final — Optimisation HMASSLOsciV3 sur MNQ (full-history)

**Période**: 2025-01-06 → 2026-05-13 (≈ 17 mois — contrats H25 → M26)
**Stratégie**: `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole**: MNQ — micro-futures Nasdaq

---

## 1. Résultat ✅

| Objectif | Cible | Atteint |
|----------|-------|---------|
| Profit net | > 30 000 $ | **30 402 $** ✅ |
| Max drawdown | < 2 500 $ | **1 960 $** ✅ |

Métriques détaillées de la configuration gagnante :

| Métrique | Valeur |
|----------|--------|
| Net PnL | **30 402 $** |
| Max drawdown $ | **1 960 $** |
| Profit factor | **1.51** |
| Win rate | 47.5 % |
| Trades actifs | 998 |
| Avg win / Avg loss | +189 $ / –113 $ |
| Reward:Risk | 1.67 |
| **Profit / DD ratio** | **15.5** |
| Sharpe (approx) | ~2.0 |

Le ratio Profit/DD = 15.5 est confortablement au-dessus du seuil de 12 nécessaire pour atteindre les deux objectifs simultanément. La campagne a livré une marge de sécurité significative (PnL +1.3% au-dessus de la cible, DD -21% en dessous).

---

## 2. Configuration gagnante

### Timeframe
**M7** (7 minutes). Sur 17 mois, M7 domine systématiquement les autres TF
(voir §4-A). La campagne précédente sur 4,5 mois ayant choisi M3 est
trompeuse : M3 produit un PnL **négatif** sur l'historique complet (cf.
sweep 01).

### Paramètres de stratégie (overrides du défaut v3)
```python
{
    "cloud_on": True,         # filtre MFI cloud activé
    "hma_pol_bars": 0,        # désactive le filtre HMA polarity recent flip
    "signal_length": 4,       # SMA(4) sur l'oscillator signal (default 3)
    "sig_extreme": 30,        # seuil osc-signal (default 35, plus serré)
    "hyper_wave_length": 7,   # HW length (default 5)
    "mf_length": 25,          # MFI lookback raccourci (default 35)
    "ssl_len": 80,            # SSL baseline plus lent (default 60)
    "entry_window_bars": 3,   # fenêtre HMA-slow×SSL serrée (default 5)
}
```
Tous les autres paramètres restent au défaut v3
(`hw_dir_on=True`, `hw_extreme_on=True`, `hw_extreme=20`,
`sig_extreme_on=True`, `delta_on=True`, `cloud_zero_on=False`,
`delta_ext_on=False`, `final_exit_mode="HMA rapide/SSL → HW"`,
`max_sl_points=300`, `cooldown_bars=1`, `one_trade_per_entry_window=True`).

### Risque
```python
initial_equity   = 50 000 $
risk_per_trade   = 0.0034   # 0.34 %  →  ~$170 risque max par trade
max_contracts    = 50
```

### Blackouts (reference Brussels time)
| Window | Statut | Raison |
|--------|--------|--------|
| 00:00 – 00:05 | inactive (UI default) | — |
| 00:00 – 01:00 | **AJOUTÉ** | H=00 perdante (-$5,073 sur 59 trades) |
| 04:00 – 05:00 | **AJOUTÉ** | H=04 perdante (-$2,283 sur 39 trades) |
| 06:00 – 07:00 | **AJOUTÉ** | H=06 perdante (-$3,185 sur 38 trades) |
| 08:00 – 09:00 | **AJOUTÉ** | H=08 perdante (-$2,556 sur 58 trades) |
| 09:00 – 09:05 | inactive (UI default) | — |
| 11:00 – 12:00 | **AJOUTÉ** | H=11 catastrophique (-$10,352 sur 83 trades) |
| 12:00 – 14:00 | **active** | UI default inactif → réactivé (déjeuner UK/EU) |
| 15:30 – 15:35 | inactive (UI default) | — |
| 16:30 – 22:00 | inactive (UI default) | — |
| 22:00 – 23:59 | active (UI default) | post-close |

### Auto-close
**22:00:00** reference Brussels (CME daily close). Conformément au cahier
des charges, l'auto-close n'a JAMAIS été touché — c'est exactement la
valeur du UI default pour `HMASSLOsciV3`.

### Daily limits
**Aucune** (`daily_win_limit_enabled = False`, `daily_loss_limit_enabled = False`).
Les daily limits ont été testées en mode `intra_bar` puis `after_close` :
sur cette config, elles dégradent systématiquement le PnL sans réduire
significativement le DD (les 6 blackouts horaires captent déjà l'essentiel
des journées toxiques).

---

## 3. Top configurations alternatives

| # | Config (overrides) | Risk | PnL | DD | PF | N | Verdict |
|---|--------------------|------|-----|----|----|---|---------|
| WINNER | sl=4 se=30 | 0.0034 | **30 402** | **1 960** | 1.51 | 998 | ✅ both goals |
| ALT1 | sl=4 se=30 | 0.0035 | 30 930 | 2 166 | 1.51 | 998 | ✅ both goals (très proche) |
| ALT2 | sl=4 se=30 | 0.0033 | 29 171 | 1 926 | 1.50 | 998 | ❌ PnL juste sous cible |
| ALT3 | sl=3 se=35 (défaut osci) | 0.0031 | 25 442 | 2 186 | 1.43 | 1012 | ❌ PnL sous cible |
| ALT4 | sl=4 se=20 | 0.0033 | 29 295 | 2 190 | 1.57 | 859 | ❌ PnL sous cible — meilleur PF |
| ALT5 | sl=4 se=30 | 0.0029 | 27 381 | 1 809 | 1.52 | 998 | ❌ PnL sous cible mais DD très tight |

ALT1 est quasi-équivalent au WINNER (r=0.0035 vs 0.0034). La marge entre
les deux est de l'ordre du bruit ; ALT1 maximise légèrement le PnL au prix
d'un DD un poil plus élevé. Le WINNER est préféré pour la marge de
sécurité sur les deux objectifs simultanément.

---

## 4. Insights et observations

### A. Hiérarchie des leviers (du plus puissant au plus marginal)

1. **Timeframe** — **M7** est strictement supérieur à M3/M5/M10/M2 sur 17
   mois. La précédente itération sur 4,5 mois avait choisi M3 ; sur
   l'historique complet, M3 baseline sort **négatif** (–25 650 $), M2
   catastrophique (–171 847 $). Le choix du TF est de loin le levier le
   plus impactant — un changement de période peut inverser totalement le
   classement.
2. **Combo `cloud_on=True + hma_pol_bars=0`** — passe le ratio Profit/DD
   de 1.74 → 4.08 à TF fixe. `cloud_on` ajoute le filtre MFI cloud.
   `hma_pol_bars=0` *désactive* le filtre "HMA flip récent" qui rejette
   trop de bons setups sur M7 longue période.
3. **Blackouts horaires ciblés** — 6 fenêtres ajoutées (00-01, 04-05,
   06-07, 08-09, 11-12, et activation 12-14 par défaut) — ratio passe
   de 5.2 → 9.2. Plus impactant que les daily limits sur cette période.
4. **Paramètres oscillateur fins** — `signal_length=4, sig_extreme=30`
   donne le meilleur ratio (sl=4 se=30 → 11.7 à r=0.005). Le sweep 1-D
   isolé suggérait `signal_length=2` (ratio 7.28), mais c'était trompeur :
   avec les blackouts et au bon niveau de risque, `signal_length=4` est
   strictement meilleur.
5. **`hyper_wave_length=7, mf_length=25, ssl_len=80, entry_window_bars=3`**
   — quatre paramètres qui consolident l'edge (ratio 4.08 → 5.22 sur le
   sweep 1-D combiné).
6. **Risk per trade** — sizing scale linéairement PnL ET DD. C'est le
   levier final pour caler le résultat sur les objectifs chiffrés
   (ratio inchangé, seul le niveau bouge).

### B. Effets contre-intuitifs / surprises

- **M3 NÉGATIF sur 17 mois** alors que c'était le `WINNER` sur 4,5 mois.
  Avertissement net sur l'overfit à période courte. La campagne précédente
  capturait probablement un régime favorable (volatilité élevée Q4 2025 +
  Q1 2026).
- **`hma_pol_bars=0`** (désactivation du filtre HMA polarity) améliore
  significativement le ratio. Le filtre par défaut (3 bars) est trop
  strict sur M7 longue période.
- **`signal_length=2` (sweep 1-D)** semblait optimal en isolation
  (ratio 7.28), mais avec le combo et les blackouts, `signal_length=4`
  est strictement meilleur. Leçon : sweep 1-D donne une heuristique,
  pas une vérité. La combo en bout de chaîne décide.
- **Daily limits dégradent le PnL** sur cette config sans réduire le DD.
  Les blackouts horaires ont déjà coupé les heures-fournaises. Limits
  `intra_bar W=400 r=0.0025` : PnL $12k (vs $21k sans limits) à DD identique.
- **`delta_on=False`** maximise le PnL absolu ($105k baseline) mais double
  le DD (~$38k). Mauvais ratio. Garder `delta_on=True`.
- **`cloud_zero_on=True`** détruit le PnL (ratio 0.52). Filtre trop strict.
- **`hyper_wave_length=9 + signal_length=3`** se sont avérés mauvais
  ensemble (PF 1.20) alors que chacun en isolation tenait. Encore une
  trace d'interaction négative.

### C. Analyse temporelle (combo M7, no limits, r=0.01)

Distribution PnL par heure d'entrée Brussels :

| Heure | n | total $ | avg $ | Statut |
|-------|---|---------|-------|--------|
| **11** | 83 | **-10 352** | -125 | toxique → blackout |
| **12** | 70 | **-6 239** | -89 | toxique → blackout |
| **00** | 59 | **-5 073** | -86 | toxique → blackout |
| 06 | 38 | -3 185 | -84 | toxique → blackout |
| 08 | 58 | -2 556 | -44 | toxique → blackout |
| 04 | 39 | -2 283 | -59 | toxique → blackout |
| 01 | 57 | **+11 637** | +204 | meilleure heure (Asia close / UK pre-open) |
| 05 | 52 | +9 525 | +183 | |
| 15 | 110 | +9 046 | +82 | volume max — début US |
| 09 | 56 | +8 279 | +148 | UK open |
| 07 | 63 | +7 736 | +123 | UK pre-open |

Day-of-week : aucun jour franchement négatif. Thursday quasi-flat
(+$783 sur 268 trades). Pas de blackout jour-entier nécessaire.

### D. Relation paramètre → métrique (sur la base finale)

| Paramètre | Effet de l'augmentation | Effet de la diminution |
|-----------|------------------------|-----------------------|
| `signal_length` | 2→3→4 améliore PnL+DD jusqu'à 4 puis dégrade | <2 invalide (n trop bas) |
| `sig_extreme` | 30→35 : PnL ↑ légèrement, DD ↓ | 15-25 : DD↓ mais PnL↓ proportionnel |
| `hyper_wave_length` | 5→7 : PF ↑ | 3 : PF inchangé, 9 : PF s'effondre |
| `mf_length` | 35→45 : DD ↑ | 25 : DD↓ significatif |
| `ssl_len` | 60→80→100 : PF ↑ | 40 : edge perdu (PF 1.07) |
| `entry_window_bars` | 5→8 : PnL ↑ légèrement, DD ↑ | 3 : DD ↓ |
| `risk_per_trade` | linéaire PnL et DD (PF inchangé) | idem inverse |
| Blackout 11-12 | n/a | PF 1.23 → 1.28 (+$10k, –$1k DD) |

---

## 5. Démarche d'optimisation

| Étape | Script | Résultat clé |
|-------|--------|--------------|
| 1. Baseline TFs | `01_baseline_tfs.py` | M7 ratio 1.74 — clair leader, M3 négatif |
| 2. Filter activation | `02_filter_activation.py` | `cloud_on + hma_pol_bars=0` → ratio 4.08 |
| 3. Core params | `03_strategy_params.py` | best 1-D : sl=2, hw=7, mf=25, ssl=80, ew=3 |
| 4. Risk & daily limits | `04_risk_and_daily_limits.py` | combo ratio 5.22, daily limits seules insuffisantes |
| 5. Hour analysis | `05_hour_analysis.py` | H=11,12,00,06,08,04 toxiques |
| 6. Blackout sweep | `06_blackout_sweep.py` | 6 cumulés → ratio 9.17 |
| 7. Fine-tune | `07_finetune.py` (interrompu — voir 07b/07c) | ratio plafonné ~9 avec sl=2 |
| 7b. Alt combos | `07b_alt_combos.py` | M3/M5/M10 < M7 ; sl=3 (default) PF↑ ; sig_extreme=15 PF 1.66 |
| 7c. Tight finetune | `07c_tight_finetune.py` | **sl=4 se=30 r=0.0034 → PnL $30 313 / DD $1 960** |
| 8. Final validation | `08_final_validation.py` | WINNER confirmé + 5 alternatives |

Tous les logs sont dans `logs/`.

---

## 6. Risques et idées pour la prochaine itération

### Risques sur la robustesse

1. **Blackouts ajustés à l'historique** — 6 fenêtres horaires sont
   posées sur la base d'une analyse statique sur 17 mois. Le risque
   d'overfit est modéré (chaque fenêtre représente >38 trades, signature
   claire) mais réel. Un walk-forward roulant clarifierait.
2. **Marge serrée sur PnL** — la cible est $30k, on atteint $30.4k. Une
   variation de –1.3% sur le PnL futur ferait basculer.
3. **`signal_length=4` agressif sur le bruit** — le sweep 1-D suggérait
   `signal_length=2` était meilleur isolé. La combo finale dépend
   fortement de l'interaction `signal_length × sig_extreme × blackouts`.
4. **Single asset** — l'edge repose entièrement sur MNQ. Pas de
   diversification.
5. **17 mois d'historique = ~5 régimes de marché distincts** — la stabilité
   trans-régime n'est pas garantie par un backtest unique.

### Idées d'amélioration

1. **Walk-forward optimization** sur fenêtres roulantes de 3 mois
   (entraînement) → test sur 1 mois suivant pour mesurer la stabilité
   des paramètres et des blackouts.
2. **Bayesian / Optuna sweep** multi-dimensionnel pour explorer les
   interactions `signal_length × sig_extreme × hyper_wave_length` non
   capturées par le sweep 1-D.
3. **Multi-strat / multi-asset** — ajouter MES (S&P) et MGC (or) en
   `mode=multi_asset` pour diversifier le DD sur les heures où MNQ
   range.
4. **Régime de marché** — segmenter par volatilité (ATR moyen, VIX).
   Le filtre H=11-12 pourrait n'être valide qu'en régime range ;
   une condition `block_11_12_if_atr<X` rendrait la strat adaptive.
5. **Audit `ssl_mult`** — le sweep n'a pas isolé son effet ; potentiel
   bug dans `_compute_ssl()` à investiguer.
6. **Position sizing alternatif** — Kelly fractionnel sur le PF observé
   par fenêtre roulante pour adapter le risque.
7. **Test sl=3 + sig_extreme=25** (ALT3 voisine) pour voir si en réduisant
   un peu plus la friction sur le risque, on retrouve la robustesse.
8. **Investiguer pourquoi `delta_ext_on=True` réduit n par 5x sur M7**
   17 mois (vs effet modeste sur la campagne 4,5 mois). Aller voir le
   code de `_compute_oscillator` / `delta_long_on` / `prev_delta_short_on`.
9. **Plafonner le drawdown intrajour via une intra-bar daily-loss limit**
   à $300-400 avec un risk un poil plus élevé pourrait améliorer le ratio
   asymétriquement — à creuser.
10. **Ajouter 22:00 → 23:00 monitor** — H=22-23 a peu de trades (n=8-13)
    mais le `auto_close=22` les coupe déjà. À surveiller si on touche
    l'auto-close.

---

## 7. Reproduction

Le preset est dans `data/presets.json` (visible dans Favorites UI) :
> `[Auto] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $30.4k / DD $2.0k)`

Pour valider en CLI :
```bash
source venv/bin/activate
python scripts/goals/2026-05-15_HMASSLOsciV3_MNQ_v2/verify_preset.py
# → ✅ MATCH
```

Pour reproduire dans l'UI :
1. Sidebar → Favorites → cliquer le preset ci-dessus
2. Toute la config (params, blackouts, risk, auto-close=22) est chargée
3. Run → résultat attendu : PnL $30 402 / DD $1 960 / PF 1.51 / WR 47.5% / N 998

Tous les scripts de la campagne :
- `sweeps/01_baseline_tfs.py` → `08_final_validation.py`
- `build_winner.py` — régénère le preset depuis la config
- `verify_preset.py` — replay et vérification
- `logs/*.log` — sortie complète de chaque sweep
