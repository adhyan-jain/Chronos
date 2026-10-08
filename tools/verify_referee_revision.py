"""Independent numerical/provenance checks for the referee revision artifacts."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))


def quantile(xs,q):
    a=sorted(xs);pos=q*(len(a)-1);lo=int(pos);hi=min(lo+1,len(a)-1)
    return a[lo]*(hi-pos)+a[hi]*(pos-lo) if hi!=lo else a[lo]


def triple(xs):return [statistics.median(xs),quantile(xs,.25),quantile(xs,.75)]


def main():
    bundle=ROOT/'evidence/referee-analysis-20261003'
    data=json.loads((bundle/'analysis.json').read_text())
    manifest=json.loads((bundle/'manifest.json').read_text())
    for path,sha in manifest['inputs'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    assert hashlib.sha256((ROOT/'tools/referee_revision.py').read_bytes()).hexdigest()==manifest['script_sha256']
    regret=read(bundle/'threshold_regret.csv')
    raw=read(ROOT/'evidence/threshold-heldout-20261002/summary.csv')
    for row in regret:
        src=next(r for r in raw if all(r[k]==row[k] for k in ('scenario','strategy','threshold')))
        candidates=[float(r['median_ms']) for r in raw if r['scenario']==row['scenario'] and r['strategy'] in ('log','merkle')]
        best=min(candidates)
        assert abs(float(row['normalized_score'])-float(src['median_ms'])/best)<1e-12
        assert abs(float(row['regret_ms'])-float(src['median_ms'])+best)<1e-12
    for strategy in ('log','merkle'):
        for split in ('calibration','validation'):
            values=[float(r['normalized_score']) for r in regret if r['strategy']==strategy and r['split']==split]
            assert len(values)==21
            assert abs(statistics.mean(values)-data['static_scores'][strategy][split])<1e-12
    pilot=read(ROOT/'evidence/threshold-robustness-pilot-20261002/raw_results.csv')
    for row in data['startup']:
        rs=[r for r in pilot if r['case']==row['case'] and r['cache_condition']=='fresh-process-reopened' and r['strategy']=='merkle']
        assert len(rs)==3
        for source,key in [('open_verify_ms','open_ms'),('diff_ms','diff_ms'),('open_plus_diff_ms','total_ms')]:
            assert all(abs(a-b)<1e-8 for a,b in zip(triple([float(r[source]) for r in rs]),row[key]))
        assert all(abs(float(r['open_plus_diff_ms'])-float(r['open_verify_ms'])-float(r['diff_ms']))<1e-5 for r in rs)
    public=read(ROOT/'evidence/public-tlc-combined-20261002/raw_results.csv')
    for row in data['rss']:
        rs=[r for r in public if r['model']==row['model'] and int(r['rows'])==row['rows'] and r['commits']=='10' and int(r['changes_per_commit'])==row['rows']//1000 and r['status']=='ok' and r['trial_kind']=='measured']
        assert len(rs)==7
        assert all(abs(a-b)<1e-8 for a,b in zip(triple([float(r['process_tree_peak_rss_bytes'])/2**20 for r in rs]),row['MiB']))
    for row in data['paired']:
        rs=[r for r in pilot if r['case']==row['case'] and r['cache_condition']==row['condition'] and r['trial_kind']=='measured']
        same=[];lm=[]
        for b in sorted({r['block'] for r in rs},key=int):
            group=[r for r in rs if r['block']==b]
            forced={r['strategy']:float(r['diff_ms']) for r in group if r['strategy'] in ('log','merkle')}
            lm.append(forced['log']/forced['merkle'])
            same.extend(float(r['diff_ms'])/forced[r['selected']] for r in group if r['strategy']=='hybrid')
        assert all(abs(a-b)<1e-12 for a,b in zip(triple(lm),row['log_over_merkle']))
        assert all(abs(a-b)<1e-12 for a,b in zip(triple(same),row['same_path_selector_over_forced']))
    repair=ROOT/'evidence/referee-repair-overhead-20261003'
    meta=json.loads((repair/'manifest.json').read_text())
    for path,sha in meta['source_hashes'].items():assert hashlib.sha256((repair/path).read_bytes()).hexdigest()==sha
    for name in ('versioned_db.py','sqlite_store.py'):
        assert (ROOT/name).read_bytes()==(repair/'source_after'/name).read_bytes(), 'Repair changed after timing snapshot'
    timings=read(repair/'raw_results.csv')
    assert len(timings)==36 and all(r['correctness']=='True' for r in timings)
    for row in json.loads((repair/'summary.json').read_text()):
        before={r['block']:float(r[row['metric']]) for r in timings if r['profile']==row['profile'] and r['phase']=='measured' and r['variant']=='before'}
        after={r['block']:float(r[row['metric']]) for r in timings if r['profile']==row['profile'] and r['phase']=='measured' and r['variant']=='after'}
        assert len(before)==len(after)==5
        assert abs(statistics.median(after[b]/before[b] for b in before)-row['median_paired_after_over_before'])<1e-12
    assert json.loads((repair/'correctness.json').read_text())['legacy_reopen_compatible']
    changed=subprocess.check_output(['git','diff','--name-only','--','evidence'],cwd=ROOT,text=True).strip()
    assert not changed,'Previously tracked evidence was modified: '+changed
    result=dict(passed=True,threshold_cases=42,startup_groups=6,rss_groups=18,pilot_groups=18,repair_executions=36,
                old_tracked_evidence_unchanged=True,repair_source_matches_measured_snapshot=True,
                limits='Numeric and provenance checks; visual inspection and journal disclosure remain separate.')
    (bundle/'verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
