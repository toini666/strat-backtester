# MomentumCheckerV2 Multi-Asset — MGC + MNQ 7m — DD reduction campaign

**Date**: 2026-05-20
**Anchor preset**: `Base combo momCheckv2 Multi-Asset — MGC/MNQ`

**Goal**: reduce combined max_dd_$ below **$2,300** (ideally **$2,000**) while
sacrificing as little PnL as possible.

**Constraints (locked)**: maxContracts=20, no daily win/loss limits,
auto_close_hour=22.

**Budget**: 500 sims.

## Result

```
WINNER — [Auto] MomentumCheckerV2 — MGC+MNQ multi-asset — DD<$2.3k

PnL=$96,428    DD=$2,254    N=1,654   WR=39.9%   PF=1.57   P/DD=42.8
  MGC risk=0.53%   PnL=$55,592 (856 trades)
  MNQ risk=0.345%  PnL=$40,836 (798 trades)
```

vs **Baseline** ($138,814 / $3,601):
**−30.5% PnL** for **−37.4% DD**. P/DD improves from 38.5 to 42.8.

## Sub-$2,000 — NOT REACHABLE

Despite extensive exploration with aggressive levers (be_mgc=1.0-1.5, MNQ risk
0.15%, etc.), the combined account DD never went below **$2,204**. The floor
is structural: MGC's worst losing streak (early April 2026) hits the
1-contract minimum and contributes ~$2,200 of DD regardless of risk setting.

## See

- `REPORT.md` — full lever attribution and phase log.
- `winner_preset.json` — the locked preset, also inserted into `data/presets.json`.
- `verify_preset.py` — replay verification (harness + actual backend code path).
- `sweeps/` — phase-by-phase sweep scripts.
- `logs/` — captured sweep outputs.
