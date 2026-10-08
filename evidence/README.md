# Audited research evidence

This directory contains the reviewed evidence used by the final Revon paper.
The 2026-10-08 manuscript uses the two Linux bundles below. They are also
packaged in Online Resource 1 with the manuscripts; local additions are not
claimed to be present in the historical public Git commit.

## Bundles

- `linux-final-supplement-20261008/` retains 27 isolated telemetry executions
  and 45 fresh-worker geometry executions (16 warm-ups and 56 measured trials
  combined). All passed correctness, including every historical state, after
  69 Linux tests passed. Cloud and local audits passed; geometry summaries
  were reproduced byte-for-byte. The corrected sampler preserves measured
  zero read bytes and keeps unavailable counters missing. Its core database
  sources match the first Linux bundle exactly. Timings are separate and are
  not pooled. See its `README.md` and `local-verification.json`.
- `linux-validation-20261008/` contains the additional GCP Ubuntu machine
  validation of the repaired source: 516 successful executions (114 warm-ups,
  399 measured trials and three million-row feasibility diagnostics), with 67
  Linux unit tests passing. Cloud and local integrity audits passed, and the
  paired summaries were reproduced exactly. The frozen protocol, executed
  source, public-data checksums and per-trial historical/diff verification are
  retained. Its fixed thresholds are 4,096 for the primary matrix and 16,384
  for the separate threshold supplement. The latter found a slower hybrid
  choice at 32,768 operations; it is not an optimal-threshold result. This is
  author-run validation on an additional machine, not independent-team
  reproduction or an OS-only causal comparison. Million-row rows are excluded
  from repeated performance comparisons. Historical Windows timings predate
  the JSON repair and remain separate evidence. See the bundle's `README.md`
  for the findings and complete limitations.
- `paper-final-20260824/` is the original 333-execution run (74 warm-ups,
  259 measured runs, of which 175 are primary evaluation runs). It is retained
  for provenance. Its Dolt `changed_keys` values came from the expected
  workload, and its Dolt `correctness=True` flags did not validate diff
  contents. Do not use those fields as Dolt observations.
- `paper-corrected-20260923/` reruns the first four review corrections with
  observed JSON Dolt diffs checked against the key/value oracle.
- `paper-corrected-issues5-12-externalrss-10ms-20260923/` refreshes all five
  systems under schema 3. It uses canonical diff and checkout outputs, stores
  Dolt commit hashes instead of creating timed tags, and externally samples
  isolated process-tree RSS at 10 ms. It is retained as the prior correction
  stage and is superseded for current paper claims by issues 13–17.
- `paper-corrected-issues13-17-counterbalanced-final-20260923/` is the historical
  schema-4, 540-execution Windows paper run. It separates SQL and Dolt bulk initial
  import, uses balanced randomized order across trials, adds three locality
  workloads, and reports normalized and post-compaction workflow storage. Its
  internal evidence-integrity audit passed with all 540 rows successful.
  Its `paired_ratio_uncertainty.csv` sidecar reports within-trial paired
  bootstrap intervals for initial import, incremental commit, diff, checkout,
  and SQL versus bulk import; intervals condition on each fixed scenario and
  one Windows host.
- `paper-issues18-20-robustness-20260923/` contains the separate Windows
  sensitivity run (405 rows, three seeds, seven measured repetitions) across
  payload, history, and update-pattern variants. Its seed-cluster bootstrap
  found the 50-commit comparison inconclusive.
- `paper-issues14-windows-telemetry-20260924/` is a separate Windows telemetry
  rerun of that 405-row robustness matrix. All rows have process-tree RSS, CPU,
  read/write bytes, and serial commit throughput; all 405 rows were correct and
  the schema-2 audit passed. Counters include setup and correctness work, not
  just timed database operations.
- `paper-issues18-20-linux-wsl-20260923/` contains a smaller WSL2 Ubuntu
  replication (180 rows, three measured repetitions) of the same 10,000-row
  variants, plus process-tree CPU/I/O counters and serial commit throughput
  where supported. WSL2 ran on the same physical computer as Windows. It is not
  an independent-machine replication, and its I/O counters are incomplete.
- The interrupted scratch attempts `paper-corrected-issues13-17-randomized-bulk-locality-20260923/`
  and `paper-corrected-issues13-17-counterbalanced-20260923/` have no complete
  audited result bundle and must not be cited. Use only the
  `...-counterbalanced-final-20260923/` bundle above.
- `trie-sensitivity-issues8-20260923/` is the corrected 45-execution
  branching-factor/depth sensitivity run. It uses the canonical diff output
  contract and backs Figure 6.
- `trie-sensitivity-20260824/` is retained as historical evidence. Its results
  use the prior output contract and are superseded by the corrected sensitivity
  run for current claims.

Re-run the internal evidence-integrity audit from the repository root:

```powershell
python -m experiments.evidence_audit evidence/paper-corrected-issues13-17-counterbalanced-final-20260923
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-robustness-20260923 --audit
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-linux-wsl-20260923 --audit
```

Unspecified new runs default to the ignored `output/` directory. The current
paper-profile run was written to its named bundle above and retained only after
its audit passed. The interrupted scratch-only attempt is listed separately and
must not be cited.
