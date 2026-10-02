"""Independently trace prepared TLC records and retained outputs to the source."""
import argparse
import gc
import hashlib
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def state_digest(state):
    # Stream the checkout contract, without retaining a second million-row list.
    h = hashlib.sha256(b'{"records":[')
    for index, key in enumerate(sorted(state)):
        if index:
            h.update(b",")
        h.update(encoded([key, state[key]]))
    h.update(b"]}")
    return h.hexdigest()


def verify(data, evidence):
    import pyarrow.parquet as pq
    from experiments.public_dataset import build_public_workload, specs
    manifest = json.loads((evidence / "manifest.json").read_text())
    metadata = manifest["dataset"]
    raw = data / "yellow_tripdata_2024-01.parquet"
    prepared = data / "records.jsonl"
    assert digest_file(raw) == metadata["download_sha256"]
    assert digest_file(prepared) == metadata["prepared_sha256"]
    assert math.gcd(metadata["stride"], metadata["original_records"]) == 1
    inverse = pow(metadata["stride"], -1, metadata["original_records"])
    fields = metadata["retained_fields"]
    seen = bytearray(metadata["retained_records"])
    missing = dict.fromkeys(fields, 0)
    ordinal = retained = 0
    parquet = pq.ParquetFile(raw)
    assert parquet.metadata.num_rows == metadata["original_records"]
    with prepared.open("rb") as stream:
        for batch in parquet.iter_batches(batch_size=16384, columns=fields):
            for record in batch.to_pylist():
                rank = ((ordinal - metadata["offset"]) * inverse) % metadata["original_records"]
                key = f"tlc-202401-{metadata['download_sha256'][:16]}-{ordinal:07d}"
                ordinal += 1
                if rank >= metadata["retained_records"]:
                    continue
                for field, value in record.items():
                    if isinstance(value, datetime):
                        record[field] = value.isoformat(timespec="microseconds")
                    elif isinstance(value, float) and not math.isfinite(value):
                        record[field] = None
                    if record[field] is None:
                        missing[field] += 1
                expected = {"rank": rank, "key": key, "value": encoded(record).decode("utf-8")}
                assert stream.readline() == encoded(expected) + b"\n", f"source mapping mismatch at ordinal {ordinal-1}"
                assert not seen[rank], "duplicate subset rank"
                seen[rank] = 1
                retained += 1
        assert stream.read() == b"", "unexpected prepared tail"
    assert retained == metadata["retained_records"] and all(seen)
    assert missing == metadata["missing_values"]
    print(f"Source-to-prepared comparison passed for all {retained:,} records", flush=True)
    del seen, batch
    gc.collect()
    execution_dirs = [ROOT / p for p in manifest.get("execution_bundles", [])] or [evidence]
    verification = [json.loads(p.read_text()) for directory in execution_dirs for p in (directory / "verification").glob("*.json")]
    raw_trials = [json.loads(line) for directory in execution_dirs for line in (directory / "trials.jsonl").read_text().splitlines()]
    scenarios = []
    initial_hashes = {}
    for spec in specs():
        workload = build_public_workload(spec, data)
        assert workload.digest == manifest["workload_digests"][spec.name]
        state = dict(workload.initial)
        hashes = {1: state_digest(state)}
        assert initial_hashes.setdefault(spec.rows, hashes[1]) == hashes[1], "sweeps changed the initial state"
        rng = random.Random(spec.seed)
        ordered_keys = sorted(state)
        touched = set()
        for revision, mutations in enumerate(workload.batches, 2):
            assert len(mutations) == spec.changes_per_commit
            assert len({m.key for m in mutations}) == spec.changes_per_commit
            assert [m.key for m in mutations] == sorted(rng.sample(ordered_keys, spec.changes_per_commit))
            for m in mutations:
                assert m.old_exists and m.new_exists and state[m.key] == m.old_value
                old, new = json.loads(m.old_value), json.loads(m.new_value)
                assert old.keys() == new.keys() == set(fields)
                assert old != new
                for field in fields:
                    expected = round(float(old[field] or 0) + 0.01, 2) if field in {"fare_amount", "total_amount"} else old[field]
                    assert new[field] == expected, (spec.name, revision, field)
                state[m.key] = m.new_value
                touched.add(m.key)
            hashes[revision] = state_digest(state)
        assert state == workload.states[-1]
        changes = [{"key": k, "old_value_sha256": hashlib.sha256(workload.initial[k].encode()).hexdigest(),
                    "new_value_sha256": hashlib.sha256(state[k].encode()).hexdigest()}
                   for k in sorted(touched) if workload.initial[k] != state[k]]
        diff_hash = hashlib.sha256(encoded({"changes": changes})).hexdigest()
        matching = [v for v in verification if v["workload_sha256"] == workload.digest]
        expected_trials = sum(r["status"] == "ok" and r["workload_sha256"] == workload.digest for r in raw_trials)
        assert len(matching) == expected_trials
        for v in matching:
            assert v["diff_output_sha256"] == v["diff_oracle_sha256"] == diff_hash
            assert v["changed_keys"] == len(changes)
            for h in v["historical_states"]:
                assert h["observed_sha256"] == h["oracle_sha256"] == hashes[h["version"]]
        scenarios.append({"scenario": spec.name, "workload_sha256": workload.digest,
                          "versions_independently_replayed": len(hashes), "retained_trial_reports_checked": len(matching),
                          "changed_records_initial_to_final": len(changes), "diff_sha256": diff_hash})
        print(f"Independent history/output replay passed: {spec.name}", flush=True)
        del workload, state, mutations, changes, ordered_keys
        gc.collect()
    report = {"passed": True, "source_records_traced": retained, "source_sha256": digest_file(raw),
              "prepared_sha256": digest_file(prepared), "missing_values": missing, "scenarios": scenarios}
    (evidence / "independent_source_verification.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data/public/nyc-tlc-2024-01")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    verify(args.data.resolve(), args.evidence.resolve())
