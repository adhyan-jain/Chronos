"""Predeclared Linux geometry and zero-aware telemetry supplement; no retuning."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from . import linux_validation as lv
from .trie_sensitivity import DEFAULT_CONFIGS, TrieConfig, run_sensitivity_trial, SensitivityRecord, _write_summary
from .workloads import WorkloadSpec, build_workload

SPEC = WorkloadSpec('linux-geometry-n10000-h10-c100', 10000, 10, 100, 20260824, payload_bytes=32)

def telemetry_cases(include_public=False):
    return [dict(spec=asdict(WorkloadSpec('linux-telemetry-n10000-h10-c100', 10000, 10, 100, 20261008)),
        dataset='synthetic', models=['revon-m', 'revon-h', 'dolt'], threshold=4096,
        warmups=2, trials=7, phase='evaluation', measured_kind='measured',
        historical_reference='separate counter-repair supplement; not pooled with original campaign')]

def geometry(output):
    target = output / 'geometry'
    target.mkdir(exist_ok=False)
    plan=[]
    for kind, count in [('warmup',2),('measured',7)]:
        for trial in range(1,count+1):
            # Rotate the same five geometries so drift is not confounded with configuration.
            shift=(trial-1)%len(DEFAULT_CONFIGS)
            order=DEFAULT_CONFIGS[shift:]+DEFAULT_CONFIGS[:shift]
            for position, config in enumerate(order,1):
                plan.append(dict(kind=kind, trial=trial, order=position, config=asdict(config)))
    lv.json_write(target/'protocol.json', dict(spec=asdict(SPEC), plan=plan,
        scope='fresh worker per geometry trial; all historical states and endpoint diff checked outside timers; no RSS comparison',
        timeout_seconds=900), exclusive=True)
    records=[]
    for index, item in enumerate(plan):
        destination=target/f'{index:03d}.json'
        result=subprocess.run([sys.executable,'-m','experiments.linux_final_supplement',
            '--worker',json.dumps(item),'--result',str(destination)],capture_output=True,text=True,timeout=900)
        if result.returncode:
            raise RuntimeError(result.stderr)
        record=SensitivityRecord(**json.loads(destination.read_text()))
        records.append(record)
        with (target/'raw_results.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(asdict(record)))
            writer.writeheader();writer.writerows(asdict(r) for r in records)
        print(f'geometry {index+1}/{len(plan)} {record.config}: {record.status}',flush=True)
        if record.status!='ok' or not record.correctness:
            raise RuntimeError('geometry failure retained')
    _write_summary(target/'summary.csv',records)
    audit_geometry(output)

def audit_geometry(output):
    target=output/'geometry'
    protocol=json.loads((target/'protocol.json').read_text())
    rows=list(csv.DictReader((target/'raw_results.csv').open()))
    issues=[]
    if len(rows)!=45:issues.append('expected 45 geometry executions')
    expected_hash=build_workload(SPEC).digest
    for row,item in zip(rows,protocol['plan']):
        cfg=TrieConfig(**item['config'])
        if (row['status']!='ok' or row['correctness']!='True' or row['config']!=cfg.label
            or row['workload_sha256']!=expected_hash or int(row['trial'])!=item['trial']
            or row['trial_kind']!=item['kind']):issues.append('geometry identity/correctness mismatch')
    lv.json_write(target/'audit.json',dict(passed=not issues,issues=issues,executions=len(rows),
        historical_states_per_execution=11,scope='geometry output identities, full-history worker oracle and raw-row integrity'))
    if issues:raise RuntimeError(str(issues))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--audit',action='store_true')
    parser.add_argument('--worker')
    parser.add_argument('--result',type=Path)
    args=parser.parse_args()
    if args.worker:
        item=json.loads(args.worker)
        scratch=args.result.parent/'.work';scratch.mkdir(exist_ok=True)
        record=run_sensitivity_trial(run_id='linux-geometry-20261008',workload=build_workload(SPEC),
            config=TrieConfig(**item['config']),trial_kind=item['kind'],trial=item['trial'],scratch_root=scratch)
        lv.json_write(args.result,asdict(record));return
    # Explicit provider substitution is part of the archived runner source.
    lv.case_definitions=telemetry_cases
    if args.audit:
        if not lv.audit(args.output,None)['passed']:raise RuntimeError('telemetry audit failed')
        audit_geometry(args.output);return
    if lv.run(args.output,None,wall_limit=7200):raise RuntimeError('telemetry failed')
    geometry(args.output)
    lv.json_write(args.output/'supplement-completed.json',dict(telemetry=27,geometry=45,passed=True))

if __name__=='__main__':main()
