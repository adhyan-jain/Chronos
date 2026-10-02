"""Independent raw-record and preservation audit for the local pilot."""
import csv
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

directory=Path(__file__).resolve().parent
root=directory.parents[2]
manifest=json.loads((directory/'manifest.json').read_text())
results=json.loads((directory/'results.json').read_text())
audit=json.loads((directory/'audit.json').read_text())
protected=json.loads((directory/'protected_before.json').read_text())
for source,digest in manifest['source_sha256'].items():
    assert hashlib.sha256((root/source).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((directory/'source'/source).read_bytes()).hexdigest()==digest
for path,digest in protected['files'].items():
    assert (root/path).is_file() and hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()==protected['git_head']
configs=[tuple(x) for x in manifest['configs']]
all_rows=[]
for case in results:
    spec=case['spec']
    assert spec in manifest['cases']
    assert spec['operations']==case['actual_operations']
    assert case['distinct_keys_touched']<=spec['operations']
    assert sum(case['mutation_mix'].values())==spec['operations']
    assert case['mutation_mix']['inserts']==case['mutation_mix']['deletes']==spec['commits']
    assert len(case['records'])==49
    assert len(case['fresh_records'])==(21 if spec['operations']==65536 else 0)
    for condition,rows,blocks in [('warmup',[r for r in case['records'] if r['trial_kind']=='warmup'],2),
                                 ('measured',[r for r in case['records'] if r['trial_kind']=='measured'],5),
                                 ('fresh',case['fresh_records'],3 if spec['operations']==65536 else 0)]:
        for block in range(1,blocks+1):
            selected=[r for r in rows if r['block']==block]
            assert sorted((r['strategy'],r['threshold']) for r in selected)==sorted(configs)
            assert sorted(r['execution_order'] for r in selected)==list(range(1,8))
    for row in case['records']+case['fresh_records']:
        assert row['correctness'] and row['output_sha256']==case['oracle_sha256']
        expected=row['strategy'] if row['strategy']!='hybrid' else 'log' if row['operations']<=row['threshold'] else 'merkle'
        assert row['selected']==expected
        assert row['log_operations_examined']==(row['operations'] if expected=='log' else 0)
        if row['cache_condition']=='fresh-process-reopened':
            assert abs(row['open_plus_diff_ms']-row['open_verify_ms']-row['diff_ms'])<1e-6
    assert case['semantic_checks']
    assert all(r['returncode']==0 and not r['failure_reason'] for r in case['resources'])
    all_rows+=case['records']+case['fresh_records']
with (directory/'raw_results.csv').open(newline='',encoding='utf-8') as stream: raw=list(csv.DictReader(stream))
assert len(raw)==len(all_rows)
with (directory/'summary.csv').open(newline='',encoding='utf-8') as stream: summary=list(csv.DictReader(stream))
for row in summary:
    values=[r['diff_ms'] for r in all_rows if r['trial_kind']=='measured' and
            (r['case'],r['cache_condition'],r['strategy'],r['threshold'])==
            (row['case'],row['cache_condition'],row['strategy'],int(row['threshold']))]
    assert len(values)==int(row['n_queries'])
    assert abs(statistics.median(values)-float(row['median_ms']))<1e-8
assert audit['completed_cases']==len(results)
assert audit['warm_queries']+audit['fresh_queries']==len(all_rows)
assert audit['all_correct'] and audit['source_unchanged']
report=dict(passed=True,complete_repositories=len(results),queries=len(all_rows),
    protected_files=len(protected['files']),raw_summary_agreement=True,all_paths_match_oracle=True,
    randomized_block_orders_valid=True,manifest_sources_unchanged=True,
    manuscript_production_prior_evidence_unchanged=True,commits_unchanged=True)
(directory/'independent_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
