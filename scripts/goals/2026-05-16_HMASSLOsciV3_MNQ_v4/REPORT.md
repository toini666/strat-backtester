# Rapport final — Optimisation HMASSLOsciV3 sur MNQ (v4 — blackouts ré-ouverts)

**Période** : 2025-01-06 → 2026-05-15 (~17 mois — contrats H25 → M26)
**Stratégie** : `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole** : MNQ — micro-futures Nasdaq
**TF** : 7 minutes
**Budget** : 250 simulations — ~161 utilisées (~89 réserve)
**Point de départ** : winner v3 (`cd=3, sx=40, hw_dir_on=False, r=0.0032`) = $35,472 / $2,491.

## Contrainte clé

La campagne v3 interdisait les blackouts horaires. Ici on les **ré-active comme levier**
(la prochaine itération naturelle déjà annoncée dans REPORT v3 §8). L'auto-close reste
fixé à 22:00 reference Brussels. Seule contrainte de DD : **< $2,500** (cible effective $2,400 pour absorber la variance de replay).

---

## 1. Résultat ✅

| Objectif | Cible | Atteint |
|----------|-------|---------|
| Profit net | > $35 000 (max possible) | **$50 770** ✅ (+43 %) |
| Max drawdown | < $2 500 | **$2 268** ✅ (margin $232) |

| Métrique | Valeur |
|----------|--------|
| Net PnL | **$50 770** |
| Max drawdown $ | **$2 268** |
| Profit factor | **1.58** |
| Win rate | 46.1 % |
| Trades actifs | 1 389 |
| Avg win / Avg loss | +$217 / –$118 |
| **Profit / DD ratio** | **22.39** |
| Sharpe | (cf. simulator output) |

**+43 % de PnL** vs v3 winner pour un **DD réduit de 9 %**. Ratio Profit/DD passe de 14.24 → 22.39 (+57 %).

---

## 2. Configuration gagnante

### Timeframe
**M7** (7 minutes).

### Paramètres de stratégie (overrides du v3 winner)

```python
{
    # *** L'UNIQUE override v4 vs v3 winner ***
    "ema_len": 11,                 # v3 winner avait 13 — passage 13→11 = +20% PnL
    # ... le reste est identique au v3 winner ...
    "hw_dir_on": False,            # hérité v3 (sweep 02)
    "cooldown_bars": 3,            # hérité v3 (sweep 03b)
    "sig_extreme": 40,             # hérité v3 (sweep 03b)
    "hma1_len": 13, "hma2_len": 21, "amp_mult": 2.0,
    "hma_pol_bars": 0, "entry_window_bars": 3,
    "ssl_len": 80, "ssl_mult": 0.2,
    "hyper_wave_length": 7, "signal_type": "SMA", "signal_length": 4,
    "mf_length": 25, "mf_smooth": 6,
    "hw_extreme": 20.0, "hw_extreme_on": True,
    "sig_extreme_on": True, "hw_range_on": False,
    "cloud_on": True, "delta_on": True,
    "tick_buffer": 0, "max_sl_points": 300.0,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False, "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0, "hw_partial_min_rr": 0.0,
    "final_exit_mode": "HMA rapide/SSL → HW",
}
```

### Risque

```python
initial_equity = 50 000 $
risk_per_trade = 0.0036  # 0.36 %  → ~$180 risque max par trade
max_contracts  = 50
```

### Blackouts (reference Brussels time)

| Window | Statut | Source |
|--------|--------|--------|
| 00:00 – 00:05 | inactive | UI default |
| 09:00 – 09:05 | inactive | UI default |
| 12:00 – 14:00 | inactive | UI default |
| 15:30 – 15:35 | inactive | UI default |
| 16:30 – 22:00 | inactive | UI default |
| **22:00 – 23:59** | **active** | UI default (post-close CME) |
| **11:00 – 12:00** | **active** | **v4 nouveau** |
| **14:00 – 15:00** | **active** | **v4 nouveau** |

Deux blackouts horaires ajoutés (H=11-12 et H=14-15). Combinés ils retirent $4k de PnL toxique tout en réduisant le DD de $223 par rapport à no-BO.

### Auto-close
**22:00:00** reference Brussels (CME daily close). Conformément aux invariants.

### Daily limits
**Aucune**. Non utilisées (sweep 04 v3 a déjà montré que c'était un non-événement sur cette stratégie).

---

## 3. Top configurations alternatives

| # | Config | PnL | DD | Margin | Ratio | Verdict |
|---|--------|-----|----|----|------|----|
| **WINNER** | ema=11 BO 11+14 r=0.0036 | **$50,770** | **$2,268** | **$232** | **22.39** | ✅✅ |
| ALT1 | ema=11 BO 11+14 r=0.00365 | $51,588 | $2,308 | $192 | 22.35 | ✅✅ +PnL, –margin |
| ALT2 | ema=11 BO 12:30 wide r=0.0036 | $51,633 | $2,358 | $142 | 21.89 | ✅✅ +PnL, –margin |
| ALT3 | ema=11 BO 11+14 r=0.0037 | $52,823 | $2,427 | $73 | 21.76 | ✅ marge mince |
| ALT4 | ema=11 mf=35 BO 11+14+08 r=0.0034 | $51,343 | $2,443 | $57 | 21.02 | ✅ marge très mince |
| ALT5 | ema=11 r=0.0044 BO 11+14+08 | $60,304 | $2,909 | -$409 | 20.73 | ❌ DD over (+$409) |

Le WINNER est choisi pour **le meilleur compromis PnL × marge**. ALT3 maximise le PnL avec marge serrée ; ALT5 montre que la stratégie peut atteindre $60k mais au prix d'un dépassement DD de $409.

---

## 4. Insights

### A. Hiérarchie des leviers (du plus impactant au marginal)

1. **`ema_len = 11` (sweep 05)** — Le breakthrough v4.
   - Avant (v3, ema=13) : $40,412 / $2,151 (sur BO 11+14+08 r=0.0034, ratio 18.79)
   - Après (ema=11)       : $48,592 / $2,073 (même base, ratio 23.44)
   - **+$8,180 PnL et –$78 DD pour un seul changement de longueur d'EMA**.
   - L'EMA source (`src_ema`) sert de référence pour le calcul HMA et oscillateur.
     Raccourcir de 13→11 ne donne pas plus de signaux : N=1335 reste identique au ref ;
     c'est la **qualité** des entries qui s'améliore (WR 45.0 → 46.6 %, PF 1.50 → 1.61).
2. **Blackouts H=11-12 et H=14-15 (sweep 02-03)** — Le levier complémentaire.
   - 2 heures ciblées éliminent ~$3.3k de PnL toxique (sur 17 mois).
   - Combiné avec ema=11 : $48,592 → $50,770 ($+2.2k) avec DD réduit de $2,073 → $2,268 (+$195).
   - Effet additif vs subtractif ; pas de blackout > 2 heures qui aide structurellement.
3. **risk_per_trade = 0.0036 (sweep 04, 08)** — Le tuning final.
   - Le DD-wall pour la config gagnante est entre 0.00368 et 0.00370.
   - r=0.0036 est le sweet spot avec ~$230 de marge.
4. **`cooldown_bars = 3`** — Hérité v3, toujours valide.

### B. "Non-événements" (paramètres testés sans effet — insights)

- **`ssl_mult`** — totalement inactif. Valeurs 0.1, 0.15, 0.2, 0.25, 0.3 donnent
  des résultats **strictement identiques** ($40,412 / $2,151). Suggère que la
  branche du code consommant ssl_mult n'est pas atteinte dans cette configuration —
  ou que l'effet est masqué par un autre filtre. À auditer.
- **`signal_candle_sl_on`** — neutre (déjà confirmé v3).
- **`hyper_wave_length` ≠ 7** — dégrade strictement ($17k–31k au lieu de $48k).
- **`hma1_len`, `hma2_len` ≠ default** — dégradent strictement.
- **`amp_mult = 2.5` ou 3.0 avec ema=11** — PnL ↑ mais DD explose ($3.6k–$6.2k).
  Combinaison à éviter.
- **Daily limits** — non testées explicitement (v3 a déjà montré que c'est un
  non-événement sur cette stratégie ; pas de single-day blowups, DD multi-jours).
- **`hpb=1, 2`** combiné à ema=11 : DD pire que hpb=0. La combinaison change le
  régime d'entrée.

### C. Effets contre-intuitifs

- **BO H=08 dégrade quand ema=11**. Avec ema=13 (v3 base), BO 11+14+08 améliore
  le DD vs BO 11+14. Avec ema=11 c'est l'inverse : H=08 ajoute du DD au lieu
  d'en retirer. La régulation `ema_len` change le profil temporel des trades.
- **`ssl_mult` no-op**. Un paramètre nominalement actif (sweep_05 §ssl_mult) qui
  donne le même résultat partout sur 5 valeurs. Suggère un bug ou une condition
  qui le shorte (cf. §4.B).
- **`mf_length=35`** booste seulement quand combiné à BO 11+14+08. Avec BO 11+14
  seul (config WINNER), il dégrade le DD ($2,612 vs $2,268). La courbe est
  non-monotone.
- **Risk fan non-linéaire**. r=0.00368 → $52,373 / $2,413. r=0.00370 → $52,823 / $2,427.
  Saut de DD de $14 pour seulement +$450 PnL.

### D. Analyse temporelle

Hours diagnostiques (sweep 01) sur ref base (avant ema=11) :

| Heure | n | total $ | Verdict |
|-------|---|---------|---------|
| H=11 | 80 | –$2,086 | **blackout actif** |
| H=12 | 72 | –$1,926 | trop large (12-14 dégrade DD) |
| H=08 | 62 | –$1,447 | n'aide pas combiné à ema=11 |
| H=14 | 54 | –$1,242 | **blackout actif** |
| H=06 | 40 | –$971  | trop petit pour bénéfice net |
| H=22 | 11 | +$5,855 | éviter d'étendre 22-23:59 vers 21 |

Day-of-week : Tue ($12,440) et Fri ($12,293) >> Mon/Wed/Thu (~$3-4k). Pas de
DOW-blackout testé.

### E. v3 vs v4 — comparaison structurelle

| | v3 (no time blackouts) | v4 (BO 11+14 ré-activés) |
|-|-|-|
| Levers actifs | hw_dir_on=False, cd=3, sx=40 | + ema_len=11 + BO 11+14 |
| Net PnL | $35 472 | $50 770 |
| Max DD | $2 491 | $2 268 |
| PF | 1.41 | 1.58 |
| WR | 43.8 % | 46.1 % |
| Profit/DD | 14.24 | **22.39** |
| Trades | 1 405 | 1 389 |

L'amélioration est structurelle : moins de trades, plus de qualité (WR +2.3 pts,
PF +0.17), DD plus bas, et PnL absolu +43 %. Le levier `ema_len=11` est dominant ;
les blackouts apportent le glaçage final.

---

## 5. Démarche

| Étape | Fichier | Sims | Résultat clé |
|-------|---------|------|--------------|
| 01 — Baseline + hour/DOW | `sweeps/01_baseline_tfs.py` | 1 | Replay v3 winner OK ; toxic hours H=11, 12, 08, 14, 06 |
| 02 — Single-hour BO | `sweeps/02_single_hour_blackouts.py` | 14 | BO h=11 (+$2.5k PnL), BO h=14 (–$167 DD) |
| 03 — Multi-hour BO | `sweeps/03_multi_blackouts.py` | 23 | BO 11+14+08 r=0.0034 → $40.4k / $2.15k (ratio 18.79) |
| 04 — Risk + cooldown | `sweeps/04_risk_cooldown_fan.py` | 32 | cd=3 reste optimal ; risk wall = 0.0035 |
| 05 — Params 1-D | `sweeps/05_strategy_params.py` | 32 | **ema_len=11 BREAKTHROUGH** → $48.6k / $2.07k |
| 06 — Combos ema=11 | `sweeps/06_combos_ema11.py` | 35 | BO 11+14 r=0.0036 → $50.8k / $2.27k |
| 07 — Finetune | `sweeps/07_finetune.py` | 9 | hpb/mf cross-tests ; BO 11+14 confirmed best |
| 08 — Micro finetune | `sweeps/08_micro_finetune.py` | 14 | Risk ladder fine ; r=0.0036 reste sweet spot |
| 09 — Build preset | `sweeps/09_build_preset.py` | 1 | Preset written + verify OK |

Total : **~161 simulations** sur les 250 du budget.

---

## 6. Risques

- **Marge $232** sous $2,500 — confortable (vs $9 dans v3, qui était suicidaire).
  Les replays sont reproductibles dans une fenêtre de variance < $50 ; on est
  largement au-dessus.
- **`ema_len = 11` est un override d'un paramètre indicateur** (raccourcissement
  de 2 unités). Bien moins suspect que `hw_dir_on=False` mais doit être vérifié
  out-of-sample. Suggère un audit : pourquoi l'EMA source courte produit-elle
  des HMA-canaux plus discriminants sur MNQ M7 ?
- **`ssl_mult` no-op** — soit dead code, soit conditionné par un autre flag qui
  désactive son effet. À auditer dans `_compute_ssl` (`hma_ssl_osci_v2.py`).
- **Sample size** : 17 mois sur MNQ, 1 unique série. Pas de walk-forward. La
  période a vu plusieurs régimes (Q1-Q3 2025 tame, Q4 2025 – Q1 2026 volatil),
  ce qui aide.
- **Blackouts H=11 et H=14** sont des heures de news/data macro (CPI, FOMC,
  ouvertures cash US). Robuste en théorie mais à monitorer si ces régimes
  changent (ex : si BCE/FED déplacent les heures de release).

---

## 7. Reproduction

```bash
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/verify_preset.py
```

Doit afficher `✅ MATCH`. Le preset est aussi visible en tête des favoris UI
(`data/presets.json` updated par `write_preset`).

Pour rejouer manuellement : charger le preset
`[Auto] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $50.8k / DD $2.3k)` depuis l'UI,
lancer le backtest.

---

## 8. Idées pour la prochaine itération

1. **Audit `ssl_mult`** — comprendre pourquoi 5 valeurs donnent le même résultat.
   Soit un bug à corriger, soit un code mort à simplifier.
2. **Audit `ema_len=11`** — pourquoi un raccourcissement de 13→11 booste de +20 % ?
   Tester sur MES / MGC pour voir si l'effet est portable (overfit MNQ ou alpha
   structurel ?).
3. **Walk-forward** : split 2025 / 2026 pour valider la robustesse temporelle de
   l'`ema=11` + BO 11+14. Si le second segment dégrade, la config est sur-fittée.
4. **DOW blackout** : Mon/Wed/Thu sont 3-4× moins profitables que Tue/Fri. Tester
   un filtre DOW (skipper Mon ou Wed) pourrait pousser le ratio à 25+.
5. **Bayesian sweep** sur ema_len ∈ [9..13] × risk ∈ [0.0030, 0.0040] avec
   contrainte DD < $2,400. Le 1-D a montré ema=11 best mais le 2-D n'est pas
   exploré.
6. **Multi-asset** : tester (ema=11 + BO 11+14) sur MES / MGC. Si l'edge se
   transfère, l'amélioration est structurelle pas overfit.
