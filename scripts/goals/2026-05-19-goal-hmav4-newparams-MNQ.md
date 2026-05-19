# Goal — A/B test des nouveaux paramètres HMASSLOsciV4 vs preset gagnant V3 MNQ

Ton objectif est de **mesurer empiriquement** l'effet des 4 paramètres ajoutés à `HMASSLOsciV4` dans le portage PineScript V4 du 2026-05-19, en A/B contre le meilleur preset MNQ mono-asset actuel (`HMASSLOsciV3` WINNER). Chaque paramètre est testé seul, puis les combinaisons gagnantes sont validées. Le livrable est un (ou plusieurs) preset(s) V4 ≥ baseline V3 sur le ratio PnL/DD, plus un rapport qui explique quel paramètre apporte quoi.

---

## 🎯 Variables remplies

- **Stratégie** : `HMASSLOsciV4` (**déjà existante** — pas de Lab à créer ; les flags sont déjà dans la classe avec defaults neutres reproduisant V3).
- **Symbole** : `MNQ` (mono-asset).
- **Timeframe** : `7m` (figé — celui du preset baseline).
- **Période** : `2025-01-06T00:00` → `2026-05-15T00:00` (= période du preset baseline).
- **Preset baseline** : `[WIN MNQ] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $68.8k / DD $1.6k)`
  - id `34d5eaec-d375-40bb-a779-8fec81ff2633` dans `data/presets.json`
  - `risk_per_trade = 0.48%`, `max_contracts = 50`, `initial_equity = $50k`
  - Métriques de référence à confirmer en Phase 0 par replay : **PnL ≈ $68 800**, **max DD ≈ $1 600**
- **Auto-close** : `22:00` reference Brussels — **FIXE, jamais modifié**.
- **Initial equity / risk / max contracts** : identiques au preset baseline.
- **Engine settings** : blackouts actifs du preset baseline conservés (`08-09`, `11-12`, `12-13`, `14-15`, `22-23:59`), daily limits **off** (comme dans le preset).

---

## 🔬 Paramètres à tester (4 nouveaux V4 + 1 sanity)

Les 4 paramètres ajoutés au portage V4 du 2026-05-19. Tous ont des defaults neutres reproduisant V4 pré-update — qui lui-même reproduit V3 avec les defaults V4 préexistants.

