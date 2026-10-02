# Comment 1 public dataset results

This report covers the public dataset, scale, history and update-density evaluation. It does not close the other seven comments in the supervisor's review.

## Dataset and preparation

NYC TLC yellow-taxi trip records, January 2024: 2,964,624 source rows and 1,000,000 retained rows with eleven original fields. Keys identify source-file rows through release/checksum/ordinal, rather than asserting a natural trip identifier. Nested affine subsets share a fixed sampling seed. Missing values remain null, anomalous domain values survive, and duplicate field contents retain separate row identities. Histories are generated corrections to fare and total, not observed revisions.

Authoritative source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Download SHA-256: `c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510`. Prepared JSONL SHA-256: `6608b7680e82432ca22f90a71d4994676ffd290c4fc85f17f91fab03d4c7b661`.

## Completed matrix

325 executions; 324 successful; 1 failed/unavailable. Each configuration schedules 2 warm-ups and 7 measured trials; the table gives successful measured-trial counts. Pilot timings are excluded. Every successful trial checks both endpoint states and semantic diff. The first measured trial per system/configuration checks all historical versions; the retained verification reports contain 1221 state-hash comparisons in total.

| Scenario | Rows | Incremental commits | Changed records per commit | Update density | Diff endpoints |
|---|---:|---:|---:|---:|---|
| tlc-n10000-h10-c10 | 10,000 | 10 | 10 | 0.1% | 1 to 11 |
| tlc-n100000-h10-c100 | 100,000 | 10 | 100 | 0.1% | 1 to 11 |
| tlc-n1000000-h10-c1000 | 1,000,000 | 10 | 1,000 | 0.1% | 1 to 11 |
| tlc-n100000-h50-c100 | 100,000 | 50 | 100 | 0.1% | 1 to 51 |
| tlc-n100000-h10-c10 | 100,000 | 10 | 10 | 0.01% | 1 to 11 |
| tlc-n100000-h10-c1000 | 100,000 | 10 | 1,000 | 1% | 1 to 11 |

Systems: Snapshot, Log-only, forced-Merkle Revon-M, Revon-H, Dolt SQL import and Dolt CSV import. The two Dolt workflows use the same engine for subsequent operations. Revon remains at b=8, d=4 and threshold 4096.

## Measured results and uncertainty

All values below are median [25th percentile, 75th percentile] across measured trials. Each trial's incremental-commit value is itself the median of the timed commit intervals. These IQRs describe fixed-workload repetition on this host; they are not confidence intervals across datasets or machines. Storage is the whole directory before compaction. Import and incremental commit are separate operations.

