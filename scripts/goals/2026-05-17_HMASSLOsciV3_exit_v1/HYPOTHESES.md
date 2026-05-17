# HYPOTHESES.md — Bilan des A/B tests

Baselines de référence :
- **MNQ_v5** : PnL $68,765 / DD $1,579 (P/DD 43.6) — 1241 trades.
- **MGC_v3** : PnL $44,692 / DD $1,944 (P/DD 23.0) — 865 trades.

Critère KEEP : ΔP/DD positif sur **les 2 presets** sur la période FULL, et négatif nulle part.
Le verdict consolidé est cross-asset stricte (la mission n'a que 2 presets de référence, donc pas de tolérance asymétrique).

| # | Levier | Angle | Hypothèse | Param ajouté | Source obs. | Verdict | Best ΔPnL$ MNQ | Best ΔPnL$ MGC | Best ΔP/DD MNQ | Best ΔP/DD MGC | Cross-preset | Note |
|--:|:------:|:-----:|-----------|--------------|-------------|---------|---------------:|---------------:|---------------:|---------------:|:------------:|------|
| 1 | EX | L | Sortir au cross HMA rapide sans attendre HW | `lab_exit_fast_cross_only=True` | obs-EX.L.1 | **REJECT** | −12,033 | −7,804 | −28.6 | −5.0 | 0/2 ✗ | HW pays +$23k en moyenne sur 1340 setups ; couper l'attente détruit l'edge. |
| 2 | EX | L | HW only if in profit (fidèle au brief) | `lab_exit_hw_only_if_profit=True` | obs-EX.L.1 | **NOT TESTED** | n/a | n/a | n/a | n/a | n/a | Non implémentable sans modif moteur : V3 Canal Exit (sim.py:1203) ferme avant le partial slot (sim.py:1262). Side-experiment dans logs/02 — voir REPORT § Limites. |
| 3 | EX | L | Fermer sur flip canal HMA contra | `lab_exit_on_canal_flip=True` | obs-EX.L.3 | **REJECT** | −21,549 | −18,301 | −31.1 | −12.9 | 0/2 ✗ | Le flip cap le tail des gros gagnants ; sum_delta_flip_vs_real = −$27k sur n=571. |
| 4 | EX | W+L | MFE-floor full close | `lab_exit_mfe_floor_r`, `lab_exit_mfe_floor_trigger_r` (sweep 5 var.) | obs-EX.L.2 | **REJECT** | −5,966 (trig1.5,floor1.0) | −1,156 (trig2.0,floor1.0) | −21.5 | −2.0 | 0/2 ✗ | Coupe certains give-backs mais sacrifie davantage de winners qui auraient continué — net négatif sur tous les variants. Le meilleur (trig2.0,floor1.0) garde le DD identique sur MNQ mais perd $8k de PnL. |
| 5 | PT | W | Partial X % au cross HMA rapide (in-profit gate) | `lab_pt_on_fast_cross_pct` ∈ {10,15,20,25,50,75} | obs-PT.W.1 | **MIXED → REJECT** | +1,684 (10%) | −4,477 (10%) | −20.0 | −5.3 | 0/2 ✗ FULL ; 1/2 ✓ MNQ TEST_H2 | Seule hypothèse à montrer un PnL positif sur MNQ FULL (+$1,225 à 25 %, +$1,684 à 10 %), mais DD inflate de +$1,400 sur la même bar (événement structurel concentré en TRAIN). Walk-forward TEST_H2 sur MNQ : **ΔPnL=+1,319 ET ΔDD=−154** (les 2 positifs out-of-sample). MGC perd dans les 3 folds. Verdict strict cross-asset : REJECT. À ré-évaluer dans une campagne avec plus de données out-of-sample (§ Pistes). |
| 6 | PT | L | Partial X % au flip canal HMA contra | `lab_pt_on_canal_flip_pct` ∈ {25,50} | obs-EX.L.3 / PT.W.2 | **REJECT** | −2,832 (25%) | −5,512 (25%) | −18.2 | −8.7 | 0/2 ✗ | Le flip est un signal "tail-cap" même en partial — perd plus que protège. |
| 7 | PT | L | Partial X % au seuil MFE | `lab_pt_on_mfe_r_pct`, `lab_pt_on_mfe_r_trigger` (sweep 4 var.) | obs-PT.L.1 | **REJECT** | −2,496 (50%@1.5R) | −5,769 (50%@1.5R) | −19.4 | −5.1 | 0/2 ✗ | Locker au seuil MFE sacrifie le run des gros winners ; le tail de PnL > la queue défensive. |

**Comptage quota** :
- Hypothèses comptabilisées (verdict assigné) : H1, H3, H4, H5, H6, H7 = **6 hypothèses** ✓ (mission : 5-9).
- Levier EX : 3 (H1, H3, H4) ✓ (mission : 2-5).
- Levier PT : 3 (H5, H6, H7) ✓ (mission : 1-4).
- Angle L : H1, H3, H6, H7 (4 lignes) ✓ (mission : ≥1).
- Angle W+L : H4 (1 ligne).
- Angle W : H5 (1 ligne).
- Hypothèse hors quota (NOT TESTED) : H2 (limite moteur, documentée).

**Verdict global** : **aucune hypothèse ne bat les baselines V3 selon le critère cross-asset strict.** La sortie « HMA rapide → HW » de V3 est un édifice net-positif sur les 2 presets (sum Δ HW − fast = +$23,248 cross-asset), et chaque modification testée détruit plus de PnL qu'elle n'en récupère, ou inflate le DD de manière structurelle.

Aucun `winner_v6_MNQ.json` / `winner_v4_MGC.json` n'est produit ce cycle. Ce résultat négatif est explicitement permis par la mission (« Au moins 1 winner V<N+1> existe pour ≥ 1 asset, sinon le rapport explique pourquoi aucune combinaison ne bat les baselines — c'est un résultat valide »).
