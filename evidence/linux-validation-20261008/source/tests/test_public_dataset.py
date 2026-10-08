"""Public record mapping, nested sampling and oracle regressions."""
import json
import unittest
import uuid
from pathlib import Path
from experiments.adapters import canonical_bytes, canonical_state_bytes, decode_state_bytes
from experiments.public_dataset import SHA256, build_public_workload
from experiments.workloads import WorkloadSpec


class PublicDatasetTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("tmp") / f"public-test-{uuid.uuid4().hex}"
        self.path.mkdir(parents=True)
        (self.path / "dataset.json").write_text(json.dumps({"download_sha256": SHA256,
            "retained_records": 20, "prepared_sha256": "fixture"}))
        with (self.path / "records.jsonl").open("wb") as f:
            for i in reversed(range(20)):
                value = canonical_bytes({"fare_amount": 12.5, "total_amount": 16.2,
                    "passenger_count": None, "location": "Vellore", "distance": 3.75}).decode()
                f.write(canonical_bytes({"rank": i, "key": f"trip-{i:02d}", "value": value}) + b"\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.path, ignore_errors=True)

    def test_nested_samples_and_repeatable_history(self):
        small = build_public_workload(WorkloadSpec("small", 10, 10, 2, 42, 8), self.path)
        large = build_public_workload(WorkloadSpec("large", 20, 10, 2, 42, 8), self.path)
        again = build_public_workload(small.spec, self.path)
        self.assertEqual(set(small.initial), {f"trip-{i:02d}" for i in range(10)})
        self.assertTrue(small.initial.items() <= large.initial.items())
        self.assertEqual(small.digest, again.digest)
        self.assertEqual(small.batches, again.batches)

    def test_history_preserves_nulls_fields_and_exact_changes(self):
        workload = build_public_workload(WorkloadSpec("history", 20, 50, 3, 42, 8), self.path)
        previous = workload.initial
        for index, batch in enumerate(workload.batches, 1):
            current = decode_state_bytes(canonical_state_bytes(workload.states[index]))
            self.assertEqual(len(current), 20)
            self.assertEqual(sum(previous[k] != current[k] for k in current), 3)
            for m in batch:
                self.assertEqual(m.old_value, previous[m.key])
                self.assertEqual(m.new_value, current[m.key])
                value = json.loads(m.new_value)
                self.assertIsNone(value["passenger_count"])
                self.assertEqual(value["location"], "Vellore")
                self.assertEqual(value["distance"], 3.75)
            previous = current
        self.assertEqual(previous, workload.states[-1])


if __name__ == "__main__":
    unittest.main()
