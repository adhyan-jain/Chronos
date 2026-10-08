set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export PYTHONHASHSEED=20261008
export PYTHONUNBUFFERED=1
cd "$HOME/revon-validation/source-20261008"
exec "$HOME/revon-validation/venv/bin/python" -m experiments.linux_validation \
  --output evidence/linux-validation-20261008 \
  --dataset "$HOME/revon-validation/data/tlc-prepared"
