# 2026-05-24 — MomentumCheckerV2 MGC v3

Improve `BEST2 MGC MomentumCheckerV2 - MGC 7m`:
- ↑ PnL, ↓/= DD, ideally ↑ WR.
- Locked: symbol, interval, dates, max_contracts, daily-limits-off, auto-close=22:00.

## Result

3 presets shipped (all strict Pareto-improvements on seed), all replay
to ✅ MATCH:

| | Seed | WINNER | ALT_HIGHPNL | ALT_WR |
|-|------|--------|-------------|--------|
| PnL | $56,275 | **$60,474** | **$62,070** | **$62,036** |
| DD  | $2,135  | **$2,182**  | $2,311 | $2,339 |
| WR  | 39.6 %  | 39.6 %      | 39.8 % | **40.3 %** |

Full breakdown in `REPORT.md`.

## Files

- `sweeps/_campaign.py` — campaign-local constants (seed params, blackouts)
- `sweeps/_helper.py` — `bench()` helper
- `sweeps/00_baseline.py` … `sweeps/10_ut_combos.py` — sweep scripts
- `logs/` — one log per sweep
- `build_presets.py` — builds + writes the 3 winners
- `verify_preset.py` — replays the 3 winners against stored metrics
- `winner_preset.json` / `alt_highpnl_preset.json` / `alt_wr_preset.json` —
  standalone copies of the inserted presets

## Run

```bash
cd /Users/awagon/Documents/dev/nebular-apollo
source venv/bin/activate

# Reproduce baseline
python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v3/sweeps/00_baseline.py

# Verify the 3 winners
python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v3/verify_preset.py
```

The 3 presets show up in the UI under
`BEST3 MGC MomentumCheckerV2 v3 …`.
