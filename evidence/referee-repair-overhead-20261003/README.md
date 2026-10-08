# Bounded JSON repair overhead check

This is a descriptive before/after comparison of the JSON ownership and encoded-equality repair on three fixed string workloads. It does not recalibrate the selector or replace the historical publication campaign.

`manifest.json` was written before measurement and records Python 3.14.3, Windows, hash seed 20261003, profiles, timing boundaries and source hashes. `source_before` is the implementation at commit `37d27d465ffc922a3881b85bb415574f956a9a09`; `source_after` is the measured repaired implementation. The copied harness is retained alongside raw results.

There are six repository pairs per profile: one warm-up pair and five measured pairs, 36 executions overall. Before/after order alternates by block. All profiles share one process and physical host; each block and variant builds a fresh SQLite repository from the same deterministic profile. Read timers include canonical output construction. Open/verify is separate. The fixed log/Merkle/hybrid order does not establish unbiased cross-strategy rankings.

`summary.json` contains marginal medians and median paired after/before ratios; these are different estimands. `correctness.json` records matching string roots and reopening a genuine pre-repair nested-JSON repository with the repaired reader. Existing encoding and schema are unchanged. The repair cannot recover updates discarded before this revision.

Reproduce to a NEW directory from the repository root, with the current core matching `source_after`:

```bash
PYTHONHASHSEED=20261003 python -B experiments/referee_repair_check.py \
  --baseline evidence/referee-repair-overhead-20261003/source_before \
  --output evidence/referee-repair-overhead-new-run
python -B tools/verify_referee_revision.py
```

Do not overwrite this retained run. The independent checker targets this archived run; a fresh run has different timings and needs its own analysis. Ratios do not prove statistical equivalence. Paired checkout ratios of 1.058-1.293 and hybrid-diff ratios of 1.088-1.112 show that historical absolute timings must not be advertised as repaired-code performance. Nested JSON, million-row workloads and independent Linux hardware were not benchmarked here.
