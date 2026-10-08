# JSON value ownership and identity

Revon accepts JSON nulls, booleans, finite numbers, strings, lists and objects
with string keys. Values use Python's built-in representations (`None`, `bool`,
`int`, finite `float`, `str`, `list`, `dict`). Python-only coercions such as tuples
or numeric object keys are rejected on new writes, as are cyclic containers and
non-finite numbers. Validation completes before interning a batch's objects.

The existing v1 encoding remains sorted-key, compact JSON with UTF-8 text and
`allow_nan=False`. Equality follows these encoded bytes. In particular, `true`,
`1`, `1.0`, `0.0` and `-0.0` retain their encoded distinctions. Object key order
does not affect identity. This is the project's Python encoding contract, not
a cross-language canonical-JSON standard.

Writes detach mutable containers before hashing or retaining them. `get`,
`materialize`, `checkout`, structured diffs and diagnostic node/changeset views
export detached values. Immutable scalar objects can be shared. The diagnostic
stores are read-only mappings; mutating an exported node or changeset does not
change history. Internal names beginning with `_` are not mutation APIs.

SQLite storage uses the unchanged schema and object encoding. Existing stored
JSON payloads reopen without root/commit rehashing. Values previously supplied
as coercible Python objects already exist as their JSON encodings on disk.
Previously suppressed updates or unpersisted caller mutations cannot be
recovered automatically from history that never recorded them.

Regression coverage: `python -m unittest tests.test_json_contract -v`.
The oracle uses JSON bytes rather than Python equality. It covers input/read
aliases, diagnostic exports, full and incremental writes, typed transitions,
null/absence, cancellation, reverse intervals, all diff modes, addressed hashes
and SQLite reopen. Existing versioning, API and experiment tests remain part
of `python -m unittest discover -s tests -v`.

## Performance provenance

Published historical tables belong to their archived implementation snapshots.
The repair changes copying and comparison work, so those timings must not be
represented as measurements of the current implementation.

`evidence/referee-repair-overhead-20261003` retains original/repaired source
snapshots, their hashes, a frozen bounded protocol, raw before/after timings,
paired summary ratios and legacy-reopen checks. To repeat the bounded protocol
using the current implementation, choose a new output directory:

```bash
PYTHONHASHSEED=20261003 python -m experiments.referee_repair_check \
  --baseline evidence/referee-repair-overhead-20261003/source_before \
  --output evidence/referee-repair-overhead-new
```

The command snapshots the current source as its repaired variant. To reproduce
the exact retained variant, first check the current file hashes against the
bundle's `source_after` entries or use a separate checkout populated from those
two files. Do not overwrite the original evidence.

`python tools/referee_revision.py` independently derives the static-policy,
startup, geometry, RSS and nested-block analyses from the named archived CSVs.
Its output manifest lists every input checksum and the analysis-script hash.
This reanalysis does not create new timing observations.
