# Linux geometry and telemetry supplement

This is a separate, frozen follow-up to `linux-validation-20261008`. It does
not replace or edit the first campaign. Both run on the same additional GCP
Ubuntu n2-standard-4 machine; exact environment and sources are in manifest.json.

## Completed protocol

- Telemetry: M, H and Dolt SQL, 10k rows, H10/C100, seed 20261008, T4096;
  2 warm-ups + 7 measured fresh-repository trials per system = 27 executions.
- Geometry: b4-d6, b8-d3, b8-d4, b8-d5 and b16-d3; 10k rows, H10/C100,
  32-byte synthetic values, seed 20260824, forced Merkle; 2 warm-ups + 7
  measured trials in fresh workers with rotating order = 45 executions.
- Total: 72 successful executions, including 16 warm-ups and 56 measured.
- Every execution checks all eleven historical states and endpoint diff
  outside operation timers. The geometry record retains the worker's boolean
  oracle result; the telemetry records additionally retain per-state hashes.
- All 69 Linux tests passed before timing. The initial preflight failed due
  to an absent empty tests/test_data directory in the transfer. The directory
  was created, the full suite rerun, and only then did measurement begin.
  Both logs are retained; no failed timing execution was excluded.

## Source and counter interpretation

The database files versioned_db.py and sqlite_store.py are byte-identical to
the first campaign. The measurement harness now records zero read/write bytes
when counters were available, and None only when no I/O sample was available.
The 27 telemetry executions all observed zero physical read bytes; this is
compatible with filesystem caching and is not proof of zero logical reads.
Ten-millisecond process sampling may miss short-lived child processes.
CPU/I/O/RSS span setup, timings and verification, not individual operations.
Geometry monitor peaks are not comparable with external process-tree RSS.

No threshold was tuned here. The first campaign's adverse T16384 result at
32768 operations remains reported. One fixed geometry workload does not
establish a generally optimal branching factor or depth.

## Audit and reproduction

Cloud audits and the separate downloaded local audit passed. The local check
reproduces geometry summaries byte-for-byte and checks every geometry JSON
against the raw row. SHA256SUMS.json covers the collected experiment files;
README and local-verification were added after download and are not included
in that collection-time manifest. Audits are internal consistency checks,
not independent timing reproduction.

When rerunning the archived auditors, work on a disposable copy of the evidence:
they rewrite audit.json, and Windows text output can change LF to CRLF without
changing the JSON values. The repository's tools/verify_linux_final.py now
audits a temporary copy and checks that the collected file hashes remain intact.
The two audit records were restored byte-for-byte from the checksum-pinned cloud
archive after confirming their JSON values were identical. Raw observations,
source snapshots, protocols and conclusions were unchanged.

Use the pinned environment setup supplied with the first campaign, then:

```bash
cd source
mkdir -p tests/test_data
export PYTHONHASHSEED=20261008
python -m unittest discover -s tests -v
python -m experiments.linux_final_supplement --output /path/to/new-output
python -m experiments.linux_final_supplement --output /path/to/new-output --audit
```

Use a new output directory. Preserve both source snapshots and never merge
these timing rows into the first campaign's summaries.
