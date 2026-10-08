# Referee reanalysis, 3 October 2026

This bundle reanalyzes retained observations. It contains no new performance campaign and does not relabel historical timings as measurements of repaired code.

- `analysis.json`: static-policy scores, startup totals, geometry, public-scale RSS and seed-specific pilot ratios.
- `threshold_regret.csv`: case-level normalized costs and excess latency versus the faster forced-path median. Negative excess is observed timing variation.
- `manifest.json`: exact source CSV hashes and the analysis script hash.
- `verification.json`: independently computed numerical/provenance checks.

Regenerate from the repository root with Python 3.14:

```bash
python -B -c "import tools.referee_revision as r; r.analysis()"
python -B tools/verify_referee_revision.py
```

The checker recomputes scores, paired startup totals, RSS and pilot/repair ratios using a separate implementation. It also verifies source hashes and that tracked historical evidence has not changed relative to the current Git baseline. This is internal reconciliation, not independent external reproduction or timing replication. See the source manifest and original bundles for environments, timing boundaries and independent-unit limitations.
