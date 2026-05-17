# Phase 1 — Observations brutes (MNQ_v5 + MGC_v3)

Données : `outputs/trades_ALL.csv` (2,106 trades = 1,241 MNQ_v5 + 865 MGC_v3),
enrichies avec MAE/MFE en R (calculés sur les 1m bars entre entry et exit
execution), `bars_in_trade`, `bars_since_setup`, `hour` (reference Brussels),
`candle_pct`, `two_bar_body_pct`, `risk_dist_points`, `last_hw_value`,
`canal_width`, `shadow_hw_bars` (distance vers le prochain adverse-HW cross).

## Statut global

| Statut | MNQ_v5 n | MNQ_v5 PnL | MGC_v3 n | MGC_v3 PnL |
|--------|---------:|-----------:|---------:|-----------:|
| Canal Exit | 762 | **+$141,206** | 527 | **+$91,708** |
| Stop Loss | 379 | −$80,718 | 243 | −$56,510 |
| Auto-Close (profit) | 66 | +$10,456 | 54 | +$12,375 |
| Auto-Close (loss) | 33 | −$2,178 | 41 | −$2,882 |

Les **Stop Loss représentent 30 % des trades et 100 % des pertes nettes**
(les Canal Exit incluent ~80 % de gagnants).

---

## A. Conditions d'entrée

### A.1 — issues des Winners (amplification)

- **obs-A1a** : sur **MGC**, les entrées tardives dans la fenêtre (bars 3+
  après le slow-cross) ont WR 65 % (n=40 à bar 3) à 68 % (n=28 à bar 4)
  vs 54 % aux bars 0/1 (n=722). Sur **MNQ** (entry_window=3) le pic WR est
  à bar 3 (55 %, n=164) vs 48 % à bar 0 (n=552). Pattern : **se précipiter
  sur le slow-cross dilue l'edge ; attendre 1–3 bars sélectionne les
  setups confirmés**.
  → **H-A1** : `lab_entry_min_bars=1..3`.

### A.2 — issues des Losers (exclusion)

- **obs-A2a** : Les trades avec **distance SL très petite (< 23 pts MNQ)**
  ont WR 36 % (n=252) — pire WR observé — mais total PnL +$35,854 grâce à
  la taille de position (l'effet de levier compense le WR). C'est
  **ambigu** : conserver pour le PnL ou couper pour la stabilité ? À tester.
  → **H-A3** : `lab_min_sl_points` ∈ {5, 10, 15, 20}.

- **obs-A2b** : **MNQ — H=6 toxique** (n=52, PnL −$2,112, WR 30.8 %, SL rate
  53.8 %). H=12 résiduelle après V5-BO (n=18, −$509). **MGC — H=22**
  toxique (n=9, −$891, 33 % WR, 66.7 % SL rate). H=20 et H=17 marginales
  (PnL ~0, fortes SL rates).
  → **H-A4** : `lab_entry_blocked_hours` — bloquer H=6 sur MNQ ; H=22 sur
  MGC.

### A.2 — Pattern observé contre-intuitif (insight, pas H)

- Les **candles agressives à l'entrée** (top quintile candle_pct) ont
  **WR 57 % MNQ / 65 % MGC** vs ~45 % pour les petits candles → le
  filtre `max_candle_pct=0.9` actuel laisse les bons trades passer ;
  serrer ce filtre serait **contre-productif**.

---

## B. Évitement des SL

### B.1 — issues des Losers

- **obs-B1a** : Les Stop Loss surviennent rapidement — **39 % des SL MNQ
  arrivent en ≤ 3 bars** ($-31k = 39 % de la SL-loss totale) ; **52 % en
  ≤ 5 bars** ($-42k). Pattern : un trade qui n'a pas avancé en 3-5 bars
  est statistiquement déjà perdu.
- **obs-B1b** : Indicateur signal — `shadow_hw_bars` (distance vers
  prochain HW adverse depuis entry) — SL trades : médiane 2.0 bars
  (MNQ/MGC) ; Canal Exit : médiane 4.0/3.0. Le HW retourne défavorable
  très tôt sur les SL trades.
- **obs-B1c** : Les Stop Loss ont **MAE moyen 1.38R (MNQ) / 1.26R (MGC)**
  vs 0.37/0.38R pour les Canal Exit (par construction ils touchent ~1R
  côté loss, mais le ratio MFE/MAE est dévastateur : MFE moyen SL 0.61R
  MNQ / 0.49R MGC — la moitié n'a jamais dépassé 0.3R).
  → **H-B2** : `lab_no_hw_flip_kill_bars` ∈ {3, 4, 5, 6} — armer un
  fast-HMA exit si **aucun HW favorable** dans les N bars qui suivent
  l'entrée potentielle (mécanisme `fast_hma_exit_long/short` consommé
  par `v3_fast_hma_ssl`).

- **obs-B1d** : 2-bar body cumulé non-discriminant en moyenne (le top
  quintile a même un meilleur PnL), mais pour les SL pris en <3 bars,
  la valeur médiane 2-bar body peut être plus élevée (à vérifier dans
  le sweep — sinon REJECT).
  → **H-B1** : `lab_max_2bar_body_pct` ∈ {0.5, 0.7, 1.0, 1.5}. Hypothèse
  faible a priori — testée pour complétude.

### B.2 — issues des Winners

- **obs-B2a** : Les **winners "courts" (bars_in_trade ≤ 4)** sont rares
  (130/1241 MNQ avec >0 PnL) ; les vrais winners patientent ≥ 6 bars
  (MFE moyen 1.78R → 2.90R). Insight : **ne pas couper trop vite** —
  mais l'inverse n'est PAS l'objectif (on veut couper les non-progressors,
  pas les patients). Donc H-B2 est conçue avec un N de 4-6 bars (pas 2).

