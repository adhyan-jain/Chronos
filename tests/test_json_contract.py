"""Regression checks for addressed JSON identity and ownership at API boundaries."""

import hashlib
import json
from pathlib import Path
import uuid
import unittest

from sqlite_store import SQLiteRevonRepository
from versioned_db import VersionedDatabase


def encoded(value):
    # Independent test oracle: Python equality hides True/1 and -0.0/0.0.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


class JsonContractTests(unittest.TestCase):
    def assert_hashes(self, db):
        for digest, node in db.node_store.items():
            self.assertEqual(hashlib.sha256(encoded(node)).hexdigest(), digest)
        for digest, changes in db.changeset_store.items():
            payload = encoded([change.as_record() for change in changes])
            self.assertEqual(hashlib.sha256(b"revon:changeset:v1\0" + payload).hexdigest(), digest)

    def test_inputs_and_all_exported_values_are_detached(self):
        db = VersionedDatabase()
        a = {"items": [1, {"flag": True}]}
        first = db.commit({"k": a})
        a["items"][1]["flag"] = False
        b = {"items": [2, {"flag": False}]}
        second = db.apply_changes(first, puts={"k": b})
        b["items"].append("mutated")
        originals = [{"k": {"items": [1, {"flag": True}]}},
                     {"k": {"items": [2, {"flag": False}]}}]
        for version, root in enumerate((first, second), 1):
            db.get(root, "k")["items"].append("get")
            db.checkout(version)["k"]["items"].append("checkout")
            db.materialize(root)["k"]["items"].append("materialize")
        for strategy in ("log", "merkle", "hybrid"):
            for left, right in ((1, 2), (2, 1)):
                entry = db.diff_versions(left, right, strategy)[0]
                entry.old_value["items"].append("diff old")
                entry.new_value["items"].append("diff new")
        for changes in db.changeset_store.values():
            for change in changes:
                if change.new_exists:
                    change.new_value["items"].append("diagnostic changeset")
                    change.as_record()["new"]["items"].append("record")
        for node in db.node_store.values():
            if node["type"] == "leaf":
                node["entries"][0][1]["items"].append("diagnostic node")
        for version, expected in enumerate(originals, 1):
            self.assertEqual(encoded(db.checkout(version)), encoded(expected))
        with self.assertRaises(TypeError):
            db.node_store[first] = {}
        self.assert_hashes(db)

    def test_typed_transitions_and_cancellation_in_both_write_modes(self):
        values = [True, 1, 1.0, False, 0, 0.0, -0.0, None,
                  {"a": [True]}, {"a": [1]}, {"a": [1.0]}]
        for full in (False, True):
            db = VersionedDatabase()
            root = db.commit({})
            states = [{}]
            for value in values + list(reversed(values)):
                state = {"k": value}
                root = db.commit(state) if full else db.apply_changes(root, puts=state)
                states.append(state)
                self.assertEqual(encoded(db.checkout(db.head)), encoded(state))
            root = db.commit({}) if full else db.apply_changes(root, deletes=["k"])
            states.append({})
            for left in range(1, len(states)+1):
                for right in range(1, len(states)+1):
                    a, b = states[left-1], states[right-1]
                    for strategy in ("log", "merkle", "hybrid"):
                        entries = db.diff_versions(left, right, strategy)
                        if encoded(a) == encoded(b):
                            self.assertEqual(entries, [])
                        else:
                            self.assertEqual(len(entries), 1)
                            e = entries[0]
                            self.assertEqual(e.key, "k")
                            self.assertEqual(e.change_type, "added" if not a else "deleted" if not b else "modified")
                            self.assertEqual(encoded(e.old_value), encoded(a.get("k")))
                            self.assertEqual(encoded(e.new_value), encoded(b.get("k")))
            self.assert_hashes(db)

    def test_rejected_non_json_values_do_not_partially_write(self):
        cyclic = []; cyclic.append(cyclic)
        for value in (float("nan"), float("inf"), (1, 2), {1: "x"}, {"x": object()}, cyclic):
            db = VersionedDatabase()
            root = db.commit({"safe": [1]})
            for full in (False, True):
                with self.assertRaises(TypeError):
                    if full:
                        db.commit({"invalid": value})
                    else:
                        db.apply_changes(root, puts={"invalid": value})
                self.assertEqual(db.head, 1)
                self.assertEqual(encoded(db.checkout(1)), encoded({"safe": [1]}))
                self.assert_hashes(db)

    def test_sqlite_live_persisted_and_reopened_values_agree(self):
        base = Path(__file__).parent / "test_data"
        base.mkdir(exist_ok=True)
        path = base / ("json-contract-" + uuid.uuid4().hex + ".db")
        try:
            with SQLiteRevonRepository.create(path) as repo:
                value = {"a": [True]}
                root = repo.commit({"k": value})
                value["a"].append(99)
                root = repo.apply_changes(root, puts={"k": {"a": [1]}})
                repo.get(root, "k")["a"].append(88)
                repo.checkout(1)["k"]["a"].append(77)
                repo.diff_versions(1, 2, "log")[0].new_value["a"].append(66)
                expected = [encoded(repo.checkout(v)) for v in (1, 2)]
                hashes = dict(repo.versions)
                repo.verify_integrity()
                self.assert_hashes(repo.database)
            with SQLiteRevonRepository.open(path) as repo:
                self.assertEqual(dict(repo.versions), hashes)
                self.assertEqual([encoded(repo.checkout(v)) for v in (1, 2)], expected)
                self.assertEqual(expected, [b'{"k":{"a":[true]}}', b'{"k":{"a":[1]}}'])
                for strategy in ("log", "merkle", "hybrid"):
                    self.assertEqual(encoded(repo.diff_versions(1, 2, strategy)[0].new_value), b'{"a":[1]}')
                    self.assertEqual(encoded(repo.diff_versions(2, 1, strategy)[0].new_value), b'{"a":[true]}')
                repo.verify_integrity()
                self.assert_hashes(repo.database)
        finally:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
