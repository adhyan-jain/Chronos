"""Isolated public-dataset trials, resumable evidence, and independent audit."""
from __future__ import annotations
import argparse
import csv
import gc
import json
import platform
import shutil
import statistics
import time
import uuid
import importlib.metadata
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .public_dataset import build_public_workload, file_digest, specs
from .workloads import Workload
from .final_benchmark import (MODEL_KEYS, TrialRecord, _blocked_model_order,
                              _write_csv, _write_summary, run_trial)


def execute(directory, data, *, mode="pilot", scenarios=None, warmups=2, trials=7, models=MODEL_KEYS, timeout=900):
    import psutil
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.json"
    selected = [s for s in specs() if scenarios is None or s.name in scenarios]
    if path.exists():
        manifest = json.loads(path.read_text())
        if (manifest["models"] != list(models) or manifest["warmups"] != warmups
                or manifest["measured_trials"] != trials
                or manifest["workloads"] != [asdict(s) for s in selected]):
            raise ValueError("Resume configuration differs from original manifest")
    else:
        manifest = {
            "schema_version": 1, "study": "public-dataset", "mode": mode,
            "run_id": uuid.uuid4().hex, "created_utc": datetime.now(timezone.utc).isoformat(),
            "models": list(models), "warmups": warmups, "measured_trials": trials,
            "workloads": [asdict(s) for s in selected], "workload_digests": {},
            "dataset": json.loads((data / "dataset.json").read_text()),
            "platform": platform.platform(), "python": platform.python_version(),
            "package_versions": {name: importlib.metadata.version(name) for name in ("pyarrow", "psutil")},
            "processor": platform.processor(), "cpu_logical": psutil.cpu_count(),
            "physical_memory_bytes": psutil.virtual_memory().total,
            "available_memory_at_start_bytes": psutil.virtual_memory().available,
            "free_disk_at_start_bytes": shutil.disk_usage(directory).free,
            "trial_wall_clock_limit_seconds": timeout,
            "trie": {"branching_factor": 8, "depth": 4, "threshold": 4096},
            "update_rule": "uniform seeded sample without replacement within each commit; +0.01 fare and total; repeated records across commits allowed; updates only; histories synthetic",
            "endpoints": "diff initial version 1 to version H+1; all trials verify both endpoints; first measured trial per system/configuration verifies every historical version outside timing",
            "payload_bytes_field": "null in typed public trial evidence and empty in CSV because real values have variable lengths; internal spec validation placeholder 8 is not a payload measurement",
            "measurement": "existing whole-system adapter workflow; import separately; trial commit statistic is median of H timed commits; diff includes canonicalization; storage after timed diff/checkout and untimed historical checks, before close/compaction",
            "sampling_limitations": "affine nested sample is dispersed but not a uniform random permutation; single seed, single month, no observed change histories",
            "source_code_sha256": {str(p): file_digest(p) for p in [Path('experiments/public_dataset.py'), Path('experiments/public_dataset_study.py'), Path('experiments/final_benchmark.py'), Path('experiments/adapters.py'), Path('experiments/workloads.py'), Path('sqlite_store.py'), Path('versioned_db.py'), Path('requirements.txt')]},
        }
        for source in manifest["source_code_sha256"]:
            destination = directory / "source" / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        path.write_text(json.dumps(manifest, indent=2))
    raw = directory / "raw_results.csv"
    records = []
    if raw.exists():
        # Recover typed records without lossy CSV inference.
        records = [TrialRecord(**json.loads(line)) for line in (directory / "trials.jsonl").read_text().splitlines()]
    done = {(r.scenario, r.trial_kind, r.trial, r.model) for r in records}
    names = {"snapshot": "Snapshot", "log": "Log-only", "revon-m": "Revon-M (forced Merkle)", "revon-h": "Revon-H", "dolt": "Dolt", "dolt-bulk": "Dolt (bulk import)"}
    for spec in selected:
        if spec.name not in manifest["workload_digests"]:
            workload = build_public_workload(spec, data)
            manifest["workload_digests"][spec.name] = workload.digest
            del workload
            gc.collect()
            path.write_text(json.dumps(manifest, indent=2))
        stub = Workload(spec, {}, (), (), manifest["workload_digests"][spec.name])
        for kind, count in (("warmup", warmups), ("measured", trials)):
            for trial in range(1, count + 1):
                order = _blocked_model_order(models, seed=spec.seed, phase=mode, scenario=spec.name, kind=kind, trial=trial)
                for position, model in enumerate(order, 1):
                    if (spec.name, kind, trial, names[model]) in done:
                        continue
                    if mode == "evaluation":
                        for source, expected_hash in manifest["source_code_sha256"].items():
                            if file_digest(source) != expected_hash:
                                raise ValueError(f"Source changed during evaluation: {source}")
                    started = time.monotonic()
                    print(f"START {spec.name} {kind} {trial} {model}", flush=True)
                    record = run_trial(run_id=manifest["run_id"], phase=mode, workload=stub,
                        model_key=model, trial_kind=kind, trial=trial, execution_order=position,
                        threshold=4096, scratch_root=directory / ".work", public_dataset=data,
                        verification_path=directory / "verification" / f"{spec.name}-{kind}-{trial}-{model}.json",
                        timeout_seconds=timeout, verify_all_history=(kind == "measured" and trial == 1))
                    record.payload_bytes = None
                    records.append(record)
                    with (directory / "trials.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(asdict(record)) + "\n")
                    _write_csv(raw, records)
                    _write_summary(directory / "summary.csv", records)
                    with (directory / "elapsed.jsonl").open("a") as stream:
                        stream.write(json.dumps({"scenario": spec.name, "kind": kind, "trial": trial, "model": model, "wall_seconds": time.monotonic() - started}) + "\n")
                    print(f"DONE {record.status} {time.monotonic()-started:.1f}s import={record.initial_import_ms} commit={record.incremental_commit_ms} diff={record.diff_ms}", flush=True)
    return audit(directory)


def audit(directory):
    from .final_benchmark import _percentile
    manifest = json.loads((directory / "manifest.json").read_text())
    records = [TrialRecord(**json.loads(line)) for line in (directory / "trials.jsonl").read_text().splitlines()]
    issues = []
    with (directory / "raw_results.csv").open(newline="") as stream:
        csv_records = list(csv.DictReader(stream))
    expected_csv = [{k: "" if v is None else str(v) for k, v in asdict(r).items()} for r in records]
    if csv_records != expected_csv:
        issues.append("raw CSV differs from typed trial journal")
    for name, expected_hash in manifest["source_code_sha256"].items():
        archived = directory / "source" / name
        if manifest["mode"] == "evaluation" and not archived.exists():
            issues.append(f"missing archived source {name}")
        if archived.exists() and file_digest(archived) != expected_hash:
            issues.append(f"archived source checksum mismatch {name}")
    keys = [(r.scenario, r.model, r.trial_kind, r.trial) for r in records]
    if len(set(keys)) != len(keys):
        issues.append("duplicate trials")
    expected = len(manifest["workloads"]) * len(manifest["models"]) * (manifest["warmups"] + manifest["measured_trials"])
    if len(records) != expected:
        issues.append(f"incomplete matrix {len(records)}/{expected}")
    displays = {"snapshot": "Snapshot", "log": "Log-only", "revon-m": "Revon-M (forced Merkle)", "revon-h": "Revon-H", "dolt": "Dolt", "dolt-bulk": "Dolt (bulk import)"}
    expected_keys = {(s["name"], displays[m], kind, trial)
        for s in manifest["workloads"] for m in manifest["models"]
        for kind, count in (("warmup", manifest["warmups"]), ("measured", manifest["measured_trials"]))
        for trial in range(1, count + 1)}
    if set(keys) != expected_keys:
        issues.append("trial identities differ from planned matrix")
    spec_map = {s["name"]: s for s in manifest["workloads"]}
    for r in records:
        if r.workload_sha256 != manifest["workload_digests"][r.scenario] or r.hybrid_threshold != 4096:
            issues.append("workload or threshold mismatch")
        if r.status == "ok" and not r.correctness:
            issues.append("false correctness")
        spec = spec_map.get(r.scenario)
        if spec is None or any(getattr(r, field) != spec[field] for field in ("rows", "commits", "changes_per_commit", "seed")):
            issues.append("trial workload parameters differ from manifest")
    verification = list((directory / "verification").glob("*.json"))
    if len(verification) != sum(r.status == "ok" for r in records):
        issues.append("missing verification report")
    for p in verification:
        doc = json.loads(p.read_text())
        if not doc["diff_correct"] or any(v["oracle_sha256"] != v["observed_sha256"] for v in doc["historical_states"]):
            issues.append(f"oracle mismatch {p.name}")
        if doc.get("diff_oracle_sha256", doc["diff_output_sha256"]) != doc["diff_output_sha256"]:
            issues.append(f"diff hash mismatch {p.name}")
    model_keys = {"Snapshot": "snapshot", "Log-only": "log", "Revon-M (forced Merkle)": "revon-m", "Revon-H": "revon-h", "Dolt": "dolt", "Dolt (bulk import)": "dolt-bulk"}
    for r in records:
        if r.status != "ok":
            continue
        p = directory / "verification" / f"{r.scenario}-{r.trial_kind}-{r.trial}-{model_keys[r.model]}.json"
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        if (doc["workload_sha256"] != r.workload_sha256
                or len(doc["historical_states"]) != (r.commits + 1 if doc.get("all_history_verified", True) else 2)
                or len(doc["commit_intervals_ms"]) != r.commits
                or doc["changed_keys"] != r.changed_keys
                or not math_isclose(statistics.median(doc["commit_intervals_ms"]), r.incremental_commit_ms)):
            issues.append(f"verification metadata mismatch {p.name}")
    # Independently reproduce all summary medians and linear-interpolated IQRs.
    with (directory / "summary.csv").open(newline="") as stream:
        summaries = list(csv.DictReader(stream))
    for s in summaries:
        group = [r for r in records if r.status == "ok" and r.trial_kind == "measured" and r.scenario == s["scenario"] and r.model == s["model"]]
        for metric in ("initial_import_ms", "incremental_commit_ms", "diff_ms", "storage_bytes"):
            values = [getattr(r, metric) for r in group]
            for suffix, value in (("median", statistics.median(values)), ("p25", _percentile(values, .25)), ("p75", _percentile(values, .75))):
                if not math_isclose(float(s[f"{metric}_{suffix}"]), value):
                    issues.append(f"summary mismatch {s['scenario']} {metric}")
    result = {"passed": not issues, "issues": issues, "executions": len(records),
              "ok": sum(r.status == "ok" for r in records),
              "failures": [asdict(r) for r in records if r.status != "ok"],
              "historical_states_verified": sum(len(json.loads(p.read_text())["historical_states"]) for p in verification),
              "evidence_files_sha256": {name: file_digest(directory / name) for name in ("manifest.json", "trials.jsonl", "raw_results.csv", "summary.csv", "elapsed.jsonl")},
              "verification_files_sha256": {p.name: file_digest(p) for p in verification}}
    (directory / "evidence_audit.json").write_text(json.dumps(result, indent=2))
    return result


def math_isclose(a, b):
    import math
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--data", type=Path, default=Path("data/public/nyc-tlc-2024-01"))
    p.add_argument("--mode", default="pilot")
    p.add_argument("--scenarios", nargs="+")
    p.add_argument("--models", nargs="+", default=list(MODEL_KEYS))
    p.add_argument("--warmups", type=int, default=2)
    p.add_argument("--trials", type=int, default=7)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--audit", action="store_true")
    a = p.parse_args()
    result = audit(a.output) if a.audit else execute(a.output, a.data, mode=a.mode,
        scenarios=a.scenarios, models=a.models, warmups=a.warmups, trials=a.trials, timeout=a.timeout)
    print(json.dumps({k: len(v) if k == "failures" else v for k, v in result.items()
        if k not in ("verification_files_sha256", "evidence_files_sha256")}, indent=2))
