"""Diagnostic long repeated-key history; excluded from threshold selection."""
from pathlib import Path
import argparse
import json
import shutil
from datetime import datetime, timezone
from .threshold_validation import run_case, summarize, emit_csv, digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(); directory=args.output;directory.mkdir(parents=True,exist_ok=True)
    sources=[Path(p) for p in ("experiments/crossover_extension.py","experiments/threshold_validation.py","experiments/workloads.py","experiments/adapters.py","sqlite_store.py","versioned_db.py")]
    hashes={str(p):digest(p) for p in sources}
    plan=dict(study="diagnostic long-history crossover extension",created_utc=datetime.now(timezone.utc).isoformat(),
        profile=["diagnostic",10000,256,"repeated-key",20261009],operations=[8192,16384,32768,65536,131072],
        excluded_from_selection=True,scope="exploratory extension after held-out study; no threshold reselection; repeated cached queries on one repository per workload",source_code_sha256=hashes)
    path=directory/"manifest.json"
    if path.exists():
        assert json.loads(path.read_text())["source_code_sha256"]==hashes
    else:
        path.write_text(json.dumps(plan,indent=2))
        for p in sources:
            target=directory/"source"/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    results=[run_case(directory,tuple(plan["profile"]),n) for n in plan["operations"]]
    raw=[r for case in results for r in case["records"]]
    emit_csv(directory/"summary.csv",summarize(results));emit_csv(directory/"raw_results.csv",raw)
    audit=dict(passed=all(case["semantic_checks"] for case in results),cases=len(results),queries=len(raw),measured=sum(r["trial_kind"]=="measured" for r in raw),excluded_from_selection=True)
    (directory/"audit.json").write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit),flush=True)

if __name__=="__main__": main()
