# Public dataset evaluation

This study addresses Comment 1 only. It evaluates structured key/value versioning over public NYC TLC yellow-taxi trip records from January 2024. Monthly files contain different trips, not successive states of the same trips; the experiment therefore uses **synthetic update histories over public records**.

## Acquisition and terms

- Authoritative landing page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- January 2024 file: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- SHA-256: `c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510`
- Source file: 49,961,641 bytes; 2,964,624 physical records.
- Dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf
- Usage: NYC Open Data's FAQ states unrestricted use. The AWS dataset registry points to NYC terms. These are the documented terms, not an invented Creative Commons license. https://www.nyc.gov/opendata/get-started/FAQs ; https://registry.opendata.aws/nyc-tlc-trip-records-pds/ ; https://www.nyc.gov/main/terms-of-use
- Raw and prepared records remain local under ignored `data/public/`. Repository evidence contains metadata, digests, timings and verification hashes, not redistributed trip records.

Download in PowerShell:

```powershell
New-Item -ItemType Directory -Force data/public/nyc-tlc-2024-01
Invoke-WebRequest https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet -OutFile data/public/nyc-tlc-2024-01/yellow_tripdata_2024-01.parquet
```

The retained evaluation uses Python 3.12.14, pyarrow 25.0.1 and psutil 7.2.2. Install the dataset dependencies in a dedicated environment with `python -m pip install -r experiments/requirements-public-dataset.txt`. The benchmark otherwise uses Python standard-library modules; publication rendering has separate repository dependencies. Preparation rejects any file whose checksum differs; a publisher replacement requires an explicit new study, not silently reusing this evidence.

```bash
python -m experiments.public_dataset --raw data/public/nyc-tlc-2024-01/yellow_tripdata_2024-01.parquet --output data/public/nyc-tlc-2024-01
```

## Record mapping and subsets

Eleven original fields survive: vendor ID, pickup/drop-off timestamps, passenger count, distance, pickup/drop-off location IDs, payment type, fare, tip, and total. Values use the adapters' sorted-key compact UTF-8 JSON convention. Source timestamps retain their timezone-free ISO representation. Missing values and nonfinite numbers become JSON null; invalid domain values such as negative fares are retained, because this is a storage experiment, not an estimation of taxi activity. All 1,000,000 selected records serialize successfully; 47,277 passenger counts are null. No other retained field is null in this selected set.

Keys combine the month, the first 16 hex digits of the file checksum, and the zero-based physical row ordinal. Keys identify rows within this frozen file, not trips across months or reissued files. Duplicate field values remain distinct records; ordinal construction prevents identifier collisions.

With seed 20261001, rank `r` maps to source ordinal `(996110 + r * 1344731) mod 2964624`. The stride is coprime with the record count, so this is a bijection. The first N ranks define nested 10,000 / 100,000 / 1,000,000 record subsets. This dispersed affine sample is **not** a uniformly random permutation and must not be described as one. The prepared JSONL is written in source-file order and has SHA-256 `6608b7680e82432ca22f90a71d4994676ffd290c4fc85f17f91fab03d4c7b661`.

## Workloads and measurement contract

| Sweep | Records | Commits | Changes per commit | Density |
|---|---:|---:|---:|---:|
| Scale | 10,000 | 10 | 10 | 0.1% |
| Scale and baseline | 100,000 | 10 | 100 | 0.1% |
| Scale | 1,000,000 | 10 | 1,000 | 0.1% |
| History | 100,000 | 50 | 100 | 0.1% |
| Density | 100,000 | 10 | 10 | 0.01% |
| Density | 100,000 | 10 | 1,000 | 1% |

The overlapping 100k baseline is executed once. Each commit samples distinct existing keys using Python Random(20261001); records may repeat across commits. Each selected fare and total is increased by 0.01 and rounded to two decimal places. This models generated corrections, not observed taxi revisions. Record count stays fixed; these public workloads test updates only, unlike the earlier mixed synthetic workloads.

Every system receives identical starting records and mutations. Existing Snapshot, Log-only, Revon-M, Revon-H, Dolt SQL and Dolt CSV-import adapters are reused. Revon uses b=8, d=4 and the frozen 4096-operation threshold. Initial import is timed separately. Each trial's incremental-commit statistic is the median of its H commit intervals; diff compares initial version 1 with final version H+1. Diff and checkout materialize the existing canonical output contracts. Every trial checks both endpoint states and the semantic initial/final diff against the same oracle outside timing. The first measured trial per system/configuration also checks all historical versions; later trials avoid redundant full-history scans.

