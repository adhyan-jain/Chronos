"""Pool one explicitly documented recovery trial without altering source bundles."""
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.final_benchmark import TrialRecord, _write_csv, _write_summary


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, q):
    ordered = sorted(values)
    position = (len(ordered)-1)*q
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(position-lo)


def combine(directories, output):
    manifests, audits, records = [], [], []
    for directory in directories:
        manifest = json.loads((directory / "manifest.json").read_text())
        audit = json.loads((directory / "evidence_audit.json").read_text())
        assert audit["passed"], audit["issues"]
        for name, digest in audit["evidence_files_sha256"].items():
            assert sha(directory / name) == digest, f"changed retained evidence: {directory}/{name}"
        for name, digest in audit["verification_files_sha256"].items():
            assert sha(directory / "verification" / name) == digest
        manifests.append(manifest); audits.append(audit)
        records.extend(TrialRecord(**json.loads(line)) for line in (directory / "trials.jsonl").read_text().splitlines())
    original = manifests[0]
    for manifest in manifests[1:]:
        for field in ("dataset", "source_code_sha256", "trie", "python", "package_versions", "platform", "processor", "cpu_logical", "physical_memory_bytes"):
            assert manifest[field] == original[field], f"recovery differs in {field}"
        assert all(original["workload_digests"][name] == digest for name, digest in manifest["workload_digests"].items())
    identities = [(r.run_id, r.scenario, r.model, r.trial_kind, r.trial) for r in records]
    assert len(set(identities)) == len(identities)
    assert len(records) == 325 and sum(r.status == "ok" for r in records) == 324
    assert len([r for r in records if r.status != "ok"]) == 1
    assert records[-1].model == "Revon-M (forced Merkle)" and records[-1].scenario == "tlc-n1000000-h10-c1000"
    output.mkdir(parents=True, exist_ok=True)
    (output / "trials.jsonl").write_text("".join(json.dumps(asdict(r)) + "\n" for r in records), encoding="utf-8")
    elapsed = []
    for directory, source_manifest in zip(directories, manifests):
        for line in (directory / "elapsed.jsonl").read_text().splitlines():
            item = json.loads(line)
            item["run_id"] = source_manifest["run_id"]
            elapsed.append(item)
    (output / "elapsed.jsonl").write_text("".join(json.dumps(item) + "\n" for item in elapsed))
    _write_csv(output / "raw_results.csv", records)
    _write_summary(output / "summary.csv", records)
    with (output / "summary.csv").open(newline="") as f:
        summaries = list(csv.DictReader(f))
    assert len(summaries) == 36
    for row in summaries:
        selected = [r for r in records if r.status == "ok" and r.trial_kind == "measured" and r.scenario == row["scenario"] and r.model == row["model"]]
        assert len(selected) == int(row["trials"]) == 7
        for metric in ("initial_import_ms", "incremental_commit_ms", "diff_ms", "checkout_ms", "storage_bytes"):
            values = [getattr(r, metric) for r in selected]
            for suffix, expected in (("median", statistics.median(values)), ("p25", percentile(values, .25)), ("p75", percentile(values, .75))):
                assert math.isclose(float(row[f"{metric}_{suffix}"]), expected, rel_tol=1e-12, abs_tol=1e-9)
    manifest = dict(original)
    manifest.update({"study": "public-dataset pooled analysis", "mode": "analysis", "run_id": uuid.uuid4().hex,
        "execution_bundles": [d.relative_to(ROOT).as_posix() for d in directories],
        "recovery_policy": "The initial matrix scheduled two warm-ups and seven measured attempts per configuration. One million-record Revon-M attempt was interrupted. One fresh isolated recovery trial was run after the matrix under identical frozen source, workload and packages, with no additional warm-up. Both the failed original row and successful recovery are retained. Seven successful measured trials per configuration enter summaries. Recovery was outside the original counterbalanced block; RAM and host conditions were not held constant.",
        "analysis_source_sha256": sha(Path(__file__)),
        "execution_run_ids": [m["run_id"] for m in manifests]})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    audit = {"passed": True, "issues": [], "executions": len(records), "ok": sum(r.status == "ok" for r in records),
        "failures": [asdict(r) for r in records if r.status != "ok"],
        "historical_states_verified": sum(a["historical_states_verified"] for a in audits),
        "successful_measured_trials": 252, "warmup_trials": 72,
        "configurations": 36, "successful_measured_trials_per_configuration": 7,
        "source_bundle_audits_sha256": {d.relative_to(ROOT).as_posix(): sha(d / "evidence_audit.json") for d in directories},
        "evidence_files_sha256": {name: sha(output / name) for name in ("manifest.json", "trials.jsonl", "raw_results.csv", "summary.csv", "elapsed.jsonl")}}
    (output / "evidence_audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps({k: v for k,v in audit.items() if k not in {"failures", "evidence_files_sha256", "source_bundle_audits_sha256"}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    combine([p.resolve() for p in args.evidence], args.output.resolve())
