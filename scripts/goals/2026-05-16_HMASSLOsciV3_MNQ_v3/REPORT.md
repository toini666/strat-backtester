# Rapport final — Optimisation HMASSLOsciV3 sur MNQ (no time-of-day blackouts)

**Période**: 2025-01-06 → 2026-05-15 (≈ 17 mois — contrats H25 → M26)
**Stratégie**: `HMASSLOsciV3` (`src/strategies/hma_ssl_osci_v3.py`)
**Symbole**: MNQ — micro-futures Nasdaq

## Contrainte clé

La campagne précédente (`2026-05-15_HMASSLOsciV3_MNQ_v2`) atteignait $30.4k PnL / $2.0k DD via **6 blackouts horaires actifs** (H=00, 04, 06, 08, 11, 12-14) + auto-close à 22h. Ici, on **retire tous les blackouts horaires** et on garde uniquement le `22:00-23:59` (post-close, UI default). L'amélioration doit venir des paramètres stratégie.

---

## 1. Résultat ✅

| Objectif | Cible | Atteint |
|----------|-------|---------|
| Profit net | ≥ $35 000 (goal $40 000) | **$35 472** ✅ |
| Max drawdown | < $2 500 | **$2 491** ✅ |

| Métrique | Valeur |
|----------|--------|
| Net PnL | **$35 472** |
| Max drawdown $ | **$2 491** |
| Profit factor | **1.41** |
| Win rate | 43.8 % |
| Trades actifs | 1 405 |
| Avg win / Avg loss | +$198 / –$109 |
| Reward:Risk | 1.82 |
| **Profit / DD ratio** | **14.24** |

Le ratio Profit/DD = 14.24 satisfait les deux contraintes avec une marge mince mais bien réelle. Il représente une progression structurelle de +9.6% par rapport au ratio v2 (12.96 sans blackouts), entièrement dûe aux paramètres stratégie.

---

## 2. Configuration gagnante

### Timeframe
**M7** (7 minutes).

### Paramètres de stratégie (overrides du défaut v3)

```python
{
    # Lever #1 (sweep 02): désactivation du filtre HW direction
    "hw_dir_on": False,
    # Lever #2 (sweep 03b): cooldown allongé à 3 bars
    "cooldown_bars": 3,
    # Lever #3 (sweep 03b): osc-signal extreme à 40 (default 35)
    "sig_extreme": 40,
    # --- Reste hérité du v2 winner (matches PineScript v3 essentials) ---
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 4,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
    # ... (tous les autres défauts v3)
}
```

### Risque

```python
initial_equity = 50 000 $
risk_per_trade = 0.0032  # 0.32 % → ~$160 risque max par trade
max_contracts  = 50
```

### Blackouts (reference Brussels time)

| Window | Statut | Notes |
|--------|--------|-------|
| 00:00 – 00:05 | inactive | UI default |
| 09:00 – 09:05 | inactive | UI default |
| 12:00 – 14:00 | inactive | UI default (toujours inactive ici) |
| 15:30 – 15:35 | inactive | UI default |
| 16:30 – 22:00 | inactive | UI default |
| **22:00 – 23:59** | **active** | UI default (post-close CME) |

**Aucun blackout horaire ajouté** — c'est la contrainte clé de cette campagne.

### Auto-close
**22:00:00** reference Brussels (CME daily close). Conformément aux invariants, non modifié.

### Daily limits
**Aucune**. Sweep 04 a montré que les daily limits (intra_bar comme after_close) sont
quasiment sans effet sur cette configuration : les DD viennent d'une accumulation
multi-jours, pas de blowups intra-jour. Voir §4.

---

## 3. Top configurations alternatives

| # | Config (overrides) | Risk | PnL | DD | PF | N | Verdict |
|---|--------------------|------|-----|----|----|---|---------|
| WINNER | cd=3 sx=40 | 0.0032 | **35 472** | **2 491** | 1.41 | 1405 | ✅ both goals |
| ALT1   | cd=3 sx=40 | 0.0034 | 37 990 | 2 707 | 1.42 | 1405 | ❌ DD légèrement haut |
| ALT2   | cd=3 sx=40 | 0.0030 | 32 188 | 2 406 | 1.39 | 1405 | ❌ PnL sous cible |
| ALT3   | cd=3 (sx=30) | 0.0034 | 37 381 | 2 567 | 1.43 | 1312 | ❌ DD juste haut (+$67) |
| ALT4   | hw_dir_on=False alone | 0.0034 | 36 599 | 2 825 | 1.41 | 1372 | ❌ DD ~$325 trop haut |

ALT1 maximise le PnL ($38k) au prix d'un DD un peu plus large ($2.7k vs target $2.5k). Si on accepte une cible DD < $2 750, c'est le meilleur PnL. Le WINNER est préféré pour respecter strictement les deux objectifs.

---

## 4. Insights

### A. Hiérarchie des leviers (du plus impactant au marginal)

