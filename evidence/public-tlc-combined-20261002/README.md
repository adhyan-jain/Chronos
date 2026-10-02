# Public TLC analysis bundle

Comment 1 evaluation of January 2024 NYC TLC yellow-taxi records, using eleven retained fields and deterministic generated correction histories. This is a pooled analysis bundle, not a separate benchmark execution.

- Six workloads cover nested 10k/100k/1M scale, 10/50-commit history, and 0.01%/0.1%/1% update density.
- Six workflows per workload; 36 configurations, each with two original warm-ups and seven successful measured trials.
- 325 retained attempts: 72 successful warm-ups, 252 successful measured executions, and one interrupted failed attempt. Its unusable timings are excluded, never imputed.
- One fresh recovery execution followed the completed matrix outside its counterbalanced block. Host memory was not held constant. See manifest.json for the recovery policy and source execution bundles.

## Retained records

raw_results.csv and trials.jsonl preserve pooled rows with execution run IDs. summary.csv contains independently checked medians and linearly interpolated IQRs. elapsed.jsonl retains wall durations. figures/ contains the paper plot assets and exact plotted values.

manifest.json points to public-tlc-evaluation-20261001 and public-tlc-recovery-20261002. Those execution bundles retain the exact eight source files, their hashes, per-trial historical-state and diff verification, and commit intervals. The original bundle also retains source_verification.json, interruption.json and the quarantined interrupted worker report. Pilot bundles are separate and are not pooled.

evidence_audit.json passes matrix, correctness, digest, verification and summary checks. independent_source_verification.json independently traces all one million prepared rows to Parquet, regenerates workloads and checks 1,221 successful state-hash comparisons. paper_verification.json records numerical, citation, original-figure preservation, pagination and visual checks across all 49 final PDF pages.

## Reproduction and interpretation

See docs/experiments/PUBLIC_DATASET_EVALUATION.md for source terms, checksums, preparation and execution commands; docs/experiments/PUBLIC_DATASET_RESULTS.md for the full results and paper changes. Raw and prepared records are downloaded locally and ignored by Git. A fresh uninterrupted matrix needs no recovery or pooling step.

These are whole-system workflow measurements on one host, one monthly file and one affine sample. Histories are generated, not observed. IQRs describe repetitions of these fixed workloads. The million-record results expose expensive Revon commits and storage; they do not establish general superiority or isolate tree algorithms.
