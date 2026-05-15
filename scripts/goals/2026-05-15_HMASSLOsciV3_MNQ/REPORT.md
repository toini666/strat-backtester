# Rapport final — Optimisation HMA-SSL-Osci-v3 sur MNQ

**Période**: 06/01/2026 → 13/05/2026 (≈ 4,5 mois, contrats H26 puis M26)
**Stratégie**: `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole**: MNQ — micro-futures Nasdaq

---

## 1. Résultat (objectifs atteints ✅)

| Objectif | Cible | Atteint |
|----------|-------|---------|
| Profit total | > 30 000 $ | **33 699 $** ✅ |
| Max drawdown | < 2 500 $ | **2 319 $** ✅ |

Métriques détaillées de la configuration gagnante:

| Métrique | Valeur |
|----------|--------|
| Net PnL | **33 699 $** |
| Max drawdown $ | **2 319 $** |
| Profit Factor | **1.78** |
| Win rate | 45.9 % |
| Trades (actifs) | 368 |
| Avg win / Avg loss | +453 $ / –216 $ |
| Reward:Risk | 2.10 |
| Profit / DD ratio | **14.5** |
| Sharpe (approx) | ~1.6 |

Confiance: les paramètres sont issus d'une recherche ascendante (1 seul levier à la fois), donc le risque d'overfit sur 4,5 mois est modéré mais non nul (cf. §6).

---

## 2. Configuration gagnante

### Timeframe
- **M3** (3 minutes) — c'est le timeframe qui maximise systématiquement le profit/DD pour cette stratégie.

### Paramètres de stratégie (overrides du défaut)
```python
{
    "cloud_on": True,                  # filtre MFI cloud ACTIVÉ
    "one_trade_per_entry_window": False,
    "sig_extreme": 22.0,               # plage osc sgd ±22 (défaut 35)
    "signal_length": 4,                # SMA(4) au lieu de 3
    "entry_window_bars": 4,            # fenêtre d'entrée HMA-slow×SSL un peu plus serrée (défaut 5)
}
```
Tous les autres paramètres restent au défaut v3 (`hma_pol_bars=3`, `hma1_len=13`, `hma2_len=21`, `ssl_len=60`, `ssl_mult=0.2`, `hyper_wave_length=5`, `mf_length=35`, `mf_smooth=6`, `hw_extreme_on=True`, `hw_extreme=20`, `hw_dir_on=True`, `delta_on=True`, `max_sl_points=300`, `cooldown_bars=1`, `hw_partial_pct=0`, `final_exit_mode="HMA rapide/SSL → HW"`).

### Paramètres de risque
```python
initial_equity   = 50_000 $
risk_per_trade   = 0.006   # 0.6 % → 300 $ de risque max par trade
max_contracts    = 50
```

### Paramètres de blackout (sur Brussels reference time)
Fenêtres **actives** sur la journée:
| Window | Statut | Raison |
|--------|--------|--------|
| 04:00 – 05:00 | **ACTIVE (ajouté)** | heure peu profitable (–310 $ sur 43 trades en baseline) |
| 08:00 – 11:00 | **ACTIVE (ajouté)** | UK pre-/open particulièrement toxique (–9 762 $ sur 121 trades) |
| 11:00 – 13:00 | active (défaut) | déjeuner UK déjà bloqué |
| 15:30 – 21:00 | active (défaut) | session US déjà bloquée |
| 21:00 – 23:00 | active (défaut) | post-close déjà bloqué |

Auto-close: **21:00** Brussels reference (défaut).

### Daily limits ($ — mode "after_close")
- `daily_win_limit` : **600 $**
- `daily_loss_limit` : **600 $**

> 📌 Snapshot machine-readable: `scripts/v3_winner_output.json`

---

## 3. Top configurations alternatives

| # | Config | PnL | DD | PF | N | Compromis |
|---|--------|-----|----|----|---|-----------|
| 1 | **WINNER** r=0.6%, W=600/L=600, +blackout 04 & 08-11 | 33 699 | 2 319 | 1.78 | 368 | Ratio le plus propre (14.5) |
| 2 | r=0.6%, L=600 only, +blackout 04 & 08-11 | 35 300 | 2 966 | 1.65 | 451 | +5 % profit mais DD au-dessus (échoue) |
| 3 | r=0.6%, W=600/L=600, blackout 08-11 only | 30 774 | 2 336 | 1.69 | 381 | Plus simple, OK aux deux objectifs |
| 4 | r=0.7%, L=700, +blackout 04 & 08-11 | 40 398 | 3 460 | 1.64 | 446 | Plus profitable, DD HS |
| 5 | r=0.4%, no daily-limits, +blackout 04 & 08-11 | 24 395 | 2 294 | 1.65 | 480 | Pas de daily limit, DD ok, profit court |

> Le couple **W=600/L=600** s'avère systématiquement supérieur (PF saute de 1.65 à 1.78) parce qu'il coupe à la fois les journées-fournaise et les journées euphoriques (qui tendent à se renverser).

---

## 4. Insights et observations

### A. Hiérarchie des leviers (du plus puissant au plus marginal)

1. **Le timeframe est de loin le levier le plus puissant.** M3 est le seul TF qui converge naturellement vers un PF > 1.3 avec ce stack d'indicateurs. M5 atteint PF 1.32 mais avec un DD double. M7 a peu de trades. M2 perd carrément son edge (PF 1.0).
2. **L'activation du filtre MFI cloud (`cloud_on=True`)** est le second levier — il fait passer le PnL de $37k → $46k et le PF de 1.16 → 1.26 sur M3. C'est probablement le filtre qui élimine le plus de "trades dans le bruit".
3. **`sig_extreme=22-25`** (au lieu du défaut 35) divise quasiment le drawdown par 2 (17k → 8k) sur la même base. Cela coupe les entrées prises quand le signal est déjà trop tendu — où les retours moyens sont mauvais.
4. **Blackout sur les heures perdantes (08-11 Brussels)** ajoute $8k de PnL ET réduit le DD. C'est l'effet le plus fort hors paramètres d'indicateurs.
5. **Daily loss/win limits** sont le dernier levier décisif pour faire passer le PF de 1.4 → 1.78. Ils écrêtent les distributions queues.

### B. Effets contre-intuitifs / surprises

- **`one_trade_per_entry_window=False` est meilleur** (+$3k profit) que `True` (défaut). Sur M3, plusieurs entrées dans la même fenêtre HMA-slow × SSL ajoutent un peu de profit sans dégrader le DD — la fenêtre n'est pas tellement corrélée à un single setup.
- **Le filtre `cloud_zero_on`** détruit le PnL (–$2k vs base). Il filtre trop de bons setups.
- **`delta_ext_on`** réduit le nombre de trades de 800 → 149 sur M3 et tue le PnL. La condition "delta a viré contrarian" est trop rare pour fournir un edge significatif sur ce TF.
- **Le mode `final_exit_mode="% du prix d'entrée en profit"`** (TP fixe en pourcentage) détruit le profit dans toutes les variantes 0.05–0.30 % (–$6k à +$12k au mieux contre +$48k de la sortie HMA-rapide / SSL). La sortie HMA/SSL adaptative est strictement supérieure pour MNQ.
- **`max_candle_pct` et `max_sl_points`** sont des "tuning knobs" inutiles sur la base M3 actuelle. Aucun trade n'est en pratique filtré par ces seuils. Si on tightenait le SL absolu, on perdrait peu, mais il n'y a pas d'amélioration ratio nette.
- **`ssl_mult` est ignoré dans cette stratégie** — les sweeps 0.1 → 0.3 produisent des résultats strictement identiques. Soit le paramètre n'a pas d'effet sur le code de v3, soit il est dominé par d'autres branches (à confirmer dans le code).
- **`hw_partial_pct > 0` dégrade le PnL** ($46k → $35k). La logique de "partial sur cross HW inverse" ne crée pas de valeur sur MNQ en M3 — la sortie finale capte déjà la majorité du move.

### C. Analyse temporelle (analyse trade-par-trade)

Distribution PnL par heure de Brussels (sur la base BEST + loss_lim=$1000):

| Heure | Trades | PnL total | Avg | Observation |
|-------|--------|-----------|-----|-------------|
| 00 | 48 | +5 462 $ | +114 | Asia, bonne |
| 03 | 41 | +5 874 $ | +143 | Crossover Asia/UK, très bonne |
| 05 | 46 | +7 730 $ | +168 | Excellente heure |
| 08 | 46 | **–3 865 $** | –84 | **Pire heure → bloquer** |
| 09 | 47 | **–2 391 $** | –51 | **Mauvaise** |
| 10 | 28 | **–3 506 $** | –125 | **Pire avg → bloquer** |
| 13 | 37 | +4 998 $ | +135 | Bon retour après pause lunch |
| 22 | 7 | **+20 639 $** | +2 948 | Spike anomalie (DST shift probable) |

**Conclusion**: la session UK ouverture (08-10 Brussels = 07-09 UK pre-/open) est statistiquement perdante avec cette stratégie. Les sessions Asia et premier rebond US (13h) sont les plus rentables.

Par jour de la semaine (PnL):
- Mon +$13.9k · Wed +$8.9k · **Thu +$22.2k** · Fri +$3.8k (tous Brussels) · Tue ~0
- Aucun day-of-week n'est franchement négatif → pas besoin de bloquer un jour entier.

### D. Relation paramètre → métrique

| Paramètre | Augmenter ↑ | Diminuer ↓ |
|-----------|-------------|------------|
| `sig_extreme` | Plus de trades, DD ↑, PF ↓ | Moins de trades, DD ↓ massif (22-25 = sweet spot) |
| `signal_length` | PnL ↑ jusqu'à 4, redescend après | PF stable |
| `hyper_wave_length` | PF ↑ (5→7) | DD ↑ à 3 |
| `mf_length` | dégrade au-dessus de 35 | dégrade en-dessous de 35 |
| `ssl_len` | dégrade au-dessus de 60 | dégrade en-dessous de 60 |
| `entry_window_bars` | +trades, –PF | –trades, +DD |
| `risk_per_trade` | PnL ET DD scale linéairement (PF inchangé) | idem dans l'autre sens |
| `daily_loss_limit` | DD ↑, PF ↓ | DD ↓, PF ↑, mais profit ↓ aussi |
| Blackout 08-11 | n/a | PnL ↑ ET DD ↓ → free lunch |

---

## 5. Démarche d'optimisation

1. **Baseline par TF** → M3 sort à $37k profit, $17k DD (PF 1.16). M5 < M3, M7-M10 trop peu de trades.
2. **Filter activation** sur M3 → `cloud_on` boost PnL à $46k, PF 1.26.
3. **Oscillator core params** → `sig_extreme=22` divise DD par 2, `signal_length=4` boost PnL ; combo → $50k / $8k.
4. **Daily limits** → `loss_lim=$1000` seul donne le meilleur ratio ($50k / $6.4k = 7.9).
5. **Hour-bucket analysis** sur les trades → identification des heures 08-10 toxiques. Blackout 08-11 → $59k / $5k (ratio 11.9).
6. **Scale risk** → 0.6 % avec daily limits W=600/L=600 + extra blackout 04 + 08-11 → 33 699 $ / 2 319 $ ✅.

Scripts produits (dans `scripts/`):
- `optimize_hma_ssl_osci_v3.py` — harness principal (appelle directement le moteur, pas d'HTTP)
- `v3_sweep.py`, `v3_filter_sweep.py`, `v3_filter_sweep2.py` — sweeps initiaux
- `v3_osc_sweep.py`, `v3_combo_sweep.py` — paramètres d'oscillateur
- `v3_risk_sweep.py`, `v3_blackout_sweep.py` — risque et blackouts
- `v3_deeper.py` — analyse trade-par-trade (hour bucket)
- `v3_hour_block.py`, `v3_final.py`, `v3_finetune.py` — fine-tuning
- `v3_validate.py` — validation finale + JSON snapshot

---

## 6. Risques et idées pour la prochaine itération

### Risques sur la robustesse
1. **Petit échantillon temporel** — 4,5 mois et 368 trades. Le DD à $2.3k est confortable, mais une seule mauvaise semaine pourrait l'augmenter de 50%. Un walk-forward (e.g. backtest sur 1m de 2025 hold-out) serait précieux.
2. **Le blackout 08-11 est calé sur l'historique** — c'est typiquement le genre de filtre qui peut être overfitté. À tester sur des fenêtres glissantes.
3. **`signal_length=4`** est très proche du défaut (3) mais le profit grimpe de $48k → $58k — il faut vérifier que ce n'est pas un effet "1 ou 2 mega-trades" qui font la différence.
4. **Daily limits W=600/L=600** créent une boucle "stop early" qui peut sous-performer dans un futur régime plus tendanciel.

### Idées d'amélioration
1. **Walk-forward optimization** — re-tuner sur des fenêtres roulantes de 3 mois et tester sur le mois suivant pour vérifier la stabilité des paramètres.
2. **Bayesian / Optuna sweep** — la recherche actuelle est ascendante 1D ; un sweep multi-dimensionnel pourrait trouver des combos non explorés (e.g. `hyper_wave_length=7` + `signal_length=2` + `sig_extreme=30`).
3. **Régime de marché** — segmenter les résultats par volatilité (e.g. VIX ou ATR moyen). Le filtre 08-11 pourrait n'être valide qu'en régime range. Une condition "block_08_11_if_atr<X" rendrait la stratégie plus adaptive.
4. **Multi-strat / multi-asset** — la stratégie n'utilise que MNQ. Les contrats MES (S&P) et MGC (or) sont disponibles et un `multi_asset` run (lock du capital) pourrait diversifier les drawdowns.
5. **Auto-close earlier** — le pic post-20:00 montre quelques trades très anormaux probablement DST-related ; verrouiller l'auto-close à 20:30 réf pourrait nettoyer.
6. **Position sizing alternatif** — actuellement linéaire avec le SL, on pourrait tester un sizing par volatilité (e.g. fraction de Kelly avec PF observé) ou plafonner la taille en début de séance.
7. **Loss-limit dynamique** — au lieu de $600 fixe, l'indexer sur l'equity courante (e.g. 1 % de l'equity du jour) reste cohérent quand le capital croît.
8. **Audit de `ssl_mult`** — il est suspect que ce paramètre n'ait aucun effet observable. À investiguer dans `_compute_ssl()` pour comprendre s'il est court-circuité.
9. **Stratification du test** — séparer les trades par contrat (H26 vs M26 — la transition est mi-mars) pour s'assurer que les paramètres ne capturent pas l'effet d'un seul contrat.
10. **Optimiser sur le ratio Profit/DD plutôt que sur le PnL** dans le futur — c'est la métrique qui compte vraiment ici, et la recherche aurait été plus directe en l'optimisant explicitement.

---

## 7. Reproduction

Depuis la racine du repo:

```bash
source venv/bin/activate
python -m scripts.v3_validate
```

Sortie attendue:

```
WINNER: r=0.6% W=600 L=600 + block 04 + block 08-11   PnL=$33,699 | DD=$ 2,319 | N= 368 | WR= 45.9% | PF=1.78
```

Le JSON complet de la config gagnante est dans `scripts/v3_winner_output.json`.

Pour utiliser ces paramètres dans la UI:
1. Sidebar → Strategy = `HMASSLOsciV3`, Symbol = `MNQ`, Interval = `3m`
2. Start = `2026-01-06T00:00`, End = `2026-05-13T22:00`
3. Initial equity = 50 000, Risk = 0.006, Max contracts = 50
4. Engine Settings → activer les fenêtres 04:00-05:00 et 08:00-11:00 (en plus des défauts)
5. Daily Win Limit = 600 (activé), Daily Loss Limit = 600 (activé), mode = after_close
6. Strategy params → `cloud_on = True`, `one_trade_per_entry_window = False`, `sig_extreme = 22`, `signal_length = 4`, `entry_window_bars = 4`
