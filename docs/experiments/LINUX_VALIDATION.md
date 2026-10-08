# Independent Linux machine validation

## Scope

This is a new, separate evaluation of the JSON-repaired source on a Google
Compute Engine N2 VM in us-east1-c: four vCPUs, 16 GB advertised RAM, Ubuntu
24.04.5 LTS, x86_64, 100 GB balanced Persistent Disk. Exact CPU, kernel,
interpreter build, SQLite, storage and environment records are captured in the
run manifest. It is an additional Linux machine validation by
the authors, not reproduction by an independent research team. Differences
from Windows include hardware, virtualization and storage; they cannot be
attributed solely to the operating system.

The latest core changes were uncommitted when transferred. The source bundle
therefore includes an exact file-hashed local snapshot and a `FROZEN_SOURCE.json`
record of the base commit and working-tree status. A GitHub clone alone would
not reproduce that snapshot. The campaign archives executed source separately.
Older Windows evidence and manuscript files are not overwritten by this runner.

## Premeasurement protocol

`experiments/linux_validation.py` writes the complete plan, workload digests,
environment and source hashes before the first timed trial. There is no
calibration or threshold selection in this campaign.

| Part | Cases | Systems | Threshold | Repetitions | Executions |
| --- | ---: | --- | ---: | --- | ---: |
| Original synthetic workflow matrix | 8 | Snapshot, Log-only, Revon-M, Revon-H, Dolt SQL, Dolt CSV | 4,096 | 2 warm-ups + 7 measured | 432 |
| Separate threshold supplement | 2 | forced log, forced Merkle, hybrid | 16,384 | 2 warm-ups + 7 measured | 54 |
| Public TLC workload, 100,000 records | 1 | Revon-M, Revon-H, Dolt SQL | 4,096 | 2 warm-ups + 7 measured | 27 |
| Public TLC feasibility, 1,000,000 records | 1 | Revon-M, Revon-H, Dolt SQL | 4,096 | 1 diagnostic, no warm-up | 3 |

Total planned: 516 executions = 114 warm-ups + 399 measured + 3 diagnostics.
Synthetic workloads retain their original evaluation seed (20260822 + 10000,
plus case offsets), including spread, lexical adjacency, sorted range,
repeated-key and hash-route locality. The threshold supplement uses 10,000-row
repeated-key workloads with 16 or 64 commits and 512 operations per commit,
on opposite sides of the frozen candidate. It does not prove an optimal
threshold. Within each case, all systems use the same generated history.

For public cases, the inherited `payload_bytes=8` workload parameter is unused
by the public-data builder. It does not mean taxi records are eight bytes.
Those values retain the prepared dataset fields; `logical_payload_bytes` is
calculated from the actual encoded final keys and values.

Model order is shuffled deterministically and rotated by repetition. For the
six-system original matrix, each model occupies every position once over the
first six measured trials; the seventh is an extra repetition. Every trial
uses a fresh repository and isolated process. The maximum duration is 900
seconds per trial and 10,800 seconds for the campaign. Failures remain in the
CSV and stop the run; incomplete matrices must not be called complete.

## Correctness, metrics and evidence

Each measured operation uses the existing common canonical output contract.
The harness compares observed initial/final states and changed keys with
old/new value hashes against the workload oracle. Every historical state is
also checked outside operation timers and its observed/oracle hashes retained.
The Linux unit-test gate additionally exercises JSON ownership/type changes,
incremental versus full rebuilding, persistence, close/reopen and integrity.

Initial import, incremental commit, diff, historical checkout, repository
bytes, normalized storage, external sampled process-tree RSS/CPU/I-O and
serial commit throughput are recorded. CPU/I-O totals include worker setup
and correctness work. All 516 retained rows contain RSS, CPU and write bytes.
Their read-byte cells are blank. The inherited sampler converts an all-zero
read aggregate to missing, which conflates zero activity with unavailable
counters. The retained bundle therefore supports no read-I/O comparison;
it would require a sampler correction and new telemetry measurements.
Revon is measured through its in-process API and Dolt through its CLI, including
SQL/parsing/process costs; this is not an engine-only comparison. First measured
trials in the evaluation phase include separate offline compaction measurements
where applicable. Threshold-supplement and diagnostic trials do not.

Raw rows are flushed and fsynced after each trial. The auditor checks the
frozen plan, source and public-data hashes, exact trial identities/order,
regenerated workload identity, fixed thresholds, chosen paths, historical and
diff verification hashes, storage arithmetic and recalculated summaries.
A real-worker preflight deliberately corrupts a trial matrix, diff-output
hash and threshold; each corruption must be rejected. This is an integrity
audit, not independent remeasurement of elapsed times.

