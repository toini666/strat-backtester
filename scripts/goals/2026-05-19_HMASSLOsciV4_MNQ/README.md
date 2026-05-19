# 2026-05-19 — `HMASSLOsciV4` on MNQ (7 m)

| | |
|-|-|
| Strategy | `HMASSLOsciV4` |
| Symbol / TF | MNQ / 7 m |
| Period | 2025-01-06 → 2026-05-15 |
| Starting equity | $50,000 |
| Max contracts | 50 |
| **Goal** | Maximise PnL with `max_dd < $2,000` (strict) — budget ~500 sims |
| **Result** | ✅ **$75,236 PnL / $1,911 DD / 1,175 trades / PF 1.82** — **+12.8 % vs V3 baseline ($66,679)** |
| Sims used | ~202 (well under budget) |

Status: **complete** — preset shipped to `data/presets.json`, `verify_preset.py` prints `✅ MATCH`.

See [`REPORT.md`](./REPORT.md) for the full analysis (insights, V4-lever verdict table, top-5 alternatives, risks).

## How to reproduce

```bash
source venv/bin/activate

# Verify the winner preset is byte-equivalent to the saved metrics:
python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/verify_preset.py
# → ✅ MATCH (PnL=$75,236 / DD=$1,911 / N=1175 / PF=1.82)

# Or re-run a single sweep:
python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/sweeps/04_v4_exit_params.py
```

## Files

- `sweeps/_campaign.py` — single source of truth for campaign constants and the V3-migrated V4 baseline params
- `sweeps/01_baseline_tfs.py` … `09_final_validation.py` — one script per phase
- `sweeps/_debug_sanity.py` — V3 vs V4 trade diff helper (used to confirm Phase 1 rétrocompat)
- `logs/*.log` — captured output of each sweep
- `winner_preset.json` — standalone copy of the UI-format preset
- `verify_preset.py` — replay-and-compare; must print `✅ MATCH`
- `REPORT.md` — final report