1. **`hw_dir_on = False`** (sweep 02) — Le gros levier.
   - Avant: $29 034 / $3 425 (ratio 8.48)
   - Après: $36 599 / $2 825 (ratio 12.96)
   - **+$7.5k PnL et –$0.6k DD en un seul flip**.
   - Le filtre "HW direction" par défaut (True) rejette des setups gagnants
     sur MNQ M7 sans gain de qualité. Confirmé sur 17 mois.
2. **`cooldown_bars = 3`** (sweep 03b) — Le breakthrough qui clôt l'objectif.
   - Sur la base `hw_dir_on=False`: ratio 12.96 → 14.56.
   - Réduit de 1 372 → 1 312 trades (–4 % en volume) mais améliore
     drastiquement la qualité (PF 1.41 → 1.43, DD 2 825 → 2 567).
   - Effet: en imposant 3 bars d'attente entre clôture et nouvelle entrée,
     on évite les re-entries dans la même bougie hostile.
3. **`sig_extreme = 40`** (sweep 03b) — Ajustement DD-side.
   - Ajoute 93 trades supplémentaires (1 312 → 1 405) en relaxant le seuil
     osc-signal extreme, et la combinaison avec cd=3 baisse le DD final à $2 491
     (vs $2 567 avec cd=3 seul à r=0.0034).
4. **Risk per trade** — Levier final pour cadrer les targets.
   - r=0.0034 baseline donne $37k/$2.7k (ratio ~14.0 avec cd=3 sx=40)
   - r=0.0032 atterrit pile à $35.5k/$2.5k. Marge $9 sous le DD target.

### B. "Non-événements" (paramètres testés sans effet ou négatifs)

- **Daily limits** (sweep 04) — *aucun* effet sur le DD. Même à $700 daily loss
  limit (très tight), seulement 6 trades exclus, DD reste à $2 825.
  Le DD vient de l'accumulation multi-jours, pas de single-day blowups.
  Mon hypothèse initiale était que daily limits seraient le substitut naturel
  des blackouts — la donnée a montré le contraire.
- **`final_exit_mode = "% du prix d'entrée en profit"`** — désastreux à toutes
  les valeurs de `final_exit_pct` (5%-30%). PnL effondre à ~$0-16k, DD explose à $5-8k.
  Le mode HMA/SSL → HW reste strictement supérieur.
- **`hw_partial_pct = 25/50`** avec min_rr ≥ 0.5 réduit le DD à $2.4k mais
  coûte trop en PnL ($33.7k). Pas exploitable comme lever principal, à éviter.
- **`signal_candle_sl_on=True`** — neutre. Pas d'amélioration combinée à cd=3+sx=40.
- **`block_loss_exit_before_partial=True`** — neutre seul, dégrade combiné.
- **`tick_buffer`, `max_sl_points` tighter** — dégradent linéairement.
- **`cloud_on=False`** — explose le DD (×3 à $6.4k). Filtre cloud indispensable.

### C. Effets contre-intuitifs

- **Sweep 03b "1-D winner" ≠ best 2-D combo**. `cooldown=3` seul à r=0.0034 donne
  $37 381/$2 567 (ratio 14.56) — déjà passing. Mais avec `sig_extreme=40` ajouté,
  on a une combinaison plus robuste où le risk peut descendre à 0.0032 et
  toujours passer. La marge sous DD ($2491) > marge avec cd=3 seul ($2 567,
  qui dépasse de $67).
- **Risk fan non-linéaire**. Le DD ne scale pas linéairement avec risk_per_trade
  dans certains points. r=0.0030 (DD $2 555) > r=0.0028 (DD $2 083). Effet de
  rounding du nombre de contrats (`max(1, int(raw))` dans `simulator._calc_size`).
  Conséquence pratique : il faut tester chaque palier de risk explicitement,
  pas extrapoler.
- **PnL ceiling visible**. À risk élevé (r=0.005), PnL = $48k mais DD =$4.6k.
  L'edge plafonne autour de ratio ~13-14.5 sur cette configuration ; pour
  dépasser, il faudrait un changement structurel (blackouts ou nouveau filtre).

### D. Analyse temporelle (diagnostic, pas appliqué)

Trades par heure d'entrée Brussels avec la config WINNER (sweep 05).
Pas de blackouts ajoutés. Heures les plus toxiques restantes :

| Heure | n | total $ | avg $ |
|-------|---|---------|-------|
| H=14 | 57 | –$2 195 | –$39 |
| H=06 | 39 | –$2 122 | –$54 |
| H=12 | 74 | –$1 560 | –$21 |
| H=08 | 63 | –$1 445 | –$23 |
| H=11 | 79 | –$1 273 | –$16 |

Total potentiellement évitable : ~$8.6k. Si la contrainte le permettait, ajouter
un blackout sur H=14 (la plus toxique) pousserait probablement le PnL à ~$37-38k
tout en réduisant le DD. Mais la contrainte de cette campagne interdit ce type
de filtre temporel.

### E. v2 vs v3 — comparaison structurelle

