# Held-out operation-threshold supplement

This study supplements the original workflow experiments; it does not replace their frozen T=4,096 results. Trie geometry remains b=8,d=4 (4,096 possible buckets), independently of operation threshold T.

## Execution and evidence

Main bundle: `evidence/threshold-heldout-20261002`.

- Python 3.14.3, Windows 11 on the existing physical host. Environment/resource snapshot and exact archived source hashes are in `manifest.json`.
- Candidates: 1,024, 2,048, 4,096, 8,192, 16,384 operations.
- Operations: 512 through 32,768, seven powers-of-two points.
- Calibration: 10k/H4/spread, 100k/H16/spread, 10k/H64/repeated-key; seeds 20261003-20261005.
- Held-out validation: 100k/H4/repeated-key, 10k/H16/spread, 100k/H64/spread; seeds 20261006-20261008.
- Each point builds one durable repository. Forced log, forced Merkle and all five selectors share that repository, with shuffled query blocks, two warm-ups and seven measured queries per configuration.
- 42 repositories; 2,646 checked queries, including 2,058 measured queries. Repeated cached queries are not independent repository or dataset replications.
- Timing includes the version-pair API and canonical output materialization. A standalone ancestry/count probe outside the timer measures decision work; it is not subtracted to estimate causal selector overhead.
- Correctness includes a common semantic oracle, selected-path records, identity/reverse diffs, historical states, object hashes and verified reopen operations.
- Closed-file bytes and exact canonical payload sums by object kind are retained. Their difference includes indexes, hashes, metadata, page structure and free space; it is not pure metadata overhead. Both existing M and H retain changesets.

Selection minimizes the equally weighted mean of each calibration-case selector median divided by that case's faster forced-path median. An exact tie chooses the smaller T. The archived execution protocol writes `frozen_selection.json` before validation; per-case UTC timestamps were not recorded. The supplement is resumable and validates frozen source hashes. Working databases are removed after verification.

| T | Calibration score | Held-out score |
| ---: | ---: | ---: |
| 1,024 | 1.669139 | 1.902959 |
| 2,048 | 1.431591 | 1.554858 |
| 4,096 | 1.234427 | 1.297022 |
| 8,192 | 1.133296 | 1.148593 |
| 16,384 | 1.062401 | 1.032383 |

Calibration selected **16,384**, the largest candidate. These descriptive scores are not population confidence intervals. Forced log remains faster at every largest main-study count through 32,768; the winner therefore does not establish an optimal crossover.

## Separate diagnostic extension

`evidence/crossover-diagnostic-20261002` tests 10k rows/H256/repeated-key, seed 20261009, at 8,192, 16,384, 32,768, 65,536 and 131,072 operations. Five repositories, 315 checked queries, 245 measured. The extension is excluded from calibration and validation scores.

Log/Merkle median ratios are 0.443, 0.553, 1.108, 0.921 and 1.396 respectively. Merkle's first lower median at 32,768 reverses at 65,536; this is **not a resolved single cutoff**. IQRs and all raw queries are retained; only one seed was used.

## Reproduction

Use a fresh directory with Python 3.14 and the frozen source snapshot to reproduce timings:

```bash
python -m experiments.threshold_validation --output evidence/threshold-new-run
python -m experiments.crossover_extension --output evidence/crossover-new-run
python tools/check_final_paper.py
```

The first two commands measure new timings; the last checks the supplied artifacts/evidence. Pilot bundle `threshold-pilot-20261002` is excluded. Calibration/validation and diagnostic results are never pooled with original workflow, robustness, public-record recovery or WSL measurements. WSL is not independent hardware validation.

Reference metadata/access checks are retained in `REVISION_REFERENCE_VERIFICATION.json`; downloaded public source texts and local originality triage remain ignored under `output/docs/seven_revision_audit`. No private manuscript was uploaded, institutional similarity search performed, or detector score invented.
