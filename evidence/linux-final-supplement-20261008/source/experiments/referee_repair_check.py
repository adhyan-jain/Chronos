"""Bounded paired before/after check; historical publication timings stay intact."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pair(folder, label):
    modules=[]
    previous=sys.modules.get('versioned_db')
    for name in ('versioned_db', 'sqlite_store'):
        spec=importlib.util.spec_from_file_location(label+'_'+name,folder/(name+'.py'))
        mod=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=mod
        spec.loader.exec_module(mod)
        modules.append(mod)
        if name=='versioned_db':sys.modules[name]=mod
    if previous is None:sys.modules.pop('versioned_db',None)
    else:sys.modules['versioned_db']=previous
    return modules[0],modules[1].SQLiteRevonRepository


def canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def diff_bytes(entries):
    return canon([[e.key,e.change_type,e.old_value,e.new_value] for e in entries])


def timed(call):
    start=time.perf_counter_ns();value=call()
    return value,(time.perf_counter_ns()-start)/1e6


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output.resolve()
    if out.exists():raise FileExistsError('Use a new evidence directory')
    out.mkdir(parents=True)
    profiles=[dict(name='10k-spread-h10',rows=10000,commits=10,changes=10,locality='spread'),
              dict(name='10k-repeated-h50',rows=10000,commits=50,changes=100,locality='repeated'),
              dict(name='100k-spread-h10',rows=100000,commits=10,changes=100,locality='spread')]
    manifest=dict(study='JSON ownership/equality repair overhead; no threshold tuning',
                  created_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  python=sys.version,platform=platform.platform(),pythonhashseed=os.environ.get('PYTHONHASHSEED'),
                  profiles=profiles,blocks=6,warmup_blocks=1,measured_blocks=5,
                  order='alternate before/after by block, reverse initial order by profile',
                  clock='commit wall clock; read clocks include canonical output; setup and correctness outside timers',
                  limits='One process and host; independent repository per block/variant, same deterministic workload; descriptive medians only',
                  threshold=4096,source_hashes={})
    for label,folder in [('before',args.baseline),('after',ROOT)]:
        target=out/('source_'+label);target.mkdir()
        for filename in ('versioned_db.py','sqlite_store.py'):
            shutil.copy2(folder/filename,target/filename)
            manifest['source_hashes'][str((target/filename).relative_to(out))]=digest(target/filename)
    shutil.copy2(Path(__file__),out/'referee_repair_check.py')
    manifest['source_hashes']['referee_repair_check.py']=digest(out/'referee_repair_check.py')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    pairs={label:load_pair(out/('source_'+label),label) for label in ('before','after')}
    work=out/'.work';work.mkdir()
    records=[];checks=[]
    for pi,p in enumerate(profiles):
        initial={f'k{i:07d}':f'initial-{i:023d}' for i in range(p['rows'])}
        batches=[];expected=dict(initial)
        for c in range(p['commits']):
            indices=[(j if p['locality']=='repeated' else (j*997+c*131)%p['rows']) for j in range(p['changes'])]
            batch={f'k{i:07d}':f'value-{c:05d}-{i:019d}' for i in indices}
            batches.append(batch);expected.update(batch)
        expected_diff=canon([[k,'modified',initial[k],expected[k]] for k in sorted(expected) if initial[k]!=expected[k]])
        for block in range(6):
            roots={}
            for label in (('before','after') if (block+pi)%2==0 else ('after','before')):
                path=work/f'{pi}-{block}-{label}.db'
                _,Repo=pairs[label]
                with Repo.create(path,hybrid_log_threshold=4096) as repo:
                    root,import_ms=timed(lambda:repo.commit(initial))
                    initial_root=root;commits=[]
                    for batch in batches:
                        root,ms=timed(lambda:repo.apply_changes(root,puts=batch));commits.append(ms)
                    readings={}
                    for strategy in ('log','merkle','hybrid'):
                        result,ms=timed(lambda:diff_bytes(repo.diff_versions(1,repo.head,strategy)))
                        assert result==expected_diff
                        readings[strategy+'_ms']=ms
                    state,checkout_ms=timed(lambda:canon(repo.checkout(repo.head)))
                    assert state==canon(expected)
                    repo.verify_integrity()
                    roots[label]=(initial_root,root)
                reopened,open_ms=timed(lambda:Repo.open(path))
                with reopened:
                    assert canon(reopened.checkout(reopened.head))==canon(expected)
                records.append(dict(profile=p['name'],block=block,phase='warmup' if block==0 else 'measured',variant=label,
                    initial_import_ms=import_ms,commit_ms=statistics.median(commits),checkout_ms=checkout_ms,open_verify_ms=open_ms,
                    output_sha256=hashlib.sha256(expected_diff).hexdigest(),correctness=True,**readings))
                path.unlink()
                print(p['name'],block,label,flush=True)
            assert roots['before']==roots['after']
            checks.append(dict(profile=p['name'],block=block,string_roots_compatible=True))
    # Reopen a genuine pre-repair repository with the repaired reader, including nested JSON.
    _,Before=pairs['before'];_,After=pairs['after'];path=work/'legacy.db'
    state={'nested':{'v':[True,1,1.0,None]},'text':'unchanged'}
    with Before.create(path) as repo:
        legacy_root=repo.commit(state);legacy_head=repo.head_hash
    with After.open(path) as repo:
        assert repo.versions[1]==legacy_root and repo.head_hash==legacy_head
        assert canon(repo.checkout(1))==canon(state)
        repo.verify_integrity()
    path.unlink()
    with (out/'raw_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    summary=[]
    for p in profiles:
        for metric in ('initial_import_ms','commit_ms','log_ms','merkle_ms','hybrid_ms','checkout_ms','open_verify_ms'):
            before=[r[metric] for r in records if r['profile']==p['name'] and r['phase']=='measured' and r['variant']=='before']
            after=[r[metric] for r in records if r['profile']==p['name'] and r['phase']=='measured' and r['variant']=='after']
            summary.append(dict(profile=p['name'],metric=metric,n=5,before_ms=statistics.median(before),after_ms=statistics.median(after),
                                median_paired_after_over_before=statistics.median([b/a for a,b in zip(before,after)])))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'correctness.json').write_text(json.dumps(dict(passed=True,legacy_reopen_compatible=True,checks=checks),indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
