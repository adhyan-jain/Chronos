# Revon: additional Linux machine validation

## Result

The frozen campaign completed 516 of 516 planned executions: 114 warm-ups, 399 measured trials and 3 diagnostics. All 516 executions passed the harness correctness checks. The evidence-integrity audit passed.

This closes the additional-Linux-machine experiment for the bounded protocol below. It does not establish publication readiness, independent-team reproduction, a universal winning threshold, or a causal performance effect of Linux.

## Environment and provenance

- GCP machine: `n2-standard-4`, zone `us-east1-c`, CPU platform `Intel Cascade Lake`.
- Four vCPUs (two virtual cores with two threads each), 16 GB advertised memory, 100 GB balanced Persistent Disk.
- Ubuntu 24.04.5 LTS, x86_64; exact kernel, CPU, compiler/build and disk information are in `manifest.json`.
- Python 3.14.3 (Astral managed GIL build), SQLite 3.50.4, Dolt 2.3.1, psutil 7.1.0, pyarrow 25.0.1.
- Executed repaired core, benchmark, test, example and API source is retained in `source/`; source hashes and base-commit/dirty-status provenance are retained. Manuscripts and Git metadata are excluded.
- Original Windows measurements predate the JSON repair. This campaign is separate evidence and does not replace their absolute timings.
- Google Ops Agent was active. Its status and premeasurement process snapshot are recorded; the machine was not stripped of all background services.

## Protocol

- Original eight synthetic scenarios: all six workflow variants, frozen T=4,096, two warm-ups and seven measured fresh-repository trials.
- Threshold supplement: two separate 10k repeated-key histories (8,192 and 32,768 operations), forced log/Merkle/hybrid, frozen T=16,384.
- Public TLC: 100k records, Revon-M/Revon-H/Dolt, two warm-ups and seven measured trials. Fare-correction histories are generated, not naturally observed revisions.
- Public TLC scale: 1M records, one diagnostic trial per Revon-M/Revon-H/Dolt. Excluded from comparative summaries and paired intervals.
- The public-case `payload_bytes=8` spec parameter is inherited and unused by the public-data builder. Taxi values retain the prepared fields; `logical_payload_bytes` records their actual encoded size.
- No cloud-side calibration. Model order was shuffled deterministically and rotated across repetitions. All six positions are covered in the first six primary measured repetitions.
- Every historical state and observed endpoint/diff contract was checked. Historical verification and compaction are outside operation timers.
- Trials include external process-tree telemetry; CPU/I-O totals include setup and correctness. All 516 rows contain RSS, CPU and write bytes. All read-byte cells are blank: the inherited sampler converts an all-zero read aggregate to missing, so these records cannot distinguish zero activity from unavailable counters. Do not use them for read-I/O comparisons.

## Descriptive diff medians

These are milliseconds for the API/CLI workflow. A lower median is specific to this workload and machine; use the paired interval file for uncertainty. Dolt CLI costs include process startup, SQL and parsing.

| Scenario | Revon-H | Revon-M | Dolt SQL |
| --- | ---: | ---: | ---: |
| large-application-key-local | 31.967 | 47.253 | 125.594 |
| large-hash-route-local | 1.503 | 1.817 | 110.966 |
| large-range-local | 34.537 | 54.352 | 135.765 |
| large-repeated-key | 1.345 | 6.862 | 97.451 |
| large-sparse | 35.749 | 54.897 | 152.472 |
| linux-tlc-n100000-h10-c100 | 41.964 | 60.597 | 168.576 |
| medium-dense | 64.183 | 64.135 | 297.617 |
| medium-sparse | 0.629 | 1.620 | 95.515 |
| small-sparse | 0.604 | 1.259 | 90.704 |

## Paired Revon-H versus Revon-M ablation

Ratios are Merkle/hybrid diff latency. Values above one favor hybrid; the interval is a paired percentile bootstrap of the median of seven trial ratios. It describes repeated timings for this fixed history, not uncertainty across machines or datasets.

