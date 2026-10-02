"""Capture protection baseline for a NEW isolated pilot, without measuring."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=Path.cwd().resolve()
output=args.output.resolve()
assert output.is_relative_to(root/'.codex_tmp/threshold_robustness_pilot')
assert not output.exists(),'Use a new output directory'
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
paths={p for p in tracked if p and (root/p).is_file()}
for folder in ('paper','evidence','experiments'):
    paths.update(p.relative_to(root).as_posix() for p in (root/folder).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts)
output.mkdir(parents=True)
records={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sorted(paths)}
(output/'protected_before.json').write_text(json.dumps(dict(
    created_utc=datetime.now(timezone.utc).isoformat(),
    git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
    git_status=subprocess.check_output(['git','status','--porcelain'],cwd=root).decode(),files=records),indent=2))
print(output)