Each trial is a fresh isolated worker. External process-tree RSS/CPU/I/O sampling occurs every 10 ms. Storage is the complete repository directory after operations and verification, before close or compaction. The reused harness also retains separate offline-compaction measurements for the first measured trial of Revon and Dolt configurations; those values are not the footprints plotted in this extension. Preparation, workload generation, correctness checks and cleanup are excluded from operation latency. Whole-worker memory includes the workload oracle and untimed checks. Real values have variable lengths; public TrialRecord `payload_bytes` is null (empty in CSV), because there is no fixed payload length. The internal WorkloadSpec value 8 is only a validation placeholder. Use `logical_payload_bytes` for the measured UTF-8 size.

## Running and auditing

The pilot uses one measured execution per configuration, no warm-ups. Its results select feasible repetitions; pilot points must not be pooled with repeated measurements. The standard protocol is two warm-ups and seven measured trials per configuration. Any resource-driven deviation must be recorded beside the resulting evidence and in the paper. Each worker has a 900-second wall-clock limit, including setup and verification; failures remain in raw evidence.

```bash
python -m experiments.public_dataset_study --output evidence/public-tlc-pilot-20261001 --scenarios tlc-n10000-h10-c10 --warmups 0 --trials 1
python -m experiments.public_dataset_study --output evidence/public-tlc-evaluation-20261001 --mode evaluation
python -m experiments.public_dataset_study --output evidence/public-tlc-evaluation-20261001 --audit
```

The runner resumes completed trials only with identical manifest settings. `trials.jsonl` preserves typed raw results; `raw_results.csv` supports analysis; `elapsed.jsonl` records wall duration; `summary.csv` reports medians and linearly interpolated 25th/75th percentiles across measured trials. Per-trial `verification/` files retain historical-state oracle/output hashes, semantic-diff output hashes, changed-key counts, and all commit intervals. The independent audit checks matrix coverage, uniqueness, workload digests, threshold, correctness, verification coverage, and reproduces summary statistics. Failures are explicitly listed even when evidence consistency passes.

### Interrupted trial and recovery

The initial matrix retained 324 attempts, including one interrupted million-record Revon-M measured trial. Its raw error and unusually long worker intervals are preserved in `evidence/public-tlc-evaluation-20261001/interruption.json` and `interrupted_worker_verification/`; its timings are excluded. This is not evidence of an algorithmic scale limit. One fresh recovery execution follows the completed matrix, with the same frozen source, dataset, workload and packages. It has no additional warm-up; the original two warm-ups remain. The recovery is outside the original counterbalanced block, and host conditions were not held constant.

```bash
python -m experiments.public_dataset_study --output evidence/public-tlc-recovery-20261002 --scenarios tlc-n1000000-h10-c1000 --models revon-m --warmups 0 --trials 1 --mode evaluation
python tools/combine_public_dataset_evidence.py --evidence evidence/public-tlc-evaluation-20261001 evidence/public-tlc-recovery-20261002 --output evidence/public-tlc-combined-20261002
python tools/verify_public_dataset_source.py --evidence evidence/public-tlc-combined-20261002
```

These recovery/pooling commands describe this retained interruption. A fresh uninterrupted matrix already has seven successful measured trials per configuration and needs no recovery; audit and integrate its original execution bundle directly. To reproduce the exact recorded execution version, overlay the eight files under the original bundle's `source/` onto a separate checkout before running. The manifest records their exact hashes and the actual package versions.

Pooling preserves both source bundles and the failed original row. Run IDs distinguish the recovery from the original trial. The analysis independently checks its medians/IQRs and requires exactly seven successful measured repetitions for all 36 configurations. No failed timing is recovered or imputed.

## Boundaries

This adds public record contents and measured scale. It does not evaluate observed change histories, multiple public datasets, relational queries, multiple tables, schema evolution, branches, concurrency, independent hardware, or a new selector threshold. It does not justify engine-only or production-superiority claims.

After the original and recovery executions finished, timeout cleanup was hardened against a worker that has already exited, and failed worker reports are now quarantined automatically. These changes affect failure handling, not successful timed operations. Both execution bundles retain the exact earlier source and its hashes; the pooled manifest records those execution sources. A regression test covers the observed missing-worker cleanup case.
