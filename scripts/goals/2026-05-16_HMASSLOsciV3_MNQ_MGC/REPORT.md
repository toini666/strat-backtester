# Rapport final — HMASSLOsciV3 multi-asset MNQ + MGC

**Période** : 2025-01-06 → 2026-05-15 (~17 mois)
**Stratégie** : `HMASSLOsciV3` sur **MNQ** et **MGC** simultanément (mode `multi_asset`)
**TF** : 7 minutes (les 2 legs)
**Initial equity** : $50 000 (compte partagé)
**Max contracts** : 50 par leg
**Auto-close** : 22:00 reference Brussels (CME close — FIXE, jamais touché)
**Point de départ** : preset `HMA-SSL-V3 - MNQ/MGC - Best` (combinaison du winner v4 MNQ et v2 MGC)
**Budget** : 250 simulations — **~236 utilisées**

---

## 1. Résultat — **✅ les deux objectifs atteints**

| Objectif | Cible | Atteint | Statut |
|----------|-------|---------|--------|
| Profit net | > **$100 000** | **$101 921** | ✅ +$1 921 (margin +1.9 %) |
| Max drawdown $ | < **$2 500** | **$2 363** | ✅ −$137 |

| Métrique | Valeur |
|----------|--------|
| Net PnL | **$101 921** |
| Max drawdown $ (combiné) | **$2 363** |
| Max drawdown % (combiné) | **3.087 %** |
| Profit factor | **1.615** |
| Win rate | 51.66 % |
| Trades actifs | 2 319 |
| MNQ trades / PnL | 1 177 / **$52 263** |
| MGC trades / PnL | 1 142 / **$49 658** |
| **Profit / DD ratio** | **43.14** |
| Total return | 203.84 % |

### Vs baseline (preset `HMA-SSL-V3 - MNQ/MGC - Best` au moment du départ)

| | Baseline | **Winner** | Δ |
|-|----------|------------|---|
| PnL | $95 481 | **$101 921** | **+$6 440 (+6.7 %)** |
| Max DD $ | **$3 045** ❌ | **$2 363** ✅ | **−$682 (−22.4 %)** |
| Profit factor | 1.567 | 1.615 | +0.048 |
| Win rate | 50.5 % | 51.7 % | +1.1 pp |
| Trades | 2 531 | 2 319 | −212 (−8.4 %) |
| P/DD ratio | 31.35 | **43.14** | **+11.79 (+37.6 %)** |

La baseline **ne respectait PAS la contrainte DD**. Le winner non seulement passe le seuil PnL, mais réduit le DD de **$682**.

---

## 2. Configuration retenue (`winner_preset.json`)

> Le preset est en mode `multi_asset` et apparaît en tête de `data/presets.json` sous le nom
> `[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset — WINNER (PnL $101.9k / DD $2.4k)`.

### Risque par leg

| Leg | risk_per_trade | Notes |
|-----|----------------|-------|
| MNQ | **0.3744 %** (= 0.36 % × 1.04) | +4 % vs baseline preset |
| MGC | **0.5405 %** (= 0.47 % × 1.15) | +15 % vs baseline preset |
| max_contracts | 50 | par leg |
| initial_equity | $50 000 | compte partagé |

### Paramètres de stratégie

Identiques au baseline preset (= winners v4 MNQ et v2 MGC, déjà optimisés en monoasset). Aucun paramètre indicateur n'a été modifié dans cette campagne.

#### MNQ leg (extraits clés ; preset contient les 32 keys)
```python
{"ema_len": 11, "hma1_len": 13, "hma2_len": 21, "amp_mult": 2.0,
 "hma_pol_bars": 0, "entry_window_bars": 3,
 "ssl_len": 80, "ssl_mult": 0.2,
 "hyper_wave_length": 7, "signal_length": 4,
 "mf_length": 25, "mf_smooth": 6,
 "hw_dir_on": False, "hw_extreme_on": True, "hw_extreme": 20.0,
 "sig_extreme_on": True, "sig_extreme": 40,
 "cloud_on": True, "delta_on": True,
 "tick_buffer": 0, "max_sl_points": 300.0, "cooldown_bars": 3,
 "final_exit_mode": "HMA rapide/SSL → HW", "final_exit_pct": 0.1,
 "one_trade_per_entry_window": True}
```

