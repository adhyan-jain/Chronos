"""Frozen, separately reported Linux validation of the repaired Revon source.

No threshold calibration is performed. Historical paper evidence is untouched.
Run with ``python -m experiments.linux_validation --output PATH`` on Linux.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sysconfig
import subprocess
import sys
import time
import uuid

from .adapters import DoltAdapter
from .evidence_audit import _check_summary, _read_csv, DISPLAY_MODELS, METRICS, EXTRA_TELEMETRY_METRICS
from .final_benchmark import TrialRecord, MODEL_KEYS, _blocked_model_order, _write_summary, run_trial
from .paired_uncertainty import analyze
from .workloads import WorkloadSpec, build_workload, profile_specs

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260822
WARMUPS = 2
TRIALS = 7


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def json_write(path: Path, payload: object, *, exclusive: bool = False) -> None:
    with path.open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write('\n')


def case_definitions(include_public: bool = True) -> list[dict]:
    cases = [dict(spec=asdict(spec), dataset='synthetic', models=list(MODEL_KEYS),
                  threshold=4096, warmups=WARMUPS, trials=TRIALS, phase='evaluation',
                  measured_kind='measured', historical_reference='original workflow T=4096')
             for spec in profile_specs('paper', SEED + 10_000, phase='evaluation')]
    # This supplement tests a pre-existing frozen candidate, never retunes it.
    for history in (16, 64):
        spec = WorkloadSpec(f'linux-threshold-h{history}-c512', 10_000, history, 512,
                            20261008 + history, locality='repeated-key')
        cases.append(dict(spec=asdict(spec), dataset='synthetic',
                          models=['revon-log', 'revon-m', 'revon-h'], threshold=16384,
                          warmups=WARMUPS, trials=TRIALS, phase='threshold-supplement',
                          measured_kind='measured', historical_reference='held-out supplement T=16384; not an optimality claim'))
    if include_public:
        for rows, warmups, trials, kind, phase in (
                (100_000, WARMUPS, TRIALS, 'measured', 'evaluation'),
                (1_000_000, 0, 1, 'diagnostic', 'scale-feasibility')):
            spec = WorkloadSpec(f'linux-tlc-n{rows}-h10-c{rows // 1000}',
                                rows, 10, rows // 1000, 20261001, payload_bytes=8)
            cases.append(dict(spec=asdict(spec), dataset='tlc',
                              models=['revon-m', 'revon-h', 'dolt'], threshold=4096,
                              warmups=warmups, trials=trials, phase=phase,
                              measured_kind=kind, historical_reference='checksum-pinned TLC; generated fare corrections'))
    return cases


def build_case(case: dict, dataset: Path | None):
    spec = WorkloadSpec(**case['spec'])
    if case['dataset'] == 'tlc':
        from .public_dataset import build_public_workload
        return build_public_workload(spec, dataset)
    return build_workload(spec)


def execution_plan(cases: list[dict]) -> list[dict]:
    plan = []
    for case in cases:
        for kind, count in (('warmup', case['warmups']), (case['measured_kind'], case['trials'])):
            for trial in range(1, count + 1):
                order = _blocked_model_order(tuple(case['models']), seed=SEED,
                    phase=case['phase'], scenario=case['spec']['name'], kind=kind, trial=trial)
                for position, model in enumerate(order, 1):
                    plan.append(dict(phase=case['phase'], scenario=case['spec']['name'],
                        model_key=model, model=DISPLAY_MODELS[model], trial_kind=kind,
                        trial=trial, execution_order=position, threshold=case['threshold']))
    return plan


def environment() -> dict:
    output = dict(python=sys.version, python_version=platform.python_version(),
                  platform=platform.platform(), machine=platform.machine(),
                  sqlite_version=sqlite3.sqlite_version, pythonhashseed=os.environ.get('PYTHONHASHSEED'),
                  package_versions={name: importlib.metadata.version(name) for name in ('psutil', 'pyarrow')},
                  python_build={name: sysconfig.get_config_var(name) for name in ('CONFIG_ARGS', 'CC', 'CFLAGS')})
    for name, command in {
            'cpu': ['lscpu'], 'memory': ['free', '-b'], 'disk': ['df', '-B1', '.'],
            'block_devices': ['lsblk', '-o', 'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS'],
            'kernel': ['uname', '-a'], 'os_release': ['cat', '/etc/os-release'],
            'clock': ['timedatectl', 'show', '-p', 'NTPSynchronized'],
            'processes': ['ps', '-eo', 'comm,%cpu,%mem', '--sort=-%cpu'],
            'ops_agent': ['systemctl', 'is-active', 'google-cloud-ops-agent'],
            'dolt': [DoltAdapter.executable() or 'dolt', 'version']}.items():
        result = subprocess.run(command, capture_output=True, text=True)
        output[name] = dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    # Store reproducibility properties, excluding project IDs, account names and IPs.
    for name in ('machine-type', 'zone', 'cpu-platform'):
        result = subprocess.run(['curl', '-fsS', '--max-time', '5', '-H', 'Metadata-Flavor:Google',
            'http://metadata.google.internal/computeMetadata/v1/instance/' + name], capture_output=True, text=True)
        output['gcp_' + name] = result.stdout.strip().rsplit('/', 1)[-1] if result.returncode == 0 else 'unavailable'
    return output


def audit(output: Path, dataset: Path | None) -> dict:
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    protocol = json.loads((output / 'protocol.json').read_text())
    issues = []
    if digest(output / 'protocol.json') != manifest['protocol_sha256']:
        issues.append('premeasurement protocol hash changed')
    if protocol['cases'] != case_definitions(protocol['include_public']):
        issues.append('protocol differs from the fixed source-defined matrix')
    if protocol['execution_plan'] != execution_plan(protocol['cases']):
        issues.append('execution plan differs from frozen balanced order')
    for relative, expected in manifest['source_hashes'].items():
        if digest(output / 'source' / relative) != expected:
            issues.append('archived source hash mismatch: ' + relative)
        live = ROOT / relative
        if not live.exists() or digest(live) != expected:
            issues.append('executed source hash mismatch: ' + relative)
    if dataset is not None:
        from .public_dataset import SHA256
        metadata = json.loads((dataset / 'dataset.json').read_text())
        if metadata['download_sha256'] != SHA256 or digest(dataset / 'records.jsonl') != metadata['prepared_sha256']:
            issues.append('public data provenance or prepared checksum mismatch')
        if metadata != json.loads((output / 'dataset.json').read_text()):
            issues.append('public dataset metadata changed')
    raw = _read_csv(output / 'raw_results.csv')
    plan = protocol['execution_plan']
    if len(raw) != len(plan):
        issues.append(f'incomplete matrix: {len(raw)} of {len(plan)} rows')
    cases = {case['spec']['name']: case for case in protocol['cases']}
    workloads = {name: build_case(case, dataset) for name, case in cases.items()}
    for index, row in enumerate(raw):
        if index >= len(plan):
            issues.append('unexpected extra trial')
            break
        expected = plan[index]
        for field in ('phase', 'scenario', 'model', 'trial_kind', 'trial', 'execution_order'):
            if row[field] != str(expected[field]):
                issues.append(f'row {index}: wrong {field}')
        case = cases[row['scenario']]
        workload = workloads[row['scenario']]
        if row['run_id'] != manifest['run_id'] or row['python_version'] != manifest['python_version'] or row['platform'] != manifest['platform']:
            issues.append(f'row {index}: run/environment identity mismatch')
        if row['status'] != 'ok' or row['correctness'] != 'True':
            issues.append(f'row {index}: failed/unavailable/incorrect trial: {row["notes"]}')
            continue
        if row['workload_sha256'] != workload.digest or row['workload_sha256'] != protocol['workload_hashes'][row['scenario']]:
            issues.append(f'row {index}: regenerated workload differs')
        for field in ('seed', 'rows', 'commits', 'changes_per_commit', 'locality', 'payload_bytes'):
            if row[field] != ('' if case['spec'][field] is None else str(case['spec'][field])):
                issues.append(f'row {index}: wrong workload property {field}')
        if int(row['hybrid_threshold']) != case['threshold']:
            issues.append(f'row {index}: threshold was changed')
        strategy = {'snapshot': 'full-scan', 'log': 'operation-log', 'revon-m': 'merkle',
                    'revon-log': 'log', 'dolt': 'dolt-native', 'dolt-bulk': 'dolt-native'}.get(expected['model_key'])
        if expected['model_key'] == 'revon-h':
            strategy = 'log' if workload.spec.commits * workload.spec.changes_per_commit <= case['threshold'] else 'merkle'
        if row['strategy_selected'] != strategy:
            issues.append(f'row {index}: incorrect selected path')
        for metric in ('initial_import_ms', 'incremental_commit_ms', 'diff_ms', 'checkout_ms',
                       'process_tree_peak_rss_bytes', 'commit_operations_per_second'):
            if not row[metric] or float(row[metric]) <= 0:
                issues.append(f'row {index}: missing/nonpositive {metric}')
        logical = sum(len(k.encode()) + len(v.encode()) for k, v in workload.states[-1].items())
        if (int(row['logical_payload_bytes']) != logical or
                int(row['storage_bytes_minus_logical_payload_bytes']) != int(row['storage_bytes']) - logical or
                abs(float(row['storage_bytes_per_logical_payload_byte']) - int(row['storage_bytes']) / logical) > 1e-9):
            issues.append(f'row {index}: invalid storage normalization')
        if int(row['changed_keys']) != len(workload.expected_diff_keys):
            issues.append(f'row {index}: observed changed-key count differs')
        verification = json.loads((output / 'verification' / f'{index:05d}.json').read_text())
        if (verification['workload_sha256'] != workload.digest or not verification['diff_correct'] or
                verification['diff_output_sha256'] != verification['diff_oracle_sha256'] or
                not verification['all_history_verified'] or
                len(verification['historical_states']) != workload.spec.commits + 1 or
                any(h['observed_sha256'] != h['oracle_sha256'] for h in verification['historical_states'])):
            issues.append(f'row {index}: historical/diff verification failed')
        if expected['model_key'].startswith('dolt') and '2.3.1' not in row['dolt_version']:
            issues.append(f'row {index}: unexpected Dolt version')
    _check_summary(raw, _read_csv(output / 'summary.csv'), issues, METRICS + EXTRA_TELEMETRY_METRICS)
    report = dict(passed=not issues, issues=issues, raw_rows=len(raw), expected_rows=len(plan),
                  correct_rows=sum(r['correctness'] == 'True' and r['status'] == 'ok' for r in raw),
                  warmup_rows=sum(r['trial_kind'] == 'warmup' for r in raw),
                  measured_rows=sum(r['trial_kind'] == 'measured' for r in raw),
                  diagnostic_rows=sum(r['trial_kind'] == 'diagnostic' for r in raw),
                  audit_scope='source/protocol/matrix/semantic output hashes/history/summary integrity; not independent timing reproduction')
    json_write(output / 'audit.json', report)
    return report


def run(output: Path, dataset: Path | None, *, wall_limit: int = 10800) -> int:
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('this campaign requires a separate x86_64 Linux VM')
    if platform.python_version() != '3.14.3':
        raise RuntimeError('Python must be pinned to 3.14.3')
    if os.environ.get('PYTHONHASHSEED') != '20261008':
        raise RuntimeError('set PYTHONHASHSEED=20261008 before launching')
    if DoltAdapter.executable() is None:
        raise RuntimeError('Dolt must be installed before measurement')
    output.mkdir(parents=True, exist_ok=False)
    cases = case_definitions(dataset is not None)
    workloads = {case['spec']['name']: build_case(case, dataset) for case in cases}
    protocol = dict(created_utc=datetime.now(timezone.utc).isoformat(), include_public=dataset is not None,
                    cases=cases, execution_plan=execution_plan(cases),
                    workload_hashes={name: w.digest for name, w in workloads.items()},
                    no_calibration=True, trial_timeout_seconds=900, campaign_wall_limit_seconds=wall_limit,
                    limitations=['additional machine, not independent research team',
                        'hardware/OS/virtualization/storage differ; no Linux-only causal effect',
                        'repaired-source evidence separate from historical pre-repair Windows timings',
                        'one million rows: one diagnostic trial per system, no performance ranking',
                        'cached single-host repetitions do not establish population generality',
                        'Revon API versus Dolt CLI workflow, not engine-only comparison'])
    json_write(output / 'protocol.json', protocol, exclusive=True)
    source_hashes = {}
    for relative in ('versioned_db.py', 'sqlite_store.py', 'requirements.txt', 'FROZEN_SOURCE.json'):
        if not (ROOT / relative).exists():
            continue
        source_hashes[relative] = digest(ROOT / relative)
    for folder in ('experiments', 'tests', 'examples', 'revon_api'):
        for path in sorted((ROOT / folder).rglob('*.py')):
            source_hashes[path.relative_to(ROOT).as_posix()] = digest(path)
    for relative in source_hashes:
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    if dataset is not None:
        shutil.copyfile(dataset / 'dataset.json', output / 'dataset.json')
    manifest = dict(schema='revon-independent-linux-validation-v1', run_id=uuid.uuid4().hex,
                    created_utc=datetime.now(timezone.utc).isoformat(), python_version=platform.python_version(),
                    platform=platform.platform(), protocol_sha256=digest(output / 'protocol.json'),
                    source_hashes=source_hashes, environment=environment())
    json_write(output / 'manifest.json', manifest, exclusive=True)
    records = []
    deadline = time.monotonic() + wall_limit
    plan = protocol['execution_plan']
    try:
        with (output / 'raw_results.csv').open('x', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=[f.name for f in fields(TrialRecord)])
            writer.writeheader()
            stream.flush()
            for index, planned in enumerate(plan):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError('campaign exceeded predeclared wall limit')
                case = next(c for c in cases if c['spec']['name'] == planned['scenario'])
                print(f'[{index + 1}/{len(plan)}] {planned}', flush=True)
                record = run_trial(run_id=manifest['run_id'], phase=planned['phase'],
                    workload=workloads[planned['scenario']], model_key=planned['model_key'],
                    trial_kind=planned['trial_kind'], trial=planned['trial'],
                    threshold=planned['threshold'], execution_order=planned['execution_order'],
                    scratch_root=output / '.work', public_dataset=dataset if case['dataset'] == 'tlc' else None,
                    verification_path=output / 'verification' / f'{index:05d}.json',
                    timeout_seconds=min(900, remaining), verify_all_history=True)
                records.append(record)
                writer.writerow(asdict(record))
                stream.flush()
                os.fsync(stream.fileno())
                json_write(output / 'progress.json', dict(completed=len(records), total=len(plan),
                    last_status=record.status, last_notes=record.notes, updated_utc=datetime.now(timezone.utc).isoformat()))
                print(f'  {record.status}: diff={record.diff_ms}ms, RSS={record.process_tree_peak_rss_bytes}; {record.notes}', flush=True)
                if record.status != 'ok' or not record.correctness:
                    raise RuntimeError('trial failed; retained and stopped instead of silently dropping it')
    except Exception as exc:
        json_write(output / 'failure.json', dict(error=repr(exc), completed=len(records), total=len(plan)))
        raise
    finally:
        _write_summary(output / 'summary.csv', records)
    report = audit(output, dataset)
    analyze(output / 'raw_results.csv', output / 'paired_uncertainty.csv')
    json_write(output / 'completed.json', dict(finished_utc=datetime.now(timezone.utc).isoformat(), **report))
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['passed'] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.audit:
        report = audit(args.output, args.dataset)
        print(json.dumps(report, indent=2))
        return 0 if report['passed'] else 1
    return run(args.output, args.dataset)


if __name__ == '__main__':
    raise SystemExit(main())
