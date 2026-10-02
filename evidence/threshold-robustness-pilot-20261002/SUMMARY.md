# Threshold pilot: short assessment

**Yes, the new histories change the observed performance pattern. No, they do not validate a new optimal threshold.**

## Principal result

All three seeds agree on the following preferred forced path in warmed measurements. Ratios are log median / Merkle median; the 5% screen is exploratory, not a confidence test.

| Profile | Accumulated operations | Ratio range across three seeds | Preferred path |
|---|---:|---:|---|
| repeated-key | 32,768 | 0.738-0.817 | Log |
| repeated-key | 65,536 | 1.167-1.197 | Merkle |
| repeated-key | 131,072 | 1.455-1.507 | Merkle |
| spread | 65,536 | 0.744-0.850 | Log |

The old repeated-key diagnostic favoured Merkle at 32,768 and log at 65,536. Neither of those preferences reproduced here. The new repeated-key results favour log at 32,768 and Merkle at both larger sampled counts. This supports an observed switching region for these histories; it does not locate an exact crossover or establish a universal optimum. Old evidence is preserved and not pooled with this pilot.

At the same 65,536-operation count, repeated-key histories favour Merkle while spread histories favour log. Fresh-process/reopened results retain that contrast for all three seeds. The profiles also differ in row count and history length, so this is evidence of profile dependence, not a causal isolation of locality.

## Do larger thresholds help?

Comparing H131,072 with H16,384, warmed spread histories improve by 13.1-22.2%. Repeated-key histories at 65,536 instead worsen by 12.3-19.7%, and at 131,072 worsen by 36.0-53.5%. These are descriptive timing differences; there is no across-history confidence interval.

Always-log remains competitive for spread histories and the smallest repeated-key count. It is slower than forced Merkle at the larger repeated-key counts. Therefore neither always-log nor simply raising the threshold is supported as universally best.

## Blunt limitations

- The initial 18-case plan was reduced to 12 using a frozen wall-time resource rule after the first case, before inspecting latency trends. The six omitted cases are spread histories at 32,768 and 131,072. All three seeds were completed in each retained condition. No cases were dropped because their results were unfavourable.
- Three independent histories per condition are a pilot, not strong population-level evidence. Five warmed query blocks and three fresh-process blocks are nested observations.
- Fresh workers use hash seed = workload seed + block, while warmed workers use the workload seed. Both paths share the same hash seed within each fresh block, but warmed/fresh differences do not isolate caching or allocation state alone.
- Reopening eagerly loads and verifies the complete object model. OS filesystem cache was not cleared. Open time is separate from diff time.
- Same-path selector/forced measurements range from 0.614 to 1.213 times the corresponding forced-path median. This substantial variability prevents treating small differences among thresholds selecting the same path as algorithmic improvements. Scheduling, GC and allocation effects are hypotheses, not established causes.
- The actual workload uses one insert and one delete per commit at these update counts; the remaining mutations are updates. The generator docstring describing an 80/10/10 mix does not match this implementation. Production code was inspected but not changed.
- One physical Windows host, changing background resource conditions, and no independent Linux replication.

## Recommendation

**D. The original full pilot scope was resource-limited.** Nevertheless, the completed reduced scope provides a concrete reason to investigate workload-sensitive selection separately (option B as a follow-up hypothesis). It does not justify changing the paper or production threshold yet.

Next, hold row count and history length constant while varying locality/density. Fix Python hash seeds across warmed and reopened conditions, record GC/resource behaviour, and retain independent repositories as the uncertainty unit. Use fresh calibration and untouched validation seeds with always-log and forced-Merkle baselines, followed by separate Linux hardware. No larger study has been launched.

The reduced pilot took 28.3 minutes in completed cases and peaked at 1,214 MiB sampled worker RSS. A ten-seed extension of this reduced scope is roughly 94 minutes at the observed rate, plus setup/failures; full-scope time and required replication counts must be re-estimated.

## Verification and files

12 independently built repositories; 588 warmed queries including 168 warm-ups; 126 measured fresh-process queries. Total: 714 timed queries, 546 measured. All matched the common semantic oracle. Reverse/identity, representative historical-state and persistent-integrity checks passed. Zero worker/correctness failures; six predeclared resource omissions.
The independent audit checked raw/summary agreement, randomized blocks, selected paths, frozen source hashes and 700 protected files. Paper files, production code, existing experiment scripts, prior evidence and Git HEAD are unchanged. No commits, push or cloud provisioning.
New experimental code: experiments/threshold_robustness_pilot.py and experiments/analyze_threshold_robustness_pilot.py. All other pilot outputs remain in this ignored run directory. Exact inventory: [files_created.txt](files_created.txt).

Hardware: Intel Core i7-1255U, 10 physical/12 logical CPUs, 15.64 GiB RAM, Windows 11, NTFS; Python 3.14.3 and psutil 7.1.0. Hardware model/filesystem were inspected after freeze and recorded separately; resource conditions are from the execution manifest and worker observations.

[Full tables and reproducible commands](ASSESSMENT.md) | [Independent audit](independent_audit.json) | [All seed/path ratios](paired_ratios.json) | [Raw queries](raw_results.csv)

![Forced-path results](forced_path_ratios.png)

![Selectors against always-log](selector_vs_always_log.png)

![Fresh-process comparison](cache_sensitivity.png)
