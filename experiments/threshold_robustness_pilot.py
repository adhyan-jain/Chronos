"""Isolated exploratory replication; never edits manuscripts or frozen evidence.

Run from the repository root with the explicit experiment interpreter.
Only experimental instances receive candidate thresholds. Production defaults
and imported source files remain unchanged. See the frozen manifest for scope.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import psutil

from experiments.adapters import canonical_diff_bytes, decode_diff_bytes, value_digest
from experiments.threshold_validation import selection
from experiments.workloads import WorkloadSpec, build_workload
from sqlite_store import SQLiteRevonRepository

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [('log', 0), ('merkle', 0)] + [('hybrid', t) for t in (4096, 16384, 32768, 65536, 131072)]
SEEDS = (20261021, 20261022, 20261023)
PROFILES = [(10000, 256, 'repeated-key'), (100000, 64, 'spread')]


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def emit(path, records):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def measured_query(repo, spec, strategy, threshold, kind, block, order, cache, oracle):
    repo.database.hybrid_log_threshold = threshold
    started_utc = utc()
    rss_before = psutil.Process().memory_info().rss
    before = time.perf_counter_ns()
    entries = repo.diff_versions(1, spec['commits'] + 1, strategy)
    output = canonical_diff_bytes({e.key: (e.old_value, e.new_value) for e in entries})
    elapsed = (time.perf_counter_ns() - before) / 1e6
    stats = asdict(repo.last_diff_stats)
    output_hash = hashlib.sha256(output).hexdigest()
    assert output_hash == oracle, 'semantic output does not match oracle'
    expected_path = strategy if strategy != 'hybrid' else ('log' if spec['operations'] <= threshold else 'merkle')
    assert stats['strategy'] == expected_path
    start = time.perf_counter_ns()
    decision = selection(repo.database, 1, spec['commits'] + 1, threshold)
    decision_ms = (time.perf_counter_ns() - start) / 1e6
    assert decision['operations'] == spec['operations']
    return dict(case=spec['name'], rows=spec['rows'], commits=spec['commits'],
        locality=spec['locality'], seed=spec['seed'], operations=spec['operations'],
        changes_per_commit=spec['operations'] // spec['commits'], cache_condition=cache,
        trial_kind=kind, block=block, execution_order=order, strategy=strategy,
        threshold=threshold, selected=stats['strategy'], diff_ms=elapsed,
        decision_probe_ms=decision_ms, output_sha256=output_hash, output_bytes=len(output),
        output_entries=len(entries), correctness=True, started_utc=started_utc,
        pythonhashseed=os.environ.get('PYTHONHASHSEED'), process_rss_before_bytes=rss_before,
        process_rss_after_bytes=psutil.Process().memory_info().rss,
        available_ram_bytes=psutil.virtual_memory().available, **{k:v for k,v in stats.items() if k!='strategy'})


def build_worker(directory, spec):
    work_spec = WorkloadSpec(spec['name'], spec['rows'], spec['commits'],
        spec['operations'] // spec['commits'], spec['seed'], locality=spec['locality'])
    work_spec.validate()
    assert spec['operations'] % spec['commits'] == 0
    start = time.perf_counter()
    workload = build_workload(work_spec)
    workload_ms = (time.perf_counter() - start) * 1000
    expected = {k:(value_digest(workload.states[0].get(k)), value_digest(workload.states[-1].get(k)))
                for k in workload.expected_diff_keys}
    touched = {m.key for batch in workload.batches for m in batch}
    mix = {'updates':0, 'inserts':0, 'deletes':0}
    for batch in workload.batches:
        assert len(batch) == work_spec.changes_per_commit
        for m in batch:
            mix['updates' if m.old_exists and m.new_exists else 'inserts' if m.new_exists else 'deletes'] += 1
    oracle_bytes = canonical_diff_bytes({k:(workload.states[0].get(k), workload.states[-1].get(k)) for k in workload.expected_diff_keys})
    assert decode_diff_bytes(oracle_bytes) == expected
    oracle_hash = hashlib.sha256(oracle_bytes).hexdigest()
    history_checks = {v:workload.states[v-1] for v in (1, spec['commits']//2+1, spec['commits']+1)}
    metadata = dict(spec=spec, workload_sha256=workload.digest, oracle_sha256=oracle_hash,
        actual_operations=sum(len(b) for b in workload.batches), distinct_keys_touched=len(touched),
        repeated_operation_fraction=1-len(touched)/spec['operations'],
        operations_per_distinct_key=spec['operations']/len(touched),
        final_diff_entries=len(expected), final_diff_bytes=len(oracle_bytes), mutation_mix=mix,
        workload_generation_ms=workload_ms, started_utc=utc())
    save(directory/'oracle.json', metadata)
    start = time.perf_counter()
    with SQLiteRevonRepository.create(directory/'repository.sqlite', hybrid_log_threshold=4096) as repo:
        root = repo.commit(workload.initial, message='isolated pilot initial')
        for index, batch in enumerate(workload.batches, 1):
            root = repo.apply_changes(root, puts={m.key:m.new_value for m in batch if m.new_exists},
                deletes={m.key for m in batch if not m.new_exists}, message=f'pilot revision {index}')
        metadata['construction_ms'] = (time.perf_counter()-start)*1000
        assert selection(repo.database,1,spec['commits']+1,4096)['operations'] == spec['operations']
        del workload, oracle_bytes, touched
        gc.collect()
        records = []
        for kind, blocks in [('warmup',2), ('measured',5)]:
            for block in range(1,blocks+1):
                order = list(CONFIGS)
                random.Random(f'{spec["name"]}:{kind}:{block}').shuffle(order)
                for position, (strategy,threshold) in enumerate(order,1):
                    row = measured_query(repo,spec,strategy,threshold,kind,block,position,'warmed-built',oracle_hash)
                    records.append(row)
                    with (directory/'queries.jsonl').open('a',encoding='utf-8') as stream:
                        stream.write(json.dumps(row)+'\n')
        reverse_expected = {k:(b,a) for k,(a,b) in expected.items()}
        for strategy in ('log','merkle','hybrid'):
            assert repo.diff_versions(1,1,strategy) == []
            entries = repo.diff_versions(spec['commits']+1,1,strategy)
            assert decode_diff_bytes(canonical_diff_bytes({e.key:(e.old_value,e.new_value) for e in entries})) == reverse_expected
        for version,state in history_checks.items():
            assert repo.checkout(version) == state
        metadata['integrity'] = asdict(repo.verify_integrity())
        metadata['components'] = [dict(kind=r[0],objects=r[1],payload_bytes=r[2]) for r in
            repo._connection.execute('SELECT kind,COUNT(*),SUM(length(payload)) FROM objects GROUP BY kind')]
    metadata['storage_bytes'] = (directory/'repository.sqlite').stat().st_size
    metadata['closed_file_sha256'] = sha(directory/'repository.sqlite')
    save(directory/'warm_result.json', dict(**metadata, records=records, semantic_checks=True, completed_utc=utc()))


def fresh_worker(config):
    directory = Path(config['directory'])
    oracle = json.loads((directory/'oracle.json').read_text())
    start = time.perf_counter()
    with SQLiteRevonRepository.open(directory/'repository.sqlite', verify=True) as repo:
        open_ms = (time.perf_counter()-start)*1000
        # No diff, identity, ancestry probe or checkout occurs before this timer.
        row = measured_query(repo,oracle['spec'],config['strategy'],config['threshold'],
            'measured',config['block'],config['order'],'fresh-process-reopened',oracle['oracle_sha256'])
        row['open_verify_ms'] = open_ms
        row['open_plus_diff_ms'] = open_ms+row['diff_ms']
        assert repo.checkout(oracle['spec']['commits']+1) is not None
    save(Path(config['output']),row)


def launch(args, logfile, timeout, rss_limit):
    env = os.environ.copy()
    env['PYTHONHASHSEED'] = str(args.pop('hash_seed'))
    env['PYTHONUNBUFFERED'] = '1'
    config = Path(logfile).with_suffix('.config.json')
    save(config,args)
    start = time.perf_counter()
    peak = 0
    min_available = psutil.virtual_memory().available
    reason = None
    with Path(logfile).open('wb') as stream:
        child = subprocess.Popen([sys.executable,'-m','experiments.threshold_robustness_pilot','--worker-config',str(config)],
            cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        process = psutil.Process(child.pid)
        while child.poll() is None:
            try:
                rss = process.memory_info().rss
                peak = max(peak,rss)
                min_available = min(min_available,psutil.virtual_memory().available)
                if rss>rss_limit:
                    reason = f'RSS exceeded {rss_limit} bytes'
                elif time.perf_counter()-start>timeout:
                    reason = f'worker exceeded {timeout} seconds'
                elif min_available<192*1024**2:
                    reason = 'available system RAM fell below 192 MiB'
                if reason:
                    child.kill()
                    break
            except psutil.NoSuchProcess:
                break
            time.sleep(.1)
        child.wait()
    resource = dict(wall_seconds=time.perf_counter()-start,peak_rss_bytes=peak,
        minimum_available_ram_bytes=min_available,returncode=child.returncode,
        failure_reason=reason,hash_seed=env['PYTHONHASHSEED'],sampler_interval_ms=100)
    save(Path(logfile).with_suffix('.resource.json'),resource)
    if child.returncode or reason:
        raise RuntimeError(json.dumps(resource))
    return resource


def verify_protected(directory):
    before = json.loads((directory/'protected_before.json').read_text())
    changed = [p for p,h in before['files'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    current_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    check = dict(passed=not changed and current_head==before['git_head'],
        protected_files=len(before['files']),changed_files=changed,
        commits_unchanged=current_head==before['git_head'],checked_utc=utc())
    save(directory/'protected_after.json',check)
    assert check['passed'],check


def main(directory):
    directory = directory.resolve()
    allowed = (ROOT/'.codex_tmp/threshold_robustness_pilot').resolve()
    assert directory.is_relative_to(allowed), 'pilot output must remain local and isolated'
    assert (directory/'protected_before.json').exists(), 'capture protected baseline before authoring'
    sources = ['experiments/threshold_robustness_pilot.py','experiments/analyze_threshold_robustness_pilot.py',
        'experiments/threshold_validation.py','experiments/workloads.py','experiments/adapters.py','sqlite_store.py','versioned_db.py']
    hashes = {p:sha(ROOT/p) for p in sources}
    cases = [dict(name=f'n{n}-h{h}-{loc}-o{o}-s{s}',rows=n,commits=h,locality=loc,operations=o,seed=s)
        for n,h,loc in PROFILES for o in (65536,32768,131072) for s in SEEDS]
    for case in cases:
        assert case['operations'] % case['commits'] == 0
        WorkloadSpec(case['name'],case['rows'],case['commits'],case['operations']//case['commits'],case['seed'],locality=case['locality']).validate()
    manifest_path = directory/'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert manifest['source_sha256']==hashes,'source changed after freeze'
    else:
        manifest = dict(study='isolated threshold robustness pilot',frozen_utc=utc(),
            profiles=PROFILES,seeds=SEEDS,cases=cases,configs=CONFIGS,warmups=2,warmed_blocks=5,
            fresh_subset='65,536 operations, both profiles, all seeds',fresh_blocks=3,
            source_sha256=hashes,python=sys.version,python_executable=sys.executable,
            platform=platform.platform(),processor=platform.processor(),physical_cpus=psutil.cpu_count(logical=False),
            logical_cpus=psutil.cpu_count(),ram=psutil.virtual_memory()._asdict(),
            disk=psutil.disk_usage(str(ROOT))._asdict(),psutil_version=psutil.__version__,
            per_worker_timeout_seconds=600,fresh_worker_timeout_seconds=180,rss_limit_bytes=int(1.75*1024**3),
            first_case_estimated_budget_seconds=2400,provisional_practical_difference=.05,
            analysis='exploratory seed-level paired medians; query IQRs; all seeds shown; no population CI; no selection/held-out claims',
            cache='fresh process eagerly loads and verifies every persistent object; OS filesystem cache is not cleared; open latency separate',
            timing='diff_versions plus common canonical output; decision probe and correctness outside; probe not causally subtracted',
            resource_reduction='after first completed case: estimate from wall/RSS only, before viewing latency trends; if estimate exceeds 40 minutes run all 9 repeated-key cases plus 3 spread cases at 65,536; retain all failures',
            system_resource_floor_bytes=192*1024**2,
            geometry='branching factor 8 and depth 4; constructor production default is 128 and is not changed; explicit experimental instances start at original study threshold 4096')
        save(manifest_path,manifest)
        for source in sources:
            target = directory/'source'/source
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/source,target)
    case_results=[]
    failure_rows=[]
    resource_gate=None
    if (directory/'resource_gate.json').exists():
        resource_gate=json.loads((directory/'resource_gate.json').read_text())
    try:
        for index,spec in enumerate(cases):
            if resource_gate and resource_gate['reduce_scope'] and spec['rows']==100000 and spec['operations']!=65536:
                failure_rows.append(dict(case=spec['name'],status='not_run_resource_scope_reduction'))
                continue
            case_dir=directory/'cases'/spec['name']
            case_dir.mkdir(parents=True,exist_ok=True)
            if (case_dir/'result.json').exists():
                result=json.loads((case_dir/'result.json').read_text())
                case_results.append(result)
                print(f'RESUMED {spec["name"]}',flush=True)
                continue
            if psutil.virtual_memory().available<512*1024**2:
                failure_rows.append(dict(case=spec['name'],status='not_run_ram_floor'))
                save(directory/'failures.json',failure_rows)
                continue
            started=time.perf_counter()
            try:
                if not (case_dir/'warm_result.json').exists():
                    if (case_dir/'repository.sqlite').exists():
                        raise RuntimeError('Incomplete previous database retained; use a fresh output directory')
                    print(f'START {spec["name"]}',flush=True)
                    warm_resource=launch(dict(mode='build',directory=str(case_dir),spec=spec,hash_seed=spec['seed']),
                        case_dir/'build.log',600,manifest['rss_limit_bytes'])
                else:
                    warm_resource=json.loads((case_dir/'build.resource.json').read_text())
                warm=json.loads((case_dir/'warm_result.json').read_text())
                resources=[warm_resource]
                fresh=[]
                if spec['operations']==65536:
                    for block in range(1,4):
                        order=list(CONFIGS)
                        random.Random(f'{spec["name"]}:fresh:{block}').shuffle(order)
                        for position,(strategy,threshold) in enumerate(order,1):
                            tag=f'fresh-b{block}-{strategy}-t{threshold}'
                            output=case_dir/(tag+'.json')
                            if not output.exists():
                                resource=launch(dict(mode='fresh',directory=str(case_dir),strategy=strategy,
                                    threshold=threshold,block=block,order=position,output=str(output),hash_seed=spec['seed']+block),
                                    case_dir/(tag+'.log'),180,manifest['rss_limit_bytes'])
                            else:
                                resource=json.loads((case_dir/(tag+'.resource.json')).read_text())
                            resources.append(resource)
                            fresh.append(json.loads(output.read_text()))
                else:
                    # Reopen and verify correctness separately from warm query timing.
                    output=case_dir/'reopen_check.json'
                    resource=launch(dict(mode='fresh',directory=str(case_dir),strategy='merkle',threshold=0,
                        block=0,order=0,output=str(output),hash_seed=spec['seed']),case_dir/'reopen_check.log',180,manifest['rss_limit_bytes'])
                    resources.append(resource)
                    warm['untimed_reopen_correctness']=json.loads(output.read_text())['correctness']
                assert sha(case_dir/'repository.sqlite')==warm['closed_file_sha256'],'query changed SQLite file'
                result=dict(**warm,fresh_records=fresh,resources=resources,
                    total_wall_seconds=time.perf_counter()-started,completed_pilot_utc=utc())
                if index==0 and not resource_gate:
                    # Use resource fields only. Do not inspect diff medians for this decision.
                    estimate=result['total_wall_seconds']*len(cases)
                    resource_gate=dict(created_utc=utc(),first_case_wall_seconds=result['total_wall_seconds'],
                        first_case_peak_rss_bytes=max(r['peak_rss_bytes'] for r in resources),
                        conservative_estimated_full_seconds=estimate,reduce_scope=estimate>2400,
                        decision_basis='wall time and process RSS only; no query-latency trend inspected')
                    save(directory/'resource_gate.json',resource_gate)
                    print('RESOURCE GATE '+json.dumps(resource_gate),flush=True)
                save(case_dir/'result.json',result)
                # Verified reproducible scratch DBs are removed, with hashes retained.
                (case_dir/'repository.sqlite').unlink()
                case_results.append(result)
                save(directory/'progress.json',dict(completed=len(case_results),planned=len(cases),updated_utc=utc()))
                print(f'DONE {spec["name"]}; wall={result["total_wall_seconds"]:.1f}s; peak={max(r["peak_rss_bytes"] for r in resources)/1024**2:.0f}MiB',flush=True)
            except Exception as error:
                failure_rows.append(dict(case=spec['name'],status='failed',error=str(error),traceback=traceback.format_exc(),utc=utc()))
                save(directory/'failures.json',failure_rows)
                print(f'FAILED {spec["name"]}: {error}',flush=True)
        records=[r for c in case_results for r in c['records']+c['fresh_records']]
        if records:emit(directory/'raw_results.csv', [{**r,'open_verify_ms':r.get('open_verify_ms',''),'open_plus_diff_ms':r.get('open_plus_diff_ms','')} for r in records])
        save(directory/'results.json',case_results)
        save(directory/'failures.json',failure_rows)
        save(directory/'audit.json',dict(completed_cases=len(case_results),planned_cases=len(cases),
            warm_queries=sum(len(c['records']) for c in case_results),warm_measured=sum(r['trial_kind']=='measured' for c in case_results for r in c['records']),
            fresh_queries=sum(len(c['fresh_records']) for c in case_results),all_correct=all(r['correctness'] for r in records),
            failures=len([x for x in failure_rows if x['status']=='failed']),not_run=len([x for x in failure_rows if x['status']!='failed']),
            finished_utc=utc(),source_unchanged=all(sha(ROOT/p)==h for p,h in hashes.items())))
    finally:
        verify_protected(directory)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    parser.add_argument('--worker-config',type=Path)
    args=parser.parse_args()
    if args.worker_config:
        cfg=json.loads(args.worker_config.read_text())
        if cfg['mode']=='build':build_worker(Path(cfg['directory']),cfg['spec'])
        else:fresh_worker(cfg)
    else:
        assert args.output is not None
        main(args.output)
