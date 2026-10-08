"""Create Online Resource 1 without cloud credentials or generated databases."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/docs/linux-final-20261008'
def main():
    path=ROOT/'paper/Revon_Linux_Reproducibility_Supplement.zip'
    entries={}
    # Check collection-time hashes as well as the outer ZIP hashes. Packaging
    # must not silently bless a mutated audit record with a new package hash.
    for folder in ['linux-validation-20261008','linux-final-supplement-20261008']:
        bundle=ROOT/'evidence'/folder
        recorded=json.loads((bundle/'SHA256SUMS.json').read_text())
        for name,expected in recorded.items():
            assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==expected,(folder,name)
    for folder in ['linux-validation-20261008','linux-final-supplement-20261008',
                   'threshold-heldout-20261002','crossover-diagnostic-20261002','threshold-robustness-pilot-20261002']:
        for f in sorted((ROOT/'evidence'/folder).rglob('*')):
            if f.is_file() and not any(p in f.parts for p in ['.work','__pycache__']):
                entries['evidence/'+f.relative_to(ROOT/'evidence').as_posix()]=f
    for f in sorted((OUT/'figures').glob('*')):entries['figures/'+f.name]=f
    for f in [ROOT/'tools/setup_linux_validation.sh',ROOT/'docs/JSON_VALUE_CONTRACT.md',
              ROOT/'docs/experiments/LINUX_VALIDATION.md',ROOT/'tools/verify_linux_final.py',
              ROOT/'tools/finalize_linux_manuscripts.py',ROOT/'tools/verify_linux_papers.py',
              OUT/'manuscript_model.json',OUT/'final-verification.json']:
        entries['support/'+f.name]=f
    # Preserve the actual repository-relative manuscript build dependencies.
    for f in [ROOT/'tools/finalize_linux_manuscripts.py',
              ROOT/'tools/preview_diff_figure.py',
              ROOT/'tools/revise_discover_manuscripts.py',
              ROOT/'tools/export_linux_papers.ps1',ROOT/'tools/verify_linux_papers.py',
              ROOT/'output/docs/seven_revision_audit/manuscript_model.json']:
        entries[f.relative_to(ROOT).as_posix()]=f
    for f in (ROOT/'.codex_tmp/seven_revisions/figures').glob('Fig1.*'):
        entries[f.relative_to(ROOT).as_posix()]=f
    intro='''# Online Resource 1

Revon Linux validation and manuscript evidence, 8 October 2026.

Current Linux evidence:
- evidence/linux-validation-20261008: 516 executions, 67 Linux tests.
- evidence/linux-final-supplement-20261008: 72 executions, 69 Linux tests.

Historical Windows threshold/calibration/pilot bundles are retained separately.
Do not pool timings across machines, protocols or source snapshots.
The fixed threshold can choose a slower path than forced log. Million-row Linux
runs are n=1 feasibility diagnostics and cannot support a reliable ranking.

Each Linux bundle includes its exact executed source, frozen protocol, raw
results, summaries and internal audits. See its README and local-verification.
The supplementary source was frozen before its measurement. Its core database
files match the main Linux snapshot; only measurement/verification code changed.
Internal audits establish consistency, not independent timing reproduction.

Manuscript regeneration: the tools/ scripts and their original model/Fig1 inputs
are included at their repository-relative paths. From the extracted root, create
paper/, install python-docx, matplotlib, numpy and pypdf, then run
python tools/finalize_linux_manuscripts.py. PDF export uses Microsoft Word through
tools/export_linux_papers.ps1 on Windows. Fonts and exporter versions can affect
pagination; regenerated files require a fresh visual review. Support scripts
are reference copies; the source-directory audits described in the bundle
READMEs do not require the original download tar archives.

Use support/setup_linux_validation.sh in a user-controlled Linux x86_64
environment, with curl, tar and Python venv available. Read the script first.
It pins CPython 3.14.3, Dolt 2.3.1, psutil 7.1.0 and PyArrow 25.0.1.
Use the matching archived source as your working directory, create tests/test_data,
set PYTHONHASHSEED=20261008, and run its tests before measurement. Use a new output
directory. Exact reproduction and audit commands are in the bundle READMEs.

Public source acquisition (raw records and generated databases are not included):
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
Raw SHA-256:
c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510
Prepare with the matching source's experiments.public_dataset. For an archived
audit, match the supplied dataset.json metadata as well as the prepared record
hash. The public values are canonical JSON strings; correction histories are
generated. See the acquisition/usage details in the recorded dataset metadata.

No credentials, private keys, VM IPs, cloud account tokens, private reviewer
documents, raw TLC records or generated repository directories are included.
PACKAGE_SHA256SUMS.json covers all packaged source/evidence/support files.
'''
    hashes={}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.md',intro)
        for name,f in entries.items():
            data=f.read_bytes()
            assert b'BEGIN OPENSSH PRIVATE KEY' not in data,name
            assert b'35.227.102.15' not in data,name
            hashes[name]=hashlib.sha256(data).hexdigest();z.writestr(name,data)
        z.writestr('PACKAGE_SHA256SUMS.json',json.dumps(hashes,indent=2)+'\n')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(k)).hexdigest()==v for k,v in hashes.items())
    report=dict(path=str(path),files=len(hashes)+2,bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),verified=True)
    (OUT/'package-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