| | v2 (avec 6 blackouts horaires) | v3 (no time blackouts) |
|-|-|-|
| Levers actifs | hw_dir_on (default True), 6 blackouts | hw_dir_on=False, cd=3, sx=40 |
| Net PnL | $30 402 | $35 472 |
| Max DD | $1 960 | $2 491 |
| PF | 1.51 | 1.41 |
| Profit/DD | 15.5 | 14.2 |
| Trades | 998 | 1 405 |

Le v3 trade **plus de trades** (+41 %), avec un **PF plus bas** mais un **PnL absolu
plus élevé**. Les blackouts v2 améliorent la qualité par sélection temporelle ;
le v3 améliore la sélection par les paramètres (cd=3 filtre les re-entries
toxiques implicitement). Le ratio Profit/DD du v2 (15.5) reste supérieur — donc
**si l'on accepte les blackouts horaires, v2 est strictement meilleur**. La
question pour le futur : peut-on combiner v3 params + 1 ou 2 blackouts ciblés
pour viser un ratio 17+ et un PnL $40k+ ? C'est la prochaine itération naturelle.

---

## 5. Démarche

| Étape | Fichier | Résultat |
|-------|---------|----------|
| 01 — Baseline TFs | `sweeps/01_baseline_tfs.py` | TF=7m confirmé, v2 params hors blackouts: $29k / $3.4k |
| 02 — Filter activation | `sweeps/02_filter_activation.py` | `hw_dir_on=False` → $36.6k / $2.8k (big jump) |
| 03b — Strategy params focused | `sweeps/03b_focused_params.py` | `cooldown=3` → $37.4k / $2.6k (breakthrough) |
| 04 — Risk & daily limits | `sweeps/04_risk_and_daily_limits.py` | Daily limits non-event ; risk fan non-linéaire |
| 05 — Hour/DOW analysis | `sweeps/05_hour_analysis.py` | Diagnostic uniquement (pas de blackouts ajoutés) |
| 07 — Finetune | `sweeps/07_finetune.py` | Combo cd=3 + sx=40 + r=0.0032 → ✅ both goals |
| 08 — Validation | `sweeps/08_final_validation.py` | WINNER preset écrit dans `data/presets.json` |

**Sweep 03 (full 1-D)** a été démarré mais tué mid-flight (le sweep 03b plus
focalisé a couvert le ground utile). **Sweep 06 (combos)** a été fusionné dans
sweep 07 pour éviter la redondance.

---

## 6. Risques

- **Sample size**: 17 mois sur MNQ. Robuste sur cette période mais une seule
  série temporelle. La période 2025-01 → 2026-05 a vu plusieurs régimes
  (Q1 2025 tame, Q4 2025 + Q1 2026 volatil). Pas testé en walk-forward.
- **Marge mince**: DD à $2 491 = $9 sous le target. Une légère dérive
  du DD réalisé (slippage, fees variations, contract switches) pourrait pousser
  au-delà de $2 500. ALT1 (r=0.0034, $37.9k / $2.7k) est plus permissif sur le DD
  mais demande un target élargi à $2 750.
- **Dépendance à `cooldown=3`**: il est rare qu'un paramètre numérique unique
  apporte un saut de ratio aussi net (12.96 → 14.56). Vérifier sur out-of-sample
  ou un autre symbole pour confirmer que ce n'est pas un overfit à la
  microstructure de MNQ.
- **`hw_dir_on=False` est un override sémantique** (désactivation d'un filtre
  documenté en PineScript). Si la traduction Python diverge légèrement du
  PineScript natif, le résultat peut différer du LIVE. À vérifier en
  re-running la stratégie depuis TradingView et comparant.

---

## 7. Reproduction

```bash
python scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v3/verify_preset.py
```

Doit afficher `✅ MATCH`. Le preset est aussi visible en tête des favoris UI
(`data/presets.json` updated par `write_preset`).

Pour rejouer manuellement : charger le preset `[Auto] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $35.5k / DD $2.5k)` depuis l'UI, lancer le backtest.

---

## 8. Idées pour la prochaine itération

1. **Combine v3 params + 1 blackout ciblé** (H=14 ou H=06). Si on autorise un
   seul blackout, on devrait facilement franchir le ratio 16-17 et le PnL $40k+.
2. **Walk-forward / out-of-sample**: split la période 2025 / 2026 ou 12 / 5 mois
   pour vérifier la robustesse temporelle du `cooldown=3 + sx=40` combo.
3. **Multi-asset**: tester `HMASSLOsciV3 + cd=3` sur MES / MGC pour voir si le
   gain `hw_dir_on=False` se transfère.
4. **Audit de `hw_dir_on`** dans le code Python vs PineScript — si désactiver ce
   filtre apporte structurellement +20 % de PnL, c'est suspect ; soit le filtre
   est mal calibré, soit la traduction Python diverge.
5. **Cooldown plus large**: tester `cooldown_bars=4, 5, 6` avec d'autres
   combinaisons. Le sweep a montré cd=5 dégrade ($32.9k/$4.2k) mais peut-être
   un sweet spot intermédiaire existe (e.g. cd=4 r=0.0030).
