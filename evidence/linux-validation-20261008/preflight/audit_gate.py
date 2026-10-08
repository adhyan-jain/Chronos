"""Small real-worker gate plus deliberate evidence-corruption checks."""
from pathlib import Path
from unittest.mock import patch
import csv
import json
from experiments import linux_validation as study
from experiments.workloads import WorkloadSpec
from dataclasses import asdict

base = Path.home() / 'revon-validation/preflight'
output = base / 'audit-gate'
tiny = dict(spec=asdict(WorkloadSpec('audit-gate', 100, 2, 10, 91)), dataset='synthetic',
            models=['snapshot', 'revon-h', 'dolt'], threshold=4096, warmups=0, trials=1,
            phase='evaluation', measured_kind='measured', historical_reference='preflight only')
with patch.object(study, 'case_definitions', return_value=[tiny]):
    assert study.run(output, None, wall_limit=120) == 0
    raw = output / 'raw_results.csv'
    original = raw.read_bytes()
    rows = original.decode().splitlines(keepends=True)
    raw.write_text(''.join(rows[:-1]))
    assert not study.audit(output, None)['passed'], 'missing trial was accepted'
    raw.write_bytes(original)
    verification = output / 'verification/00000.json'
    original_verification = verification.read_bytes()
    content = json.loads(original_verification)
    content['diff_output_sha256'] = '0' * 64
    verification.write_text(json.dumps(content))
    assert not study.audit(output, None)['passed'], 'corrupt diff output was accepted'
    verification.write_bytes(original_verification)
    protocol = output / 'protocol.json'
    original_protocol = protocol.read_bytes()
    content = json.loads(original_protocol)
    content['cases'][0]['threshold'] = 1
    protocol.write_text(json.dumps(content))
    assert not study.audit(output, None)['passed'], 'altered frozen threshold was accepted'
    protocol.write_bytes(original_protocol)
    assert study.audit(output, None)['passed']
study.json_write(base / 'audit-negative-controls.json', dict(passed=True,
    rejected=['missing trial', 'corrupted observed diff hash', 'changed frozen threshold'],
    scope='Real Linux Snapshot/Revon-H/Dolt workers on 100 rows; preflight only'))
print('AUDIT NEGATIVE CONTROLS PASSED')
