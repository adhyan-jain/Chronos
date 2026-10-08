"""Checksum-pinned TLC records and deterministic, generated update histories."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from .adapters import canonical_bytes
from .workloads import Mutation, Workload, WorkloadSpec, apply_mutations

URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
SHA256 = "c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510"
SOURCE = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
SEED = 20261001
FIELDS = ("VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
          "passenger_count", "trip_distance", "PULocationID", "DOLocationID",
          "payment_type", "fare_amount", "tip_amount", "total_amount")


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare(raw: Path, output: Path, limit=1_000_000):
    import pyarrow.parquet as pq
    if file_digest(raw) != SHA256:
        raise ValueError("Source checksum differs from the frozen release")
    parquet = pq.ParquetFile(raw)
    total = parquet.metadata.num_rows
    if limit > total:
        raise ValueError("Insufficient source records")
    rng = random.Random(SEED)
    offset = rng.randrange(total)
    stride = rng.randrange(1, total)
    while math.gcd(stride, total) != 1:
        stride = (stride + 1) % total or 1
    inverse = pow(stride, -1, total)
    output.mkdir(parents=True, exist_ok=True)
    missing = {field: 0 for field in FIELDS}
    retained = malformed = 0
    ordinal = 0
    prepared = output / "records.jsonl"
    with prepared.open("wb") as stream:
        for batch in parquet.iter_batches(batch_size=16384, columns=list(FIELDS)):
            for record in batch.to_pylist():
                rank = ((ordinal - offset) * inverse) % total
                key = f"tlc-202401-{SHA256[:16]}-{ordinal:07d}"
                ordinal += 1
                if rank >= limit:
                    continue
                for field, value in record.items():
                    if isinstance(value, datetime):
                        record[field] = value.isoformat(timespec="microseconds")
                    elif isinstance(value, float) and not math.isfinite(value):
                        record[field] = None
                    if record[field] is None:
                        missing[field] += 1
                try:
                    value = canonical_bytes(record).decode("utf-8")
                except (ValueError, TypeError):
                    malformed += 1
                    continue
                stream.write(canonical_bytes({"rank": rank, "key": key, "value": value}) + b"\n")
                retained += 1
    if retained != limit or malformed:
        raise ValueError("Preparation did not produce every requested rank")
    metadata = {
        "dataset": "NYC TLC yellow taxi trip records", "release": "January 2024",
        "source_url": SOURCE, "download_url": URL, "download_sha256": SHA256,
        "download_bytes": raw.stat().st_size, "original_records": total,
        "retained_records": retained, "retained_fields": list(FIELDS),
        "source_schema": str(parquet.schema_arrow), "missing_values": missing,
        "malformed_records": malformed,
        "key_construction": "release + first 16 source checksum hex digits + zero-based physical row ordinal",
        "identifier_scope": "Unique within the checksum-pinned file; not a trip identity across releases",
        "duplicates": "No supplied trip identifier; identical field values remain distinct source rows. Ordinals are unique.",
        "sampling": "Affine permutation of physical row ordinals, not a uniform random permutation; nested rank prefixes",
        "sampling_seed": SEED, "offset": offset, "stride": stride,
        "serialization": "sorted-key compact UTF-8 JSON, ensure_ascii=False, allow_nan=False; timestamps ISO 8601 without invented timezone; null/nonfinite to null",
        "prepared_sha256": file_digest(prepared),
        "usage_terms": "NYC Open Data FAQ permits unrestricted use; AWS registry points to NYC terms. No CC license is asserted. Raw/processed records remain local.",
        "terms_urls": ["https://www.nyc.gov/opendata/get-started/FAQs", "https://www.nyc.gov/main/terms-of-use", "https://registry.opendata.aws/nyc-tlc-trip-records-pds/"],
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "dataset.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


class HistoricalStates:
    """Reconstruct an oracle on demand instead of retaining H full snapshots."""
    def __init__(self, initial, final, batches):
        self.initial, self.final, self.batches = initial, final, batches

    def __len__(self):
        return len(self.batches) + 1

    def __getitem__(self, index):
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        if index == 0:
            return self.initial
        if index == len(self.batches):
            return self.final
        state = dict(self.initial)
        for batch in self.batches[:index]:
            apply_mutations(state, batch)
        return state


def build_public_workload(spec: WorkloadSpec, directory: Path) -> Workload:
    spec.validate()
    metadata = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    if metadata["download_sha256"] != SHA256 or spec.rows > metadata["retained_records"]:
        raise ValueError("Invalid frozen public dataset")
    initial = {}
    with (directory / "records.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["rank"] < spec.rows:
                initial[row["key"]] = row["value"]
    if len(initial) != spec.rows:
        raise ValueError("Incomplete subset or duplicate keys")
    keys = sorted(initial)
    state = dict(initial)
    rng = random.Random(spec.seed)
    batches = []
    digest = hashlib.sha256(canonical_bytes({"spec": spec.__dict__, "prepared_sha256": metadata["prepared_sha256"]}))
    for key in keys:
        digest.update(canonical_bytes([key, initial[key]]) + b"\n")
    for revision in range(1, spec.commits + 1):
        batch = []
        for key in sorted(rng.sample(keys, spec.changes_per_commit)):
            old = state[key]
            value = json.loads(old)
            # Explicit synthetic fare corrections; all other original fields survive.
            value["fare_amount"] = round(float(value["fare_amount"] or 0) + 0.01, 2)
            value["total_amount"] = round(float(value["total_amount"] or 0) + 0.01, 2)
            new = canonical_bytes(value).decode("utf-8")
            batch.append(Mutation(key, True, old, True, new))
        batch = tuple(batch)
        apply_mutations(state, batch)
        batches.append(batch)
        digest.update(canonical_bytes([m.as_record() for m in batch]) + b"\n")
    batches = tuple(batches)
    return Workload(spec, initial, batches, HistoricalStates(initial, state, batches), digest.hexdigest())


def specs():
    # Baseline overlaps are executed once, not duplicated across sweeps.
    return [WorkloadSpec(name, n, h, c, SEED, payload_bytes=8) for name, n, h, c in (
        ("tlc-n10000-h10-c10", 10000, 10, 10),
        ("tlc-n100000-h10-c100", 100000, 10, 100),
        ("tlc-n1000000-h10-c1000", 1000000, 10, 1000),
        ("tlc-n100000-h50-c100", 100000, 50, 100),
        ("tlc-n100000-h10-c10", 100000, 10, 10),
        ("tlc-n100000-h10-c1000", 100000, 10, 1000),
    )]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw, args.output), indent=2))