Million-row trials are single-run feasibility observations and are excluded
from measured summaries and paired performance comparisons. All repeated
results remain conditional on one VM and fixed histories. Google Ops Agent
was active during preflight; the run manifest records its status and process
snapshot. User-space SSH access did not provide passwordless sudo to stop it.

## Reproduction on a new Linux VM

Start from the archived source snapshot for a particular evidence bundle.
The host needs x86_64 Linux, `curl`, `tar`, and Python 3 with working `venv`
support (Ubuntu's `python3-venv` package). Install user-space dependencies from
the repository's setup helper:

```bash
bash tools/setup_linux_validation.sh
export PATH="$HOME/revon-validation/bin:$PATH"
export PYTHONHASHSEED=20261008
PY="$HOME/revon-validation/venv/bin/python"
"$PY" -m unittest discover -s tests -v
```

Python is pinned to 3.14.3, psutil to 7.1.0, pyarrow to 25.0.1 and Dolt to 2.3.1.
The Linux Python is the GIL-enabled Astral managed build; compiler/build and
SQLite differences from Windows are recorded and are additional confounders.

Download the checksum-pinned TLC January 2024 file and prepare the public data:

```bash
mkdir -p data/public/linux-tlc
curl --fail --location --retry 3 \
  'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet' \
  --output data/public/linux-tlc/yellow_tripdata_2024-01.parquet
"$PY" -m experiments.public_dataset \
  --raw data/public/linux-tlc/yellow_tripdata_2024-01.parquet \
  --output data/public/linux-tlc/prepared
"$PY" -m experiments.linux_validation \
  --output evidence/linux-new-run \
  --dataset data/public/linux-tlc/prepared
"$PY" -m experiments.linux_validation \
  --output evidence/linux-new-run \
  --dataset data/public/linux-tlc/prepared --audit
```

Use a new output directory. Do not substitute a recalibrating paper-profile
command or overwrite retained evidence. Raw/prepared public data stay ignored;
retain their provenance, checksums, raw results, verification files, audit,
logs and source snapshot. Download and verify evidence before removing the VM.

## Run status

The 2026-10-08 run completed all 516 executions successfully: 114 warm-ups,
399 measured trials and three diagnostics. All 67 Linux unit tests and the
audit negative controls passed. Both the cloud audit and the second local
audit passed; the downloaded archive checksum matched, and the paired
bootstrap file was reproduced exactly. The retained result report is
[`evidence/linux-validation-20261008/README.md`](../../evidence/linux-validation-20261008/README.md).

The primary Revon-H versus Revon-M diff comparisons favored hybrid in eight
fixed scenarios; the medium-dense interval included parity. The threshold
supplement exposed a limitation: at 32,768 operations hybrid selected Merkle,
while forced log was faster in all seven matched trials (medians 40.520 ms log,
44.120 ms Merkle and 45.944 ms hybrid). Keep the frozen threshold and report
this failure to select the faster path; do not retune using this validation set.

The million-row observations passed correctness but contain one trial per
system. They support feasibility, not a performance ranking. This completion
does not establish publication readiness.

## Final manuscript integration and measurement supplement

The current IEEE and Discover Computing manuscripts now use the repaired-source
Linux campaign for their main workflow claims. The previous Windows threshold
calibration remains explicitly historical, with no pooling of measurements.

`evidence/linux-final-supplement-20261008/` adds 27 telemetry executions and 45
geometry executions. Its corrected sampler preserves observed zero reads;
unavailable I/O remains missing. The core database files are byte-identical to
the first Linux snapshot. All 69 Linux tests passed before supplement timing.
All 72 supplement executions passed, with 16 warm-ups and 56 measured trials.
Geometry runs use fresh workers and rotated configuration order, and check all
eleven historical states outside timers. Both cloud and second local audits
passed. The first preflight's missing fixture directory and its correction
are retained in the logs.

Use the archived supplement source and a new destination to reproduce:

```bash
mkdir -p tests/test_data
export PYTHONHASHSEED=20261008
python -m experiments.linux_final_supplement --output /path/to/new-supplement
python -m experiments.linux_final_supplement --output /path/to/new-supplement --audit
```

Online Resource 1 is `paper/Revon_Linux_Reproducibility_Supplement.zip`.
The corresponding author must review the final results and publisher-required
declarations before submission. Publication acceptance is not guaranteed by
an internal audit or completion of this protocol.
