#!/usr/bin/env bash
# User-space benchmark dependencies; does not change system Python or require root.
set -euo pipefail
prefix="${REVON_VALIDATION_PREFIX:-$HOME/revon-validation}"
mkdir -p "$prefix/bootstrap" "$prefix/bin"
python3 -m venv "$prefix/bootstrap/venv"
"$prefix/bootstrap/venv/bin/pip" install 'uv==0.11.19'
uv="$prefix/bootstrap/venv/bin/uv"
"$uv" python install 3.14.3
"$uv" venv --python 3.14.3 "$prefix/venv"
"$uv" pip install --python "$prefix/venv/bin/python" 'psutil==7.1.0' 'pyarrow==25.0.1'
curl --fail --location --retry 3 --output "$prefix/bootstrap/dolt-linux-amd64.tar.gz" \
  'https://github.com/dolthub/dolt/releases/download/v2.3.1/dolt-linux-amd64.tar.gz'
printf '%s  %s\n' \
  '0a2a318f27c5e1088a2883038573c2054e00f356dc9752e74bca934f8321959a' \
  "$prefix/bootstrap/dolt-linux-amd64.tar.gz" | sha256sum --check
tar -xzf "$prefix/bootstrap/dolt-linux-amd64.tar.gz" -C "$prefix/bootstrap"
install -m 755 "$prefix/bootstrap/dolt-linux-amd64/bin/dolt" "$prefix/bin/dolt"
"$prefix/venv/bin/python" --version
"$prefix/bin/dolt" version
printf 'For the campaign: export PATH="%s/bin:$PATH" PYTHONHASHSEED=20261008\n' "$prefix"