#### MGC leg (extraits clés)
```python
{"ema_len": 13, "hma1_len": 9, "hma2_len": 34, "amp_mult": 2.0,
 "hma_pol_bars": 3, "entry_window_bars": 5,
 "ssl_len": 60, "ssl_mult": 0.2,
 "hyper_wave_length": 5, "signal_length": 3,
 "mf_length": 35, "mf_smooth": 6,
 "hw_dir_on": True, "hw_extreme_on": True, "hw_extreme": 20.0,
 "sig_extreme_on": True, "sig_extreme": 35,
 "hw_range_on": True, "hw_range": 10,
 "cloud_on": False, "delta_on": True,
 "tick_buffer": 1, "max_sl_points": 100.0, "cooldown_bars": 1,
 "block_loss_exit_before_partial": True,
 "final_exit_mode": "HMA rapide/SSL → HW"}
```

### Blackouts (reference Brussels time)

#### MNQ leg — 3 blackouts AJOUTÉS vs baseline

| Fenêtre | Statut | Source |
|---------|--------|--------|
| 00:00 – 00:05 | inactive | UI default |
| 09:00 – 09:05 | inactive | UI default |
| 12:00 – 14:00 | inactive | UI default |
| 15:30 – 15:35 | inactive | UI default |
| 16:30 – 22:00 | inactive | UI default |
| **22:00 – 23:59** | **active** | UI default (post-CME-close) |
| **11:00 – 12:00** | **active** | baseline MNQ |
| **14:00 – 15:00** | **active** | baseline MNQ |
| **08:00 – 09:00** | **active** | **NOUVEAU campagne** ← gros DD-reducer |
| **12:00 – 13:00** | **active** | **NOUVEAU campagne** ← PF-booster |
| **13:00 – 14:00** | **active** | **NOUVEAU campagne** ← DD-reducer |

#### MGC leg — INCHANGÉ vs baseline

| Fenêtre | Statut |
|---------|--------|
| 22:00 – 23:59 | active |
| 11:00 – 12:00 | active |
| 03:00 – 04:00 | active |
| 06:00 – 07:00 | active |
| 07:00 – 08:00 | active |
| 09:00 – 10:00 | active |
| (autres UI defaults) | inactive |

### Daily limits

**Désactivées**. Testées loss-only ($400/$500/$700/$900/$1200/$1500), win-only et combos (sweep 05). Aucune combinaison n'a battu le baseline `no DL` — la fenêtre DD critique est **multi-jours** (Oct 20 → Nov 3, 11 jours) et non un blowup single-day, donc les limites quotidiennes coupent les bons jours sans contrer la dérive.

### Auto-close
**22:00:00** reference Brussels. Conformément aux invariants du dépôt.

---

## 3. Top alternatives (toutes valides, du plus PnL au plus de marge)

| # | Config | Risk MNQ / MGC | PnL | DD | Margin | P/DD |
|---|--------|----------------|-----|----|----|------|
| **0** | **3BO m=1.04 / g=1.15** | 0.3744 % / 0.5405 % | **$101 921** | **$2 363** | **+$137** | **43.14** ← **WINNER** |
| 1 | 3BO m=1.04 / g=1.17 | 0.3744 % / 0.5499 % | $101 770 | $2 498 | +$2 | 40.74 |
| 2 | 3BO m=1.04 / g=1.14 | 0.3744 % / 0.5358 % | $100 670 | $2 360 | +$140 | 42.66 |
| 3 | 3BO m=1.03 / g=1.15 | 0.3708 % / 0.5405 % | $100 666 | $2 363 | +$137 | 42.60 |
| 4 | 3BO m=1.04 / g=1.13 | 0.3744 % / 0.5311 % | $100 418 | $2 360 | +$140 | 42.56 |
| 5 | 3BO m=1.04 / g=1.10 | 0.3744 % / 0.5170 % | $100 388 | $2 395 | +$105 | 41.91 |