| Scenario | System | n | Import ms | Incremental commit ms | Diff ms | Repository MiB |
|---|---|---:|---:|---:|---:|---:|
| tlc-n10000-h10-c10 | Dolt | 7 | 1082.38 [976.61, 1252.15] | 1045.28 [960.81, 1102.97] | 362.10 [259.60, 387.60] | 1.39 [1.39, 1.39] |
| tlc-n10000-h10-c10 | Dolt (bulk import) | 7 | 1228.03 [1121.35, 1387.58] | 1068.63 [861.24, 1160.84] | 399.23 [338.77, 425.25] | 1.35 [1.35, 1.35] |
| tlc-n10000-h10-c10 | Log-only | 7 | 35.32 [33.15, 40.88] | 2.85 [2.73, 3.16] | 19.44 [13.34, 23.05] | 3.29 [3.29, 3.29] |
| tlc-n10000-h10-c10 | Revon-H | 7 | 314.49 [287.98, 342.22] | 18.72 [18.60, 21.78] | 0.61 [0.57, 0.67] | 14.56 [14.56, 14.57] |
| tlc-n10000-h10-c10 | Revon-M (forced Merkle) | 7 | 279.47 [259.23, 341.60] | 19.48 [18.32, 23.01] | 1.27 [1.23, 1.47] | 14.57 [14.56, 14.57] |
| tlc-n10000-h10-c10 | Snapshot | 7 | 31.67 [26.17, 32.86] | 25.81 [23.18, 31.41] | 135.43 [130.81, 168.92] | 35.49 [35.49, 35.49] |
| tlc-n100000-h10-c10 | Dolt | 7 | 3104.56 [2917.15, 3153.15] | 1001.47 [961.31, 1054.84] | 374.25 [301.90, 393.64] | 10.85 [10.85, 10.85] |
| tlc-n100000-h10-c10 | Dolt (bulk import) | 7 | 3135.54 [3079.87, 3446.76] | 1015.52 [959.11, 1037.56] | 367.27 [360.61, 412.92] | 10.30 [10.30, 10.30] |
| tlc-n100000-h10-c10 | Log-only | 7 | 258.70 [248.35, 262.44] | 3.00 [2.83, 3.22] | 21.38 [19.69, 22.74] | 32.33 [32.33, 32.33] |
| tlc-n100000-h10-c10 | Revon-H | 7 | 2442.24 [2397.60, 2691.04] | 28.56 [28.16, 33.37] | 0.78 [0.72, 0.85] | 79.68 [79.68, 79.69] |
| tlc-n100000-h10-c10 | Revon-M (forced Merkle) | 7 | 2412.06 [2263.57, 2531.63] | 26.57 [26.04, 28.77] | 2.78 [2.50, 3.16] | 79.68 [79.68, 79.69] |
| tlc-n100000-h10-c10 | Snapshot | 7 | 232.36 [231.08, 257.33] | 236.94 [230.06, 241.25] | 1257.26 [1209.89, 1293.60] | 354.90 [354.90, 354.90] |
| tlc-n100000-h10-c100 | Dolt | 7 | 2932.48 [2737.23, 3261.14] | 749.08 [713.50, 836.40] | 329.10 [321.29, 330.90] | 13.50 [13.50, 13.50] |
| tlc-n100000-h10-c100 | Dolt (bulk import) | 7 | 3022.74 [2967.26, 3202.64] | 716.78 [705.92, 968.04] | 327.17 [301.65, 450.04] | 12.95 [12.95, 12.95] |
| tlc-n100000-h10-c100 | Log-only | 7 | 255.47 [231.10, 276.16] | 4.11 [4.09, 4.33] | 29.62 [24.95, 30.67] | 32.93 [32.93, 32.93] |
| tlc-n100000-h10-c100 | Revon-H | 7 | 2989.85 [2895.31, 3513.79] | 161.09 [131.22, 252.49] | 8.65 [8.54, 10.28] | 90.04 [90.02, 90.05] |
| tlc-n100000-h10-c100 | Revon-M (forced Merkle) | 7 | 3060.07 [2908.72, 3091.05] | 202.78 [177.20, 244.32] | 25.95 [25.74, 32.02] | 90.03 [90.02, 90.04] |
| tlc-n100000-h10-c100 | Snapshot | 7 | 205.60 [190.58, 258.26] | 257.41 [254.07, 260.59] | 1584.12 [1551.42, 1692.86] | 354.91 [354.91, 354.91] |
| tlc-n100000-h10-c1000 | Dolt | 7 | 3020.40 [2691.60, 3419.05] | 943.05 [858.58, 1032.88] | 740.59 [593.15, 804.08] | 25.31 [25.31, 25.31] |
| tlc-n100000-h10-c1000 | Dolt (bulk import) | 7 | 2820.52 [2463.27, 3062.24] | 976.99 [896.15, 1088.49] | 702.91 [678.42, 764.23] | 24.75 [24.75, 24.75] |
| tlc-n100000-h10-c1000 | Log-only | 7 | 270.46 [210.60, 297.52] | 11.04 [10.85, 11.85] | 146.20 [141.44, 155.57] | 38.90 [38.90, 38.90] |
| tlc-n100000-h10-c1000 | Revon-H | 7 | 2961.99 [2893.83, 3313.49] | 679.38 [637.29, 784.68] | 166.75 [149.23, 181.91] | 177.66 [177.65, 177.77] |
| tlc-n100000-h10-c1000 | Revon-M (forced Merkle) | 7 | 3005.45 [2928.90, 3070.31] | 752.02 [663.37, 887.75] | 164.79 [153.96, 218.70] | 177.68 [177.63, 177.69] |
| tlc-n100000-h10-c1000 | Snapshot | 7 | 257.56 [213.42, 277.36] | 265.73 [227.22, 275.99] | 1738.57 [1464.95, 1833.36] | 354.97 [354.97, 354.97] |
| tlc-n100000-h50-c100 | Dolt | 7 | 2789.25 [2757.11, 2973.81] | 882.14 [859.80, 968.41] | 590.91 [554.77, 683.54] | 25.88 [25.88, 25.88] |
| tlc-n100000-h50-c100 | Dolt (bulk import) | 7 | 2937.69 [2608.48, 3099.51] | 873.70 [860.46, 981.66] | 525.45 [496.60, 535.66] | 25.33 [25.33, 25.33] |
| tlc-n100000-h50-c100 | Log-only | 7 | 227.01 [223.30, 242.22] | 3.26 [3.20, 3.42] | 52.11 [50.53, 60.70] | 35.58 [35.58, 35.58] |
| tlc-n100000-h50-c100 | Revon-H | 7 | 2177.15 [2086.43, 2290.86] | 141.22 [135.22, 144.18] | 91.79 [82.20, 97.15] | 137.24 [137.22, 137.27] |
| tlc-n100000-h50-c100 | Revon-M (forced Merkle) | 7 | 2275.67 [2194.56, 2424.93] | 135.36 [128.09, 141.45] | 83.68 [83.54, 95.00] | 137.24 [137.23, 137.25] |
| tlc-n100000-h50-c100 | Snapshot | 7 | 234.18 [224.47, 247.44] | 219.28 [218.15, 253.28] | 1377.48 [1252.46, 1460.05] | 1645.60 [1645.60, 1645.60] |
| tlc-n1000000-h10-c1000 | Dolt | 7 | 29022.95 [20931.34, 37704.65] | 1175.64 [931.21, 1297.20] | 1068.97 [835.76, 1242.86] | 132.76 [132.76, 132.76] |
| tlc-n1000000-h10-c1000 | Dolt (bulk import) | 7 | 24935.34 [20111.50, 27287.45] | 937.17 [884.30, 1014.26] | 1009.29 [805.13, 1090.23] | 126.91 [126.91, 126.91] |
| tlc-n1000000-h10-c1000 | Log-only | 7 | 2415.54 [2066.29, 2913.10] | 10.84 [8.63, 12.59] | 148.16 [98.22, 150.74] | 329.27 [329.27, 329.27] |
| tlc-n1000000-h10-c1000 | Revon-H | 7 | 39596.67 [27543.38, 41406.98] | 4764.26 [3086.15, 5159.49] | 651.01 [448.66, 693.13] | 1446.69 [1446.67, 1446.71] |
| tlc-n1000000-h10-c1000 | Revon-M (forced Merkle) | 7 | 35894.85 [22907.72, 40610.97] | 5355.21 [2780.57, 5968.45] | 621.49 [466.41, 731.30] | 1446.69 [1446.67, 1446.70] |
| tlc-n1000000-h10-c1000 | Snapshot | 7 | 2668.94 [2226.88, 2766.84] | 2652.01 [2078.95, 2729.10] | 20912.44 [16010.37, 22305.87] | 3549.03 [3549.03, 3549.03] |

