#!/bin/bash
# Frozen synthetic qualification: harness twice, pinned offline env.
set -euo pipefail
cd "$(dirname "$0")"
PY="$HOME/workspace/qf_td59_wt/.venv59/bin/python"
unshare -n "$PY" test_s2_synthetic.py > run1_output.json
unshare -n "$PY" test_s2_synthetic.py > run2_output.json
sha256sum run1_output.json run2_output.json
cmp run1_output.json run2_output.json && echo "RUNS_BYTE_IDENTICAL"