Le WINNER **maximise le PnL absolu** avec marge confortable. ALT1 a 2 $ de marge — trop fragile. ALT2/4 préfèrent une marge légèrement supérieure ($140) au prix de ~$1.5k de PnL. ALT5 est l'option la plus "safe" parmi les valides à $100k+.

### Closest failures (documentation)

| Config | PnL | DD | Reason |
|--------|-----|----|--------|
| 3BO m=1.05 / g=1.10 | $100 816 | **$2 570** ❌ | DD over by $70 |
| 3BO m=1.05 / g=1.15 | $102 349 | **$2 534** ❌ | DD over by $34 |
| 3BO m=1.06 / g=1.10 | $100 992 | **$2 594** ❌ | DD over by $94 |
| 3BO m=1.04 / g=1.20 | $102 588 | **$2 782** ❌ | DD over by $282 |

Pousser MNQ au-delà de m=1.04 (= risk 0.374 %) franchit un mur de DD à $2,539-$2,594.

---

## 4. Insights de la recherche

### A. Hiérarchie des leviers (de la plus haute à la plus marginale)

1. **3 nouveaux blackouts MNQ (h08-09, h12-13, h13-14)** — Le levier principal.
   - h08 (single) : −$467 DD au baseline, PnL +0
   - h08 + h13 (double) : DD $2,329, ratio P/DD = 39.93 (vs 31.35)
   - h08 + h12 + h13 (triple) : DD $2,319, ratio P/DD = 40.88, **+3 pp sur WR**
   - Avec risk scaling, ratio monte à 43.14.
2. **MGC risk-up (+15 %)** — Le PnL-booster.
   - g=1.15 ajoute $4 947 PnL sur MGC sans pousser le DD combiné (effet floor entier sur les contrats).
   - Le g=1.15 est un sweet spot de rounding : DD identique à g=1.13 et g=1.14 ($2 360-$2 363) mais PnL plus élevé.
3. **MNQ risk-up (+4 %)** — Le PnL-booster mineur.
   - m=1.04 : sweet spot avant le saut de DD à $2 539. Au-delà la fonction DD(risk) n'est plus monotone.
4. **Non-leviers** : daily limits (cf. §C), MGC blackouts supplémentaires (cf. §B), strategy params (laissés inchangés).

### B. Effet contre-intuitif : MGC blackouts inutiles

Les blackouts MGC déjà actifs (11, 6, 7, 3, 9 — hérités du winner MGC v2) suffisent. Les hours suspectes restantes (H=17 -$1.1k, H=23 -$557, H=21 -$336) **n'aident pas en multi-asset** : ajouter h17-18 réduit MGC PnL de $1.6k pour seulement $29 de DD gagné. Ce sont les MNQ blackouts qui pilotent la réduction du DD combiné, parce que c'est MNQ qui contribue le plus au DD combiné dans la fenêtre critique d'Oct/Nov 2025 (-$1,570 MNQ vs -$1,475 MGC sur 11 jours).

### C. Daily limits inopérants (multi-asset)

Sweep 05 a testé 16 combos. Tous DD figés à $3 045 (= baseline) ou pire, PnL en baisse :
- loss=-700 → PnL $93,393 / DD $3,045 (DD figé car les limites kick in EN AVAL du gros DD)
- win=+500 → PnL $85,881 / DD $3,045 (perte du upside)
- combo +500/-700 → PnL $83,641 / DD $3,045

Cause : la fenêtre DD critique (11 jours du 2025-10-20 au 2025-11-03) accumule **65 trades** avec moyenne −$47/trade. Aucune journée individuelle ne déclenche un limit cap parce qu'aucune n'a un blowup. Daily limits inopérants quand le DD est multi-jours et "lisse".

