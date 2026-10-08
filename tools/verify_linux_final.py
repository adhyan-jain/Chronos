"""Independent local integrity check for the final Linux supplement and claims."""
from pathlib import Path
import csv,json,hashlib,math,shutil,subprocess,sys,tarfile,tempfile
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'evidence/linux-final-supplement-20261008'
def read(path):return list(csv.DictReader(path.open(encoding='utf-8',newline='')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    archive=ROOT/'.codex_tmp/linux-validation-access/linux-final-supplement.tar.gz'
    assert sha(archive)=='440761dae203cef2860327e9f688bfcb0b29f2f635b9568144c232f7c84027bd'
    if not P.exists():
        with tarfile.open(archive) as t:t.extractall(ROOT/'evidence',filter='data')
    hashes=json.loads((P/'SHA256SUMS.json').read_text())
    assert all(sha(P/k)==v for k,v in hashes.items())
    # Archived auditors write audit.json. Audit a disposable copy so a Windows
    # rerun cannot replace the collected LF files with CRLF and break hashes.
    with tempfile.TemporaryDirectory() as temp:
        copy=Path(temp)/P.name
        shutil.copytree(P,copy,ignore=shutil.ignore_patterns('__pycache__','.work'))
        result=subprocess.run([sys.executable,'-m','experiments.linux_final_supplement','--output',str(copy),'--audit'],cwd=copy/'source',capture_output=True,text=True)
        assert result.returncode==0,(result.stdout,result.stderr)
    assert all(sha(P/k)==v for k,v in hashes.items()),'audit mutated collected files'
    # Recompute geometry summaries from raw records, independently of saved audit.
    sys.path.insert(0,str(P/'source'))
    from experiments.trie_sensitivity import SensitivityRecord,_write_summary
    raw=read(P/'geometry/raw_results.csv')
    records=[]
    expected=[]
    configs=[(4,6),(8,3),(8,4),(8,5),(16,3)]
    for kind,count in [('warmup',2),('measured',7)]:
        for trial in range(1,count+1):
            shift=(trial-1)%5
            for b,d in configs[shift:]+configs[:shift]:expected.append((kind,trial,f'b{b}-d{d}'))
    assert len(raw)==45
    for index,(r,identity) in enumerate(zip(raw,expected)):
        assert (r['trial_kind'],int(r['trial']),r['config'])==identity
        proof=json.loads((P/f'geometry/{index:03d}.json').read_text())
        for k,v in proof.items():
            actual=r[k]
            if isinstance(v,float):assert math.isclose(float(actual),v,rel_tol=1e-12)
            else:assert actual==('' if v is None else str(v))
        assert proof['correctness'] and proof['status']=='ok'
        records.append(SensitivityRecord(**proof))
    with tempfile.TemporaryDirectory() as temp:
        calculated=Path(temp)/'summary.csv';_write_summary(calculated,records)
        assert calculated.read_bytes()==(P/'geometry/summary.csv').read_bytes()
    telemetry=read(P/'raw_results.csv')
    assert len(telemetry)==27 and all(r['process_tree_read_bytes']!='' for r in telemetry)
    assert all(float(r['process_tree_read_bytes'])==0 for r in telemetry)
    # Preserve core identity: only the harness and checks changed.
    original=ROOT/'evidence/linux-validation-20261008/source'
    assert all(sha(original/name)==sha(P/'source'/name) for name in ['versioned_db.py','sqlite_store.py'])
    primary=read(ROOT/'evidence/linux-validation-20261008/raw_results.csv')
    adverse=[r for r in primary if r['scenario']=='linux-threshold-h64-c512' and r['trial_kind']=='measured']
    for trial in range(1,8):
        block={r['model']:r for r in adverse if int(r['trial'])==trial}
        assert float(block['Revon-log calibration']['diff_ms'])<float(block['Revon-H']['diff_ms'])
    report=dict(passed=True,file_hashes=len(hashes),telemetry_executions=27,geometry_executions=45,
        geometry_summary_byte_identical=True,core_source_identical=True,zero_read_observations=27,
        adverse_threshold_matched_trials=7,external_archive_sha256=sha(archive),
        scope='local semantic/matrix/provenance/summary audit; no independent timing reproduction')
    (P/'local-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
