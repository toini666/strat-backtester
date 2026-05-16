# Campaign — HMASSLOsciV2 on MGC

**Period**: 2025-01-06 → 2026-05-15 (~17 months)
**Equity**: $50,000
**Max contracts**: 50
**Targets**: Net PnL > $30,000 AND Max DD < $2,500

## Reproduce

```bash
cd /Users/awagon/Documents/dev/nebular-apollo

# Run sweeps (in order)
for f in scripts/goals/2026-05-16_HMASSLOsciV2_MGC/sweeps/[0-9]*.py; do
  name=$(basename "$f" .py)
  python "$f" 2>&1 | tee "scripts/goals/2026-05-16_HMASSLOsciV2_MGC/logs/${name}.log"
done

# Build / verify winner
python scripts/goals/2026-05-16_HMASSLOsciV2_MGC/build_winner.py
python scripts/goals/2026-05-16_HMASSLOsciV2_MGC/verify_preset.py
```

## Status

See `REPORT.md` for the final result and analysis.
