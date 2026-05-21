# MomentumCheckerV2 — COMBO RIsky Multi-Asset (MGC + MNQ 7m) — DD reduction

**Seed**: `COMBO RIsky Multi-Asset — MGC/MNQ` preset (more aggressive than the prior
multi-asset winner: MNQ risk=0.60 % with be_at_rr=0).

**Goal**: drop combined `max_dd_$` < $2,500 with the smallest possible PnL cost.

**Locked constraints**:
- `maxContracts = 20` on both legs (user-stated, non-negotiable).
- Daily win/loss limits OFF for the deliverable (user preference). Tested in
  `after_close` mode out of curiosity in Phase 07.
- `auto_close_hour = 22` (CME daily close, ref Brussels).

**Period**: 2025-01-07 → 2026-05-15 · initial equity $50,000.

**Budget**: 500 sims.

## Layout
- `sweeps/_campaign.py` — preset snapshot, `run_multi`, helpers.
- `sweeps/00_baseline.py` — replay the preset.
- `sweeps/01_mnq_be_sweep.py` — MNQ `be_at_rr` lever.
- `sweeps/02_dd_episode_analysis.py` — DD trough trade-by-trade breakdown.
- `sweeps/03_mnq_risk_sweep.py` — MNQ `risk_per_trade` sweep.
- `sweeps/04_mgc_risk_sweep.py` — MGC `risk_per_trade` sweep.
- `sweeps/05_joint_risk_grid.py` — Joint risk × `be_at_rr` grid.
- `sweeps/06_mnq_blackout.py` — MNQ blackout extension over the US-AM cluster.
- `sweeps/07_daily_limits_curiosity.py` — Daily win/loss limits sweep.
- `winner_preset.json` — locked deliverable (UI format).
- `verify_preset.py` — replays preset, must print `✅ MATCH`.
- `REPORT.md` — campaign writeup.

## Key results (TBD until winner lock)

See `REPORT.md` for the final figures.
