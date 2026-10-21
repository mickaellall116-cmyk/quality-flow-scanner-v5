#!/bin/bash
# -61 frozen synthetic qualification: harness twice, pinned offline env.
set -euo pipefail
cd "$(dirname "$0")"
PY="$HOME/workspace/qf_td61_wt/.venv61/bin/python"
unshare -n "$PY" test_boundary_shim_synthetic.py > run1_output.json
unshare -n "$PY" test_boundary_shim_synthetic.py > run2_output.json
sha256sum run1_output.json run2_output.json
cmp run1_output.json run2_output.json && echo "RUNS_BYTE_IDENTICAL"
