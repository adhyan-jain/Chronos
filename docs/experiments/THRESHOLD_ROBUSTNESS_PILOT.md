# Exploratory threshold robustness pilot

This is new exploratory evidence, separate from the original T=4,096 workflow
matrix, the five-candidate calibration/held-out study (selected T=16,384), and
the earlier one-seed crossover diagnostic. No production threshold changes.

## Protocol and coverage

Frozen manifest: `evidence/threshold-robustness-pilot-20261002/manifest.json`.
Three seeds (20261021-20261023), two profiles (10k/H256/repeated-key and
100k/H64/spread), operation counts 32,768/65,536/131,072, forced log and Merkle,
and hybrid thresholds 4,096/16,384/32,768/65,536/131,072. Each independent
repository has two warm-up and five measured randomized blocks. The 65,536
subset also has three separately reopened process blocks per configuration.

A predeclared resource gate, applied after the first case before latency
inspection, reduced 18 planned cases to nine repeated-key and three spread
cases at 65,536. Six spread cases were not run, not failed. Twelve repositories
completed: 588 warmed queries (168 warm-ups, 420 measured) and 126 fresh-process
measured queries, totalling 714 timed and 546 measured queries. All semantic,
reverse/identity, representative historical-state, integrity and reopen checks
passed. Completed cases took 28.3 minutes and peaked at 1,214 MiB sampled RSS.

## Findings and limits

All three seeds favour log at 32,768 repeated-key operations, Merkle at 65,536
and 131,072 repeated-key operations, and log at 65,536 spread operations. The
earlier one-seed reversal is not reproduced; old measurements remain intact.
Profiles differ in rows and history as well as locality, so this comparison
does not isolate locality. Raising T to 131,072 helps spread medians but harms
larger repeated-key medians. No optimal threshold or new validated selector
is established. Three histories are not a population-level confidence study.

Reopen eagerly verifies/loads all objects. OS cache is not cleared; open time
is separate. Warmed Python hash seeds equal workload seed; fresh hash seeds
equal seed plus block. Both paths share a seed within each fresh block, but
between-condition changes do not isolate caching. Same-path timing variation
is large. Actual mutations are one insert and one delete per commit, with
remaining operations updates; the legacy generator docstring's 80/10/10 mix
does not describe the implementation. Production code remains unchanged.

## Evidence and reproduction

The bundle copies completed run `20261002-132649` byte-for-byte, including
archived sources, raw queries, summaries, all seed ratios and result checks.
`publication_inventory.json` pins copied files. The original manifest remains
unmodified. Historical protected-file audits apply at the end of the isolated
pilot, before the subsequently authorized manuscript revision. They are not
claims that the revised manuscript still has its pre-pilot hash. Public release
is pending until these local additions are committed and pushed.

Run from the repository root in PowerShell with Python 3.14 and psutil 7.1.0:

```powershell
$pilotOutput = '.codex_tmp/threshold_robustness_pilot/reproduction-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
& 'C:/Python314/python.exe' evidence/threshold-robustness-pilot-20261002/prepare_reproduction.py --output $pilotOutput
& 'C:/Python314/python.exe' -m experiments.threshold_robustness_pilot --output $pilotOutput
python -m experiments.analyze_threshold_robustness_pilot --output $pilotOutput
```

Use the bundled Python plus plotting dependencies for the final analysis if
the measurement interpreter lacks matplotlib. Measurements include common
canonical output; decision probes and correctness checks are outside timing.
Working databases are removed after verified reopen checks. Independent Linux
hardware validation remains pending. A follow-up should control rows/history,
fix hash seeds across process conditions, and use new calibration/validation
seeds before adopting a different selector.
