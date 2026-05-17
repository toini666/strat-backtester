# 2026-05-17 — HMASSLOsciV3 exit_v1 campaign

Campagne mono-pilier d'évolution du **mécanisme de sortie** de `HMASSLOsciV3`
(final exit + partial). Aucune modification d'entrée, SL ou sizing.

## Statut

**Aucun winner V<N+1> produit.** Les 6 hypothèses testées (3 EX, 3 PT) sont
toutes REJECT selon le critère cross-asset strict de la mission. Une hypothèse
(H2 « HW only if profit ») est marquée **NOT TESTED** (limite moteur,
documentée). Voir [`REPORT.md`](REPORT.md) § Verdict pour la justification
chiffrée et § Pistes pour itération suivante pour les candidates à
re-explorer.

## Reproduction

```bash
source venv/bin/activate

# 0. Sanity test : Lab(defaults) == V3 (cent près).
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase2_hypotheses/00_sanity_lab_equals_v3.py

# 1. Dissection des sorties V3 (CSV + summary.json + OBSERVATIONS.md).
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase1_observation/run_analysis.py

# 2. A/B sweeps (un par hypothèse).
for f in scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase2_hypotheses/0[1-9]_*.py; do
    python "$f"
done

# 3. Combos / finer sweeps.
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase3_combinations/01_h6_fine_sweep.py

# 4. Walk-forward.
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/phase4_walkforward.py

# Verify : Lab(defaults) == published baselines après tous les changements.
python scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/verify_winner.py
```

## Arborescence

```
scripts/goals/2026-05-17_HMASSLOsciV3_exit_v1/
├── README.md                                 ← ce fichier
├── REPORT.md                                 ← rapport final 8 sections
├── HYPOTHESES.md                             ← tableau des 6 verdicts
├── verify_winner.py                          ← replay Lab(defaults) == V3
├── phase1_observation/
│   ├── OBSERVATIONS.md                       ← hypothèses brutes EX/PT × W/L
│   ├── run_analysis.py
│   └── outputs/
│       ├── exits_MNQ_v5.csv                  ← 1 ligne par trade enrichi
│       ├── exits_MGC_v3.csv
│       ├── exits_ALL.csv
│       └── summary.json                      ← aggregates bucketed
├── phase2_hypotheses/
│   ├── _shared.py                            ← BASELINES, helpers
│   ├── _runner.py                            ← runner A/B mutualisé
│   ├── _baseline_cache.json                  ← V3 metrics cache
│   ├── 00_sanity_lab_equals_v3.py            ← OBLIGATOIRE
│   ├── 01_ex_fast_cross_only.py              ← H1
│   ├── 02_ex_hw_only_if_profit.py            ← H2 (NOT TESTED)
│   ├── 03_ex_on_canal_flip.py                ← H3
│   ├── 04_ex_mfe_floor.py                    ← H4 (5 variants)
│   ├── 05_pt_on_fast_cross.py                ← H5/H6 (3 variants)
│   ├── 06_pt_on_canal_flip.py                ← H6 (2 variants)
│   ├── 07_pt_on_mfe_r.py                     ← H7 (4 variants)
│   └── logs/                                 ← un .log + .json par sweep
├── phase3_combinations/
│   ├── 01_h6_fine_sweep.py                   ← finer H6 + combo H6+H8
│   └── logs/
├── phase4_walkforward.py                     ← split 50/50 train/test
└── logs/
    ├── phase1_run_analysis.log
    ├── phase4_walkforward.log
    └── verify_winner.log
```

## Lab strategy

`src/strategies/hma_ssl_osci_v3_lab_exit_v1.py` (classe `HMASSLOsciV3LabExitV1`,
hérite de `HMASSLOsciV3`). Tous les flags Lab ont un default neutre — la
stratégie sans flag activé reproduit V3 strict au cent près (vérifié par
`00_sanity_lab_equals_v3.py` ET `verify_winner.py`).

Entrée correspondante dans `STRATEGY_WARMUP_BARS` (backend/api.py:67) : 250 bars.