| # | Pilier | Angle | Paramètre | Default (= V3) | Hypothèse à valider |
|--:|:------:|:-----:|-----------|----------------|---------------------|
| 1 | A (entry) | W+L | `block_entry_if_both_windows` | `False` | Bloquer les entrées quand les fenêtres long ET short sont ouvertes simultanément (canal HMA qui "tricote" autour de SSL) → réduit le DD en évitant les setups indécis. |
| 2 | C (TP) | W+L | `tp_mode_fast_hma_hw` | `True` | Désactiver le TP standard HMA rapide + HW pour laisser les trades vivre uniquement via SL/BE/auto-close ou via `tp_mode_slow_hma_cross` (combinable avec H3). À tester seul ET en combo. |
| 3 | C (TP) | W | `tp_mode_slow_hma_cross` | `False` | Sortir immédiatement à la clôture quand la HMA lente cross la baseline SSL en sens opposé (signal de fenêtre d'entrée inverse). Indépendant de H2. |
| 4 | C (TP) | W | `report_tp_if_mfi_ok` | `False` | Au moment du HW de sortie (TP HMA rapide + HW), si le trade est en perte ET que le nuage MFI (filtre ⑤) est encore aligné avec le trade, reporter au HW suivant. N'agit que sur le chemin TP HMA rapide + HW (donc nécessite H2 ON ou non testé). |

**Sanity test obligatoire (Phase 0)** : replay du preset baseline avec `HMASSLOsciV4` (mêmes params + 4 nouveaux à leurs defaults) → doit retrouver le PnL/DD du preset V3 à 1 cent près. Sinon, la rétrocompat est cassée — debug avant tout sweep.

> Note : Les autres knobs V4 préexistants (`reject_entry_at_sl_extreme`, `move_to_be_on_fast_hma_cross`, `final_exit_min_rr`, `move_to_be_on_rejected_exit`, `early_exit_fired_mode`) ne sont **pas l'objet de cette campagne**. Ils restent à leur default V3-equivalent dans tous les runs. Si le rapport identifie un combo où l'un d'eux pourrait amplifier un KEEP, c'est une piste pour la campagne suivante.

---

## 🗂️ Organisation des fichiers

```
scripts/goals/2026-05-19_HMASSLOsciV4_MNQ_newparams/
├─ README.md                         objectifs, statut, reproduction
├─ phase0_sanity/
│  ├─ run_sanity.py                  V4(defaults) == preset V3 baseline ? Doit afficher MATCH
│  └─ logs/run_sanity.log
├─ phase1_ab_tests/
│  ├─ _shared.py                     BASELINE_PRESET, BASELINE_METRICS, helpers print_ab_row
│  ├─ 01_block_entry_if_both_windows.py
│  ├─ 02_tp_mode_fast_hma_hw.py
│  ├─ 03_tp_mode_slow_hma_cross.py
│  ├─ 04_report_tp_if_mfi_ok.py
│  └─ logs/                          un .log par sweep
├─ phase2_combos/
│  ├─ 01_pairs.py                    paires des hypothèses KEEP
│  ├─ 02_full_combo.py               tous les KEEP activés ensemble
│  └─ logs/
├─ winner_preset.json                preset V4 gagnant (peut être == baseline V3 si rien ne KEEP)
├─ verify_preset.py                  doit afficher ✅ MATCH
├─ HYPOTHESES.md                     tableau verdicts
└─ REPORT.md                         rapport final
```

**Règles strictes** :
1. Tous les fichiers de campagne sous `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ_newparams/`. Rien à plat dans `scripts/`.
2. Ne **JAMAIS modifier `src/strategies/hma_ssl_osci_v4.py`** ni `src/engine/simulator.py`. Les 4 paramètres existent déjà ; on les configure via le dict `params`/`simulator_settings` passé au harness.
3. Toujours passer par `scripts/goals/_shared/harness.py::run_backtest` (qui câble bien les 7 champs V4 vers `SimulatorConfig` depuis le patch du 2026-05-19).
4. **Auto-close = 22:00**. Jamais sweepé.
5. Chaque sweep redirige sa sortie : `python … | tee logs/<nom>.log`.

---

## 🛠️ Méthode

### Phase 0 — Sanity check (obligatoire)

`phase0_sanity/run_sanity.py` :
1. Charger le preset baseline V3 (`data/presets.json` → id `34d5eaec-…`).
2. Construire un dict params identique mais avec `strategyName = "HMASSLOsciV4"` :
   - Garder tous les params V3 communs (ema_len, hma1_len, etc.).
   - Translater `signal_candle_sl_on=False` → `reject_entry_at_sl_extreme=False`.
   - Ignorer les params V3 absents de V4 (`hw_partial_pct`, `hw_partial_min_rr`, `block_loss_exit_before_partial`, `final_exit_mode`).
   - Laisser les params V4-nouveaux et V4-preexistants à leurs defaults.
3. Run via `harness.run_backtest()`. Comparer PnL, max DD, N trades, win rate, PF avec ceux du preset V3 ré-joué.
4. **Critère de succès** : delta PnL / DD ≤ $1 (effectivement = 0 hors arrondi flottant). Si non → rétrocompat cassée, stop campagne, débug.

### Phase 1 — A/B tests indépendants (4 sweeps)

Pour chaque paramètre H1-H4 :
1. Run **OFF** = baseline V3 reproduite par V4 (config Phase 0, paramètre = default).
2. Run **ON** = même config + paramètre activé.
3. Pour `tp_mode_fast_hma_hw=False` (H2), tester aussi en combinaison avec `tp_mode_slow_hma_cross=True` (sinon le trade n'a plus de TP du tout — utile à mesurer mais le rapport doit le souligner).
4. Pour `report_tp_if_mfi_ok=True` (H4), inutile de tester avec `tp_mode_fast_hma_hw=False` (le report n'agit que sur le chemin HW).
5. Format tableau A/B :

```
=== Hypothesis: <name> ===
Config              | PnL       | max DD   | N      | WR%   | PF    | P/DD
Baseline V3 (V4 OFF)| $68,800   | $1,600   | 372    | 51.5  | 2.45  | 43.0
ON                  | $XX,XXX   | $X,XXX   | XXX    | XX.X  | X.XX  | XX.X
ΔPnL=+/-$X, ΔDD=+/-$X, ΔP/DD=+/-X.X
```

6. **Verdict** par hypothèse :
   - **KEEP** si ΔP/DD ≥ +1.0 (i.e. ratio s'améliore d'au moins 1 unité) ET DD absolu ≤ $2 500.
   - **REJECT** si ΔP/DD < 0 ou DD > $2 500.
   - **MIXED** si ΔP/DD ∈ [0, +1.0] (effet marginal) — décrire avec nuance.

### Phase 2 — Combinaisons

1. **Paires** : tous les couples de KEEPs (max C(k,2) si k KEEPs).
2. **Full combo** : tous les KEEPs activés ensemble.
3. Comparer chaque combo à baseline V3 ET aux singletons KEEPs (effet additif vs interaction).
4. Si un combo gagne sur P/DD avec DD ≤ $2 500 → construit `winner_preset.json` V4 via `_shared/preset.py::build_preset` + `write_preset`.

### Phase 3 — Validation finale

1. Split temporel 50/50 : refit-ou-pas le winner V4 sur la 2ᵉ moitié — vérifier que l'effet ne vient pas d'une période unique.
2. Le winner doit afficher `verify_preset.py` → `✅ MATCH`.
3. Si **aucun combo ne bat la baseline V3**, le winner_preset.json est une copie de la baseline V3 (renommée V4-compat) et le REPORT explique pourquoi les 4 nouveaux paramètres n'apportent rien sur MNQ — c'est aussi un résultat livrable.

---

## 📦 Livrables obligatoires

### 1. Phase 0 sanity log
`phase0_sanity/logs/run_sanity.log` qui montre `✅ MATCH V3 baseline / V4 defaults` avec PnL/DD identiques.

### 2. `HYPOTHESES.md`
Tableau format obligatoire :

```markdown
| # | Pilier | Angle | Paramètre | Default | Test value | Verdict | ΔPnL$ | ΔDD$ | ΔP/DD | Note |
|--:|:------:|:-----:|-----------|---------|------------|---------|------:|-----:|------:|------|
| 1 | A | W+L | `block_entry_if_both_windows` | False | True | KEEP/REJECT/MIXED | … | … | … | … |
| 2 | C | W+L | `tp_mode_fast_hma_hw` | True | False (seul) | … | … | … | … | trade sans TP, attendre SL/BE/auto-close |
| 2'| C | W+L | `tp_mode_fast_hma_hw + tp_mode_slow_hma_cross` | True/False | False/True | … | … | … | … | combo |
| 3 | C | W | `tp_mode_slow_hma_cross` | False | True | … | … | … | … | … |
| 4 | C | W | `report_tp_if_mfi_ok` | False | True | … | … | … | … | n'agit que si H2 = True |
```

### 3. `winner_preset.json` au format UI
- `strategyName = "HMASSLOsciV4"`.
- Tous les params V4 listés (avec defaults inclus pour overrider l'UI au chargement).
- Tous les blackouts (actifs ET inactifs) explicites.
- `auto_close_hour = 22`, `auto_close_minute = 0`.
- Inséré dans `data/presets.json` via `write_preset`.
- Nom suggéré : `[WIN MNQ V4] HMASSLOsciV4 — MNQ 7m — V4 newparams (PnL $X / DD $X)`.

### 4. `verify_preset.py`
Rejoue le winner, affiche `✅ MATCH` ou `❌ DIFF`. Doit afficher MATCH avant de déclarer le job fini.

### 5. `REPORT.md`
Sections :
1. **Cadrage** — baseline V3, période, contraintes, 4 paramètres.
2. **Phase 0** — sanity OK (PnL/DD identiques).
3. **Phase 1 — A/B singles** — un sous-tableau par hypothèse + verdict.
4. **Phase 2 — combos** — paires + full combo vs baseline.
5. **Winner V4** — config gagnante en clair (ou explication si baseline V3 inchangée).
6. **Limites** — overfit, taille échantillon, dépendance asset (MNQ uniquement).
7. **Pistes itération suivante** — knobs V4 préexistants à tester (`final_exit_min_rr`, `move_to_be_on_*`, `early_exit_fired_mode`, `reject_entry_at_sl_extreme`) si le combo final ne suffit pas ; portage du test sur MGC.
8. **Reproduction** — 2-3 lignes.

### 6. Logs des sweeps
Tous les sweeps : `… | tee logs/<nom>.log`.

---

## 🚦 Critères de succès

Tu **ne peux déclarer le job fini** que si :

1. ✅ Phase 0 sanity affiche **PnL/DD identiques** au preset V3 baseline (à 1 cent près).
2. ✅ Les **4 paramètres** ont chacun un A/B test exécuté avec verdict KEEP / REJECT / MIXED.
3. ✅ Au moins **un combo Phase 2** a été testé (paires ou full).
4. ✅ `winner_preset.json` existe au format UI, inséré dans `data/presets.json`, `auto_close_hour=22`.
5. ✅ `python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ_newparams/verify_preset.py` → `✅ MATCH`.
6. ✅ `HYPOTHESES.md` complet, `REPORT.md` couvre les 8 sections.
7. ✅ Tous les fichiers sous `scripts/goals/2026-05-19_HMASSLOsciV4_MNQ_newparams/`.

**Si aucun combo ne bat la baseline V3** : c'est un résultat valide. Le winner = baseline V3 ré-encodée en V4-compat, et le REPORT explique pourquoi les 4 nouveaux paramètres n'apportent rien sur ce preset MNQ — utile pour la prochaine campagne (autres knobs V4, autres assets).

---

## 🧱 Contraintes techniques (rappels)

1. **Ne pas modifier** `src/strategies/hma_ssl_osci_v4.py` ni `src/engine/simulator.py`. Tout passe par params + simulator_settings.
2. **Toujours** `scripts/goals/_shared/harness.py::run_backtest` (jamais reconstruire `BacktestEngineSettings` à la main).
3. **`scripts/goals/_shared/harness.py` câble depuis le 2026-05-19** les 7 champs V4 (`final_exit_min_rr`, `move_to_be_*`, `early_exit_fired_mode`, `tp_mode_fast_hma_hw`, `tp_mode_slow_hma_cross`, `report_tp_if_mfi_ok`). Si le sanity Phase 0 montre un drift, vérifier que ces champs sont bien lus du dict `simulator_settings` retourné par `HMASSLOsciV4.get_simulator_settings()`.
4. **Defaults UI = source de vérité** (déjà branchés par le harness via `ui_default_engine_settings("HMASSLOsciV4")`).
5. Auto-close 22:00 — non négociable.
6. Tous les sweeps loggés sous `logs/`.

---

## ⚙️ Référence rapide

| Information | Fichier |
|-------------|---------|
| Stratégie V4 + nouveaux paramètres | `src/strategies/hma_ssl_osci_v4.py` |
| Defaults V4 (= reproduit V3 si non touchés) | `HMASSLOsciV4.default_params` |
| PineScript source de vérité | `Pinescripts/HMA-SSL-Osci-v4.txt` |
| Briefing du portage 2026-05-19 | conversation Claude du 2026-05-19 (résumé en mémoire) |
| Wiring API ↔ simulator | `backend/api.py` lignes 621, 847 (corrigé le 2026-05-19) |
| Wiring harness ↔ simulator | `scripts/goals/_shared/harness.py` lignes 131-180 (corrigé le 2026-05-19) |
| Logique des nouveaux paramètres dans le simulateur | `src/engine/simulator.py` autour des lignes 1330-1430 (`is_v4_exit_mode` block) |
| Preset baseline | `data/presets.json` id `34d5eaec-d375-40bb-a779-8fec81ff2633` |
| Exemple campagne récente | `scripts/goals/2026-05-15_HMASSLOsciV3_MNQ_v2/` |