## Main findings

- At 10,000 records, Revon-H used `log` diff: commit 18.72 [18.60, 21.78] ms; diff 0.61 [0.57, 0.67] ms; footprint 14.56 [14.56, 14.57] MiB.
- At 100,000 records, Revon-H used `log` diff: commit 161.09 [131.22, 252.49] ms; diff 8.65 [8.54, 10.28] ms; footprint 90.04 [90.02, 90.05] MiB.
- At 1,000,000 records, Revon-H used `merkle` diff: commit 4764.26 [3086.15, 5159.49] ms; diff 651.01 [448.66, 693.13] ms; footprint 1446.69 [1446.67, 1446.71] MiB.
- At one million records, the ratios of median Revon-H/Snapshot commit and diff latencies are 1.80 and 0.03. Ratios above one mean Revon-H has a higher median; these are ratios of medians, not paired confidence intervals.
- At one million records, the ratios of median Revon-H/Log-only commit and diff latencies are 439.37 and 4.39. Ratios above one mean Revon-H has a higher median; these are ratios of medians, not paired confidence intervals.
- At one million records, the ratios of median Revon-H/Dolt commit and diff latencies are 4.05 and 0.61. Ratios above one mean Revon-H has a higher median; these are ratios of medians, not paired confidence intervals.
- At one million records, the ratios of median Revon-H/Dolt (bulk import) commit and diff latencies are 5.08 and 0.65. Ratios above one mean Revon-H has a higher median; these are ratios of medians, not paired confidence intervals.
- The scale sweep crosses the selector threshold: 100/1,000/10,000 accumulated operations lead to log/log/Merkle paths. The diff curve combines increased record count with a policy change.
- The 100k, 50-commit and 1%-density cases accumulate 5,000 and 10,000 operations and select Merkle. The original 4096 threshold was retained rather than tuned to this dataset.

