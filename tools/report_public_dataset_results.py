"""Write a reviewer-readable Comment 1 report from completed retained evidence."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report(directory):
    audit = json.loads((directory / "evidence_audit.json").read_text())
    assert audit["passed"], audit["issues"]
    manifest = json.loads((directory / "manifest.json").read_text())
    with (directory / "raw_results.csv").open(newline="") as f:
        raw = list(csv.DictReader(f))
    with (directory / "summary.csv").open(newline="") as f:
        summary = list(csv.DictReader(f))
    lookup = {(r["scenario"], r["model"]): r for r in summary}
    text = ["# Comment 1 public dataset results", "",
        "This report covers the public dataset, scale, history and update-density evaluation. It does not close the other seven comments in the supervisor's review.", "",
        "## Dataset and preparation", "",
        "NYC TLC yellow-taxi trip records, January 2024: 2,964,624 source rows and 1,000,000 retained rows with eleven original fields. Keys identify source-file rows through release/checksum/ordinal, rather than asserting a natural trip identifier. Nested affine subsets share a fixed sampling seed. Missing values remain null, anomalous domain values survive, and duplicate field contents retain separate row identities. Histories are generated corrections to fare and total, not observed revisions.", "",
        "Authoritative source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", "",
        f"Download SHA-256: `{manifest['dataset']['download_sha256']}`. Prepared JSONL SHA-256: `{manifest['dataset']['prepared_sha256']}`.", "",
        "## Completed matrix", "",
        f"{audit['executions']} executions; {audit['ok']} successful; {len(audit['failures'])} failed/unavailable. Each configuration schedules {manifest['warmups']} warm-ups and {manifest['measured_trials']} measured trials; the table gives successful measured-trial counts. Pilot timings are excluded. Every successful trial checks both endpoint states and semantic diff. The first measured trial per system/configuration checks all historical versions; the retained verification reports contain {audit['historical_states_verified']} state-hash comparisons in total.", "",
        "| Scenario | Rows | Incremental commits | Changed records per commit | Update density | Diff endpoints |", "|---|---:|---:|---:|---:|---|",
    ]
    for s in manifest["workloads"]:
        text.append(f"| {s['name']} | {s['rows']:,} | {s['commits']} | {s['changes_per_commit']:,} | {100*s['changes_per_commit']/s['rows']:.2g}% | 1 to {s['commits']+1} |")
    text += ["", "Systems: Snapshot, Log-only, forced-Merkle Revon-M, Revon-H, Dolt SQL import and Dolt CSV import. The two Dolt workflows use the same engine for subsequent operations. Revon remains at b=8, d=4 and threshold 4096.", "",
        "## Measured results and uncertainty", "",
        "All values below are median [25th percentile, 75th percentile] across measured trials. Each trial's incremental-commit value is itself the median of the timed commit intervals. These IQRs describe fixed-workload repetition on this host; they are not confidence intervals across datasets or machines. Storage is the whole directory before compaction. Import and incremental commit are separate operations.", "",
        "| Scenario | System | n | Import ms | Incremental commit ms | Diff ms | Repository MiB |", "|---|---|---:|---:|---:|---:|---:|",
    ]
    def fmt(r, metric, divisor=1):
        return f"{float(r[metric+'_median'])/divisor:.2f} [{float(r[metric+'_p25'])/divisor:.2f}, {float(r[metric+'_p75'])/divisor:.2f}]"
    for r in summary:
        text.append(f"| {r['scenario']} | {r['model']} | {r['trials']} | {fmt(r,'initial_import_ms')} | {fmt(r,'incremental_commit_ms')} | {fmt(r,'diff_ms')} | {fmt(r,'storage_bytes',2**20)} |")
    text += ["", "## Main findings", ""]
    for n in (10000, 100000, 1000000):
        r = lookup.get((f"tlc-n{n}-h10-c{n//1000}", "Revon-H"))
        if r:
            text.append(f"- At {n:,} records, Revon-H used `{r['strategy_selected']}` diff: commit {fmt(r,'incremental_commit_ms')} ms; diff {fmt(r,'diff_ms')} ms; footprint {fmt(r,'storage_bytes',2**20)} MiB.")
    large = lookup.get(("tlc-n1000000-h10-c1000", "Revon-H"))
    if large:
        for model in ("Snapshot", "Log-only", "Dolt", "Dolt (bulk import)"):
            r = lookup.get(("tlc-n1000000-h10-c1000", model))
            if r:
                commit_ratio = float(large["incremental_commit_ms_median"])/float(r["incremental_commit_ms_median"])
                diff_ratio = float(large["diff_ms_median"])/float(r["diff_ms_median"])
                text.append(f"- At one million records, the ratios of median Revon-H/{model} commit and diff latencies are {commit_ratio:.2f} and {diff_ratio:.2f}. Ratios above one mean Revon-H has a higher median; these are ratios of medians, not paired confidence intervals.")
    text += ["- The scale sweep crosses the selector threshold: 100/1,000/10,000 accumulated operations lead to log/log/Merkle paths. The diff curve combines increased record count with a policy change.",
        "- The 100k, 50-commit and 1%-density cases accumulate 5,000 and 10,000 operations and select Merkle. The original 4096 threshold was retained rather than tuned to this dataset.", "",
        "## Environment and measurement limits", "",
        f"Python {manifest['python']}; {manifest['platform']}; {manifest['cpu_logical']} logical CPUs; {manifest['physical_memory_bytes']/2**30:.2f} GiB visible RAM; {manifest['available_memory_at_start_bytes']/2**30:.2f} GiB available at launch. Package versions: {manifest['package_versions']}. Available RAM was not held constant. Whole-worker RSS includes the oracle, setup and verification. Memory pressure and paging were not isolated from operation costs.", "",
        "One monthly release, one affine sample/seed, generated update-only histories, key/value storage of eleven retained fields, and one physical host. No observed history, relational-query, multi-table, schema-evolution, concurrency, independent-hardware or beyond-one-million claim is established. No missing result is extrapolated.", "",
        "## Paper sections and files", "",
        "- Abstract: supported achieved scale; earlier latency-ratio claims explicitly scoped to the synthetic study.",
        "- Methodology subsection D (4.4 in Single Column/BERT): source, preprocessing, record mapping, generated updates, sweeps, repetitions and timing boundaries.",
        "- Table III: dataset schema/key mapping and exact scale/history/density specifications; original diff table renumbered IV.",
        "- Results subsection E (5.5 in Single Column/BERT) and Figure 7: three panels for commit, diff and footprint with IQR; Table V reports history/density medians.",
        "- Discussion: measured tradeoffs and the selector change in the scale sweep.",
        "- Limitations, future work and conclusion: successful public scale replaces obsolete no-public-data/no-million-record statements; remaining boundaries stay explicit.",
        "- Dataset reference and data availability: reference 31 in numbered variants and (NYC TLC, 2024) in BERT; reproducible acquisition/preparation/evaluation instructions.",
        "- Related Work: obsolete exclusion of public-data evidence replaced with the actual one-release/generated-history boundary.",
        "- BERT synchronization: stale duplicate abstract removed, affiliation alignment corrected, and existing tables kept with their captions.", "",
        "Updated editable manuscripts and matching PDFs:", "",
        "- paper/Revon_Research_Paper_IEEE_Pagination_Fixed.docx and paper/Revon_Research_Paper_IEEE.pdf",
        "- paper/Revon_Final_Research_Paper.docx and paper/Revon_Final_Research_Paper.pdf",
        "- paper/Revon_Research_Paper_Single_Column.docx and paper/Revon_Research_Paper_Single_Column.pdf",
        "- output/docs/Revon_Research_Paper_BERT.docx and output/docs/Revon_Research_Paper_BERT.pdf", "",
        "## Evidence and reproduction", "",
        f"Primary analysis bundle: `{directory.relative_to(ROOT).as_posix()}`. It contains pooled raw CSV and typed JSONL trials, elapsed durations, a manifest, audited summaries and plots. Its manifest references the original and recovery execution bundles, which retain exact archived source, observed/oracle verification hashes and commit intervals. Authoritative-link verification and interruption details remain in the original execution bundle. Pilot bundles are separate resource estimates. Acquisition and commands: docs/experiments/PUBLIC_DATASET_EVALUATION.md. Raw/processed records and temporary render material are ignored by Git.", "",
        "The implementation preserves the original title, author text, original thirty references, and the six approved figure assets. QA: sixteen targeted regression tests passed; all one million prepared records were independently traced to the Parquet source; 1,221 successful historical-state hash comparisons were independently checked; 54 plotted point inputs and all 72 new table values match retained summaries. All final rendered pages across the four PDFs were visually inspected, including captions, figures, tables and new labels. See paper_verification.json and independent_source_verification.json in the analysis bundle for the final records.", "",
    ]
    if audit["failures"]:
        text += ["## Failed configurations", ""]
        for r in audit["failures"]:
            text.append(f"- {r['scenario']} / {r['model']} / {r['trial_kind']} {r['trial']}: {r['notes']}")
        if (directory / "interruption.json").exists():
            text += ["", "The million-record Revon-M measured trial 5 lost its worker during an interrupted run. Its wall duration was 4,203 seconds and its retained worker report contains two commit intervals of roughly 26 and 42 minutes. These timings are unusable. The failed raw row and separate interrupted_worker_verification report are retained; no timing is recovered or imputed. Six valid measured trials remain for this configuration. This failure does not establish an algorithmic or memory scale limit. See interruption.json for the observed facts and inference boundary."]
        if manifest.get("recovery_policy"):
            text += ["", manifest["recovery_policy"], "", "Original execution and recovery bundles: " + ", ".join(manifest["execution_bundles"]) + ". The original interrupted worker report and interruption.json remain in the original execution bundle. Its unusable timings are not included in pooled summaries; the new recovery is a separate measured execution."]
    output = ROOT / "docs/experiments/PUBLIC_DATASET_RESULTS.md"
    output.write_text("\n".join(text), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    report(args.evidence.resolve())