| Scenario | Median ratio | 95% interval | Finding |
| --- | ---: | --- | --- |
| large-application-key-local | 1.47818 | [1.37836, 1.60356] | Revon-H faster by a practically relevant margin |
| large-hash-route-local | 1.18692 | [1.16543, 1.23328] | Revon-H faster by a practically relevant margin |
| large-range-local | 1.59618 | [1.49519, 1.79594] | Revon-H faster by a practically relevant margin |
| large-repeated-key | 5.13368 | [5.02283, 5.35064] | Revon-H faster by a practically relevant margin |
| large-sparse | 1.53795 | [1.34393, 1.66874] | Revon-H faster by a practically relevant margin |
| linux-tlc-n100000-h10-c100 | 1.444 | [1.39126, 1.50349] | Revon-H faster by a practically relevant margin |
| medium-dense | 0.988177 | [0.970353, 1.05783] | inconclusive: interval includes parity |
| medium-sparse | 2.50868 | [2.43949, 2.57381] | Revon-H faster by a practically relevant margin |
| small-sparse | 2.05338 | [1.97457, 3.13628] | Revon-H faster by a practically relevant margin |

## Frozen-threshold supplement

| Scenario | Forced log (ms) | Forced Merkle (ms) | Hybrid (ms) | Hybrid path |
| --- | ---: | ---: | ---: | --- |
| linux-threshold-h16-c512 | 16.364 | 24.466 | 17.926 | log |
| linux-threshold-h64-c512 | 40.520 | 44.120 | 45.944 | merkle |

The inherited display name "Revon-log calibration" denotes the forced-log adapter here. No threshold was calibrated in this campaign. These two cases test the frozen candidate and selected paths; they do not resolve the crossover globally.

**Observed selector limitation:** at 32,768 operations, hybrid selected Merkle, but forced log was faster in all seven matched measured trials. The diff medians were 40.520 ms for forced log, 44.120 ms for forced Merkle and 45.944 ms for hybrid. Thus the frozen threshold picked a slower path on this fixed history. This is a limitation to retain in the paper, not grounds for retuning on these validation results.

## Million-row feasibility observations

| System | Initial import (s) | Commit median (ms) | Diff (ms) | Checkout (s) | Peak sampled RSS (GiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Revon-H | 32.289 | 2961.901 | 1233.601 | 4.729 | 2.561 |
| Dolt | 24.902 | 547.311 | 817.034 | 11.454 | 2.555 |
| Revon-M (forced Merkle) | 32.454 | 2979.717 | 1265.367 | 4.685 | 2.561 |

**One trial per system is feasibility evidence, not a reliable performance ranking or uncertainty estimate.**

In these individual observations, Dolt had lower import, commit and diff times; Revon had lower checkout time. Repeated scale trials are required before making comparative performance claims.

## Reproduce or audit

The complete protocol is in `protocol.json`. The user-space dependency helper is retained in `reproduction/setup_linux_validation.sh`; it was packaged after the run and is not part of the executed source manifest. It requires Linux x86_64, `curl`, `tar`, and system Python with `venv` support.

For a new run, use `source/` as the working directory and a new evidence destination. Prepare the checksum-pinned TLC file with `experiments.public_dataset`. For an integrity audit of this download, pass its prepared-data directory with matching `dataset.json` and `records.jsonl`:

```bash
cd source
python -m experiments.linux_validation --output .. --dataset /path/to/prepared-tlc --audit
```

## Checks and retained files

- Linux regression gate: 67 tests passed, including SQLite reopen, integrity, incremental/full rebuild and JSON type/ownership checks.
- Small real-worker audit gate rejected missing trial rows, corrupted observed diff hashes and altered frozen thresholds.
- A first transfer omitted example/API modules; its unit-test failures were retained in local preflight logs and the package was corrected before any campaign measurements.
- Cloud and downloaded archive checksums matched. A second local audit regenerated the histories against the archived source and prepared public dataset.
- `protocol.json`, `manifest.json`, `raw_results.csv`, `summary.csv`, `paired_uncertainty.csv`, `verification/`, `audit.json`, `completed.json`, source and successful preflight records are retained.
- Integrity audits verify accounting, outputs and summaries; they do not reproduce raw elapsed times.

## Limits and manuscript use

Report this as an additional author-run Linux cloud validation of repaired Revon. Keep source versions, threshold studies and one-million-row diagnostics distinct from the historical Windows campaign. Do not claim that all operating systems, production workloads or independent hosts will reproduce these medians. Do not claim a universally optimal threshold or broad engine-level superiority over Dolt. A new manuscript revision must cite this evidence and preserve these limits.