## Environment and measurement limits

Python 3.12.14; Windows-11-10.0.26200-SP0; 12 logical CPUs; 15.64 GiB visible RAM; 4.14 GiB available at launch. Package versions: {'pyarrow': '25.0.1', 'psutil': '7.2.2'}. Available RAM was not held constant. Whole-worker RSS includes the oracle, setup and verification. Memory pressure and paging were not isolated from operation costs.

One monthly release, one affine sample/seed, generated update-only histories, key/value storage of eleven retained fields, and one physical host. No observed history, relational-query, multi-table, schema-evolution, concurrency, independent-hardware or beyond-one-million claim is established. No missing result is extrapolated.

## Paper sections and files

- Abstract: supported achieved scale; earlier latency-ratio claims explicitly scoped to the synthetic study.
- Methodology subsection D (4.4 in Single Column/BERT): source, preprocessing, record mapping, generated updates, sweeps, repetitions and timing boundaries.
- Table III: dataset schema/key mapping and exact scale/history/density specifications; original diff table renumbered IV.
- Results subsection E (5.5 in Single Column/BERT) and Figure 7: three panels for commit, diff and footprint with IQR; Table V reports history/density medians.
- Discussion: measured tradeoffs and the selector change in the scale sweep.
- Limitations, future work and conclusion: successful public scale replaces obsolete no-public-data/no-million-record statements; remaining boundaries stay explicit.
- Dataset reference and data availability: reference 31 in numbered variants and (NYC TLC, 2024) in BERT; reproducible acquisition/preparation/evaluation instructions.
- Related Work: obsolete exclusion of public-data evidence replaced with the actual one-release/generated-history boundary.
- BERT synchronization: stale duplicate abstract removed, affiliation alignment corrected, and existing tables kept with their captions.

Updated editable manuscripts and matching PDFs:

- paper/Revon_Research_Paper_IEEE_Pagination_Fixed.docx and paper/Revon_Research_Paper_IEEE.pdf
- paper/Revon_Final_Research_Paper.docx and paper/Revon_Final_Research_Paper.pdf
- paper/Revon_Research_Paper_Single_Column.docx and paper/Revon_Research_Paper_Single_Column.pdf
- output/docs/Revon_Research_Paper_BERT.docx and output/docs/Revon_Research_Paper_BERT.pdf

## Evidence and reproduction

Primary analysis bundle: `evidence/public-tlc-combined-20261002`. It contains pooled raw CSV and typed JSONL trials, elapsed durations, a manifest, audited summaries and plots. Its manifest references the original and recovery execution bundles, which retain exact archived source, observed/oracle verification hashes and commit intervals. Authoritative-link verification and interruption details remain in the original execution bundle. Pilot bundles are separate resource estimates. Acquisition and commands: docs/experiments/PUBLIC_DATASET_EVALUATION.md. Raw/processed records and temporary render material are ignored by Git.

The implementation preserves the original title, author text, original thirty references, and the six approved figure assets. QA: sixteen targeted regression tests passed; all one million prepared records were independently traced to the Parquet source; 1,221 successful historical-state hash comparisons were independently checked; 54 plotted point inputs and all 72 new table values match retained summaries. All final rendered pages across the four PDFs were visually inspected, including captions, figures, tables and new labels. See paper_verification.json and independent_source_verification.json in the analysis bundle for the final records.

## Failed configurations

- tlc-n1000000-h10-c1000 / Revon-M (forced Merkle) / measured 5: NoSuchProcess: process PID not found (pid=27816)

The initial matrix scheduled two warm-ups and seven measured attempts per configuration. One million-record Revon-M attempt was interrupted. One fresh isolated recovery trial was run after the matrix under identical frozen source, workload and packages, with no additional warm-up. Both the failed original row and successful recovery are retained. Seven successful measured trials per configuration enter summaries. Recovery was outside the original counterbalanced block; RAM and host conditions were not held constant.

Original execution and recovery bundles: evidence/public-tlc-evaluation-20261001, evidence/public-tlc-recovery-20261002. The original interrupted worker report and interruption.json remain in the original execution bundle. Its unusable timings are not included in pooled summaries; the new recovery is a separate measured execution.