### D. Analyse temporelle — pourquoi h08+h12+h13 marche

Bucketing hourly du baseline (avant blackouts campaign) :

| H | MNQ trades | MNQ PnL | MGC trades | MGC PnL | Verdict |
|---|------------|---------|------------|---------|---------|
| 8 | 69 | **−$1,680** (avg −24) | 52 | +$456 | **BO MNQ** |
| 12 | 81 | **−$1,654** (avg −20) | 62 | +$5,383 | **BO MNQ uniquement** |
| 13 | 50 | +$1,855 | 70 | +$2,732 | h13 PnL net positif mais **DD-reducer** (cf. §E) |

**Effet h13 paradoxal** : moyenne par trade positive (+$37) mais le timing des trades h13 chevauche les drawdowns. Blackout les retire → DD baisse de $295 alors que PnL ne baisse que de $1,418. Trade-off DD-favorable.

### E. Sweet spots de rounding sur le contract floor

Le simulateur arrondit le nombre de contrats avec `max(1, int(raw))`. Conséquence :

| MGC scale (g=…) | DD combiné | PnL combiné |
|----|------|------|
| 1.07 | $2,290 | $94,929 |
| 1.08 | $2,353 | $96,663 |
| 1.09 | $2,287 | $97,615 (DD repli) |
| 1.10 | $2,322 | $98,225 |
| 1.11 | $2,333 | $99,223 |
| 1.13 | $2,297 | $99,162 (DD repli) |
| 1.14 | $2,297 | $99,415 |
| **1.15** | **$2,363** | **$100,666** (winner zone) |
| 1.17 | $2,435 | $100,515 |

La fonction DD(risk) **n'est pas monotone**. g=1.15 est un sweet spot : DD reste comparable à g=1.13/1.14 mais PnL grimpe parce que le contract floor laisse passer +1 contrat sur les trades à risque moyen. Robustesse à valider en walk-forward.

### F. La baseline `HMA-SSL-V3 - MNQ/MGC - Best` ne respectait PAS le DD seuil

| | MNQ seul | MGC seul | Combiné |
|-|----------|----------|---------|
| Per-leg DD (issus des campagnes mono-asset) | $2,268 | $2,378 | — |
| **Combiné DD (replay multi)** | — | — | **$3,045** ❌ |

Les drawdowns des deux legs **se chevauchent temporellement** dans la fenêtre 2025-10-20 → 2025-11-03 (les deux legs perdent simultanément). Ce qui fait que :
**`max(DD_MNQ, DD_MGC) ≪ DD_combiné`**.
La somme des DD per-leg ($4,646) borne par le haut le DD combiné, mais cette borne est trop large.

---

## 5. Démarche (10 sweeps)

| Étape | Fichier | Sims | Insight clé |
|-------|---------|------|-------------|
| 01 — Baseline | `sweeps/01_baseline.py` | 1 | Baseline DD = $3,045 ❌ (preset original ne passe pas DD<2500) |
| 02 — Risk split | `sweeps/02_risk_split.py` | 26 | Pur scaling cap PnL à $81k (ratio 33). Insuffisant pour $100k. |
| 03 — DD analysis | `sweeps/03_dd_analysis.py` | 1 | Fenêtre DD = 11 jours, 65 trades, ~50/50 MNQ/MGC. Hour buckets identifiés. |
| 04 — BO singles | `sweeps/04_blackout_singles.py` | 12 | **MNQ h08-09 = -$467 DD breakthrough**. Autres marginaux. |
| 05 — Daily limits | `sweeps/05_daily_limits.py` | 16 | Toutes combos dégradent. DL inopérantes sur DD multi-jours. |
| 06 — BO combos | `sweeps/06_combo_blackouts.py` | 26 | **MNQ h08+h12+h13 = P/DD 42** breakthrough. MGC h17 inutile. |
| 07 — Finetune h08+h13 | `sweeps/07_finetune_h08_h13.py` | 41 | Triple BO confirmé. Premier $100k+ valide avec g=1.10. |
| 08 — Finetune triple | `sweeps/08_finetune_triple_bo.py` | 66 | Sweet spot m=1.04/g=1.10-1.12. PnL $100k+ at DD $2.4k. |
| 09 — Micro finetune | `sweeps/09_micro_finetune.py` | 41 | **g=1.15 rounding sweet spot** → $101.9k @ $2.36k DD ✅✅ |
| 10 — Final validation | `sweeps/10_final_validation.py` | 6 | Winner + 5 alts confirmés. Replay déterministe (à 1 cent près). |

