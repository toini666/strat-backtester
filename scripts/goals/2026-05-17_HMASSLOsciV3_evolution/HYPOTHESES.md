# HYPOTHESES — Verdicts par hypothèse

Format : ΔPnL$ et ΔDD$ rapportés au **meilleur point sweep** par preset (best
absolute ΔP/DD). Cross-preset = nombre de baselines avec ΔP/DD > 0.

| # | Pilier | Angle | Hypothèse | Param ajouté | Source obs. | Verdict | Best ΔPnL$ | Best ΔDD$ | Best ΔP/DD | Cross-preset | Note |
|--:|:------:|:-----:|-----------|--------------|-------------|---------|-----------:|----------:|-----------:|--------------|------|
| 1 | A | W+L | Skip first N bars after slow-cross setup | `lab_entry_min_bars` | obs-A1a | **REJECT** | −$18,312 / −$23,827 | +$1,841 / +$770 | −28.80 / −15.30 | 0/2 | Bar 0 capte des setups qu'on ne retrouve pas plus tard ; aucune valeur de N positive. |
| 2 | A | L   | Minimum SL distance filter | `lab_min_sl_points` | obs-A2a | **REJECT** | −$13,895 / −$13,413 | +$1,128 / −$57 | −23.28 / −6.41 | 0/2 | Small-SL trades sont gros contributeurs PnL via la taille — couper réduit DD modestement mais sacrifie trop de PnL. |
| 3 | A | L   | Block toxic hours via strategy filter | `lab_entry_blocked_hours` | obs-A2b | **MIXED** (KEEP MGC) | −$295/−$944 (MNQ — DD↑) / **+$1,622 (MGC)** | +$700 / **−$15 (MGC)** | −13.08 / **+1.01 (MGC)** | 1/2 | MNQ : bloquer H=6 explose le DD (+$996). **MGC à (22,20) : KEEP** — PnL ↑ et DD inchangé. Walk-forward : train ↑ ; test légère dégradation. |
| 4 | B | L   | Max 2-bar cumulative body % | `lab_max_2bar_body_pct` | obs-B1d | **REJECT** | −$1,358 / −$1,304 | +$0 / +$0 | −0.86 / −0.67 | 0/2 | Confirme l'observation Phase 1 : les candles agressives sont GOOD entries. Le filtre n'enlève que du PnL net. |
| 5 | B | L   | Defensive exit if early adverse HW | `lab_no_hw_flip_kill_bars` | obs-B1a/B1b/B1c | **NOT TESTED** | — | — | — | — | Le mode `v3_fast_hma_ssl` du simulateur ferme la position sur le PROCHAIN HW cross (favorable OU adverse) une fois `pending_final_exit` armé. Injecter notre kill ferme donc systématiquement les trades patients sur leur prochain HW favorable. Aucun mécanisme propre dans le simulateur ne permet de tester l'hypothèse sans refonte. Documenté pour itération future. |
| 6 | C | W   | Disable canal exit late (let auto-close take it) | `lab_disable_canal_exit_from_hour` | obs-C1a | **MIXED** (KEEP MGC) | −$716 (MNQ; DD↑) / **+$1,064 (MGC à h=21)** | +$0 / **+$0 (MGC à h=21)** | −0.45 / **+0.55 (MGC)** | 1/2 | MNQ : aucune valeur n'améliore. **MGC à `from_hour=21` : KEEP** — supprime fast_hma_exit arming après 21h, PnL ↑ et DD inchangé. Walk-forward : MIXED inverse (test ↑, train ↓). |
| NT-1 | B/A | L | DOW blackout (Mon/Wed dry vs Tue/Thu/Fri) | — | obs in REPORT MNQ_v5 §4-D | **NOT TESTED** | — | — | — | — | Le moteur (`BlackoutWindowSettings`) ne supporte que des fenêtres time-of-day, pas DOW. Refonte moteur nécessaire. |

## Quota et angles

- **Couverture piliers** : A=3 (#1, #2, #3) ✓ ; B=2 (#4, #5) ✓ ; C=1 (#6) ✓ → **3 piliers couverts**.
- **Quota losers (Angle L ou W+L)** : #1 (W+L), #2 (L), #3 (L), #4 (L), #5 (L) → **5/6 hypothèses issues des losers**. ✓
- **Hypothèses testées** (REJECT + MIXED + KEEP, exclut NOT TESTED) : **5**, dans la fenêtre 3-9 demandée. ✓
- Walk-forward demote (mission §4) : H-A4 a dégradé out-of-fold de manière marginale (-0.59 P/DD test) → MIXED dans cette table. H-C1 a dégradé in-fold (-0.13 train) → MIXED. **Le COMBO H-A4+H-C1 est temporairement neutre out-of-fold (P/DD −0.04 test)**, capturé comme winner.

## Winner V4 sélectionné

**MGC seulement** — combo (H-A4 + H-C1) : PnL **$47,164** / DD **$1,971** / P/DD **23.93** (vs baseline 22.99, **+4.1 %**). Voir `winner_v4_MGC.json`.

**MNQ** : aucune hypothèse testée n'améliore P/DD. La baseline V5 (P/DD 43.55) est un local-optimum très dense ; tous les filtres entry/SL testés altèrent négativement l'edge. Causes plausibles documentées dans `REPORT.md` §6.