---

## C. Optimisation des TP

### C.1 — issues des Winners (amplification)

- **obs-C1a** : Sur **MNQ aux heures tardives (H=18 à H=21)**,
  les **Auto-Close (profit)** capturent un cumul important :
  - H=18 : 12 AC-profit (+$1,494) vs 5 AC-loss (−$390) → net **+$1,103**
  - H=19 : 16 (+$3,014) vs 13 (−$874) → net **+$2,139**
  - H=20 : 10 (+$2,070) vs 4 (−$173) → net **+$1,897**
  - H=21 : 19 (+$2,898) vs 9 (−$670) → net **+$2,228**

  Plus le Canal Exit du même intervalle (H=18-21 : ~70 % WR) coupe
  prématurément des trades qui auraient atteint le 22:00 auto-close.
  → **H-C1** : `lab_disable_canal_exit_from_hour ∈ {18, 19, 20, 21}` —
  neutraliser canal_lower/upper après l'heure X (= ±inf) pour laisser
  l'auto-close à 22:00 prendre le PnL final.

- **obs-C1b** : Sur **MGC** le profil est moins favorable :
  - H=18 : 2 AC-profit (+$524) vs 4 AC-loss (−$130) → net **+$394**
  - H=19 : 5 (+$1,386) vs 5 (−$458) → net **+$928**
  - H=20 : 10 (+$1,585) vs 6 (−$256) → net **+$1,329**
  - H=21 : 19 (+$1,176) vs 16 (−$1,005) → net **+$170**

  Marges plus minces qu'MNQ, surtout à H=21 où AC-loss rattrape
  AC-profit. Effet probablement plus faible sur MGC.

### C.2 — issues des Losers

- **obs-C2a** : Les Canal Exit losers (~20 % du flux Canal Exit) ont
  MFE moyen ~0.3-0.4R — ils sortent in-loss après avoir essayé. La
  H-B2 défensive devrait recapturer une partie via le fast-HMA injecté.
  Pas d'hypothèse séparée — H-B2 traite ce sous-pilier.

---

## Synthèse — 6 hypothèses retenues

| ID | Pilier | Angle | Param | Source obs. |
|----|--------|-------|-------|-------------|
| H-A1 | A | W+L | `lab_entry_min_bars` | obs-A1a |
| H-A3 | A | L   | `lab_min_sl_points` | obs-A2a (ambigu, à tester) |
| H-A4 | A | L   | `lab_entry_blocked_hours` | obs-A2b |
| H-B1 | B | L   | `lab_max_2bar_body_pct` | obs-B1d (faible a priori) |
| H-B2 | B | L   | `lab_no_hw_flip_kill_bars` | obs-B1a, B1b, B1c |
| H-C1 | C | W   | `lab_disable_canal_exit_from_hour` | obs-C1a, C1b |

**Quota** : 3 piliers couverts (3 A, 2 B, 1 C) ; **4 hypothèses sur 6
issues des losers** (Angle L ou W+L) — largement au-dessus du minimum 1.

## Hypothèses non retenues pour ce cycle

- "Tightening `max_candle_pct`" — observation montre l'effet inverse
  (candles agressives = winners). REJECT a priori.
- "DOW blackout" — moteur ne supporte pas les blackouts par DOW. Item
  NOT TESTED dans HYPOTHESES.md.
- "Filter |last_hw_value| top quintile sur MGC" — déjà capturé par
  `sig_extreme` et `hw_range_on` dans V3. Doublon potentiel.