**Total : ~236 / 250 simulations.**

---

## 6. Risques & idées pour la prochaine itération

### Risques d'overfit

- **Marge DD = $137** sur 2 ans : confortable mais pas immense. ALT2/4 à $140 sont presque équivalents si le winner dérive.
- **`g=1.15` est un sweet spot de rounding** (contract floor) — un déplacement de quelques bps sur le risk peut faire perdre 1 contrat ailleurs et changer le DD de $50+. À monitorer sur de nouveaux mois de data.
- **Fenêtre DD critique unique** (2025-10-20 → 2025-11-03). Si cette période était un freak event, la marge $137 est plus que suffisante. Si c'était structurel, elle est juste-juste.
- **Triple BO MNQ** est un ajout de 3 heures consécutives (h08, h12, h13) sur lesquelles MNQ trade beaucoup (200+ trades sur 17 mois). Risque de capturer un bruit spécifique aux contrats H25/M25/M26. **Test de robustesse out-of-sample recommandé**.

### Note importante sur la métrique DD

**Le UI affiche `max_drawdown` en % (3.09 % ici)**, pas en $. La contrainte $2,500 est mesurée localement par notre runner (`_combined_dd_dollars`). Pour la valider dans l'UI : 3.09 % × $50 000 ≈ $1,545 si calculé sur initial equity, mais en réalité $2,363 dollar-DD car le drawdown a lieu après un peak intermédiaire élevé ($26k+ profit). **Ne PAS confondre `max_drawdown %` et dollar DD** dans l'UI.

### Idées concrètes

1. **Walk-forward** — splitter 2025-01-06 → 2026-05-15 en 4-5 fenêtres et re-fit les params (blackouts + risk) par segment. Mesurer si la fenêtre DD du Q4 2025 réapparaît stable.
2. **Cross-asset DD shaping** — quand l'un des legs perd, est-ce que l'autre est sytématiquement en position ? Si oui, ajouter un blackout DOW-conditionnel (le moteur ne le permet pas actuellement — feature request).
3. **Bayesian sweep sur (risk_m, risk_g, BO_count)** — la non-monotonicité du contract floor suggère qu'un grid 1-D laisse des poches inexplorées.
4. **Audit `ssl_mult` toujours inactif** (déjà flagué dans v3 MNQ et v2 MGC) — soit dead code, soit conditionné par un flag absent.
5. **Daily limits asymétriques par leg** — actuellement la combine est compte-partagé. Si chaque leg avait son propre cap, on pourrait borner la fenêtre DD critique sans tuer les bons jours individuels.
6. **Tester un 3ᵉ leg** (MES ou MCL) — corrélation faible avec MNQ/MGC potentiellement utile pour diluer encore le DD.

---

## 7. Reproduction

```bash
# Vérification déterministe (doit afficher ✅ MATCH)
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/verify_preset.py

# Reconstruire le preset depuis zéro
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/build_winner.py

# Visualiser dans l'UI
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001
# (autre terminal)
cd frontend && npm run dev -- --port 3001 --host
# → http://localhost:3001 → Favorites → preset
#   "[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset — WINNER (PnL $101.9k / DD $2.4k)"
```
