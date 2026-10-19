#!/usr/bin/env bash
# QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r2 — emissions + assembly.
# Runs ONLY inside `unshare -n`. Pinned generator v2 (2995b124) and
# assembler (6a6308f9), unmodified. Full dual emission repeated once for
# determinism (part of the contract sequence).
set -u
W="$(cd "$(dirname "$0")" && pwd)"
PY="$W/venv/bin/python"
cd "$W" || exit 20
echo "== network probe in emissions context (must FAIL) =="
"$PY" -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('8.8.8.8',53))" 2>&1 | tail -1 || true
for run in 1 2; do
  "$PY" generator.py --path A --start 2024-09-16 --end 2026-10-16 --out "out/emission_A_run${run}.json" || exit 21
  "$PY" generator.py --path C --start 2024-09-16 --end 2026-10-16 --out "out/emission_C_run${run}.json" || exit 22
  "$PY" generator.py --path A --start 2024-01-01 --end 2024-12-31 --out "out/aux2024_A_run${run}.json" || exit 23
  "$PY" generator.py --path C --start 2024-01-01 --end 2024-12-31 --out "out/aux2024_C_run${run}.json" || exit 24
  "$PY" generator.py --path A --start 2026-01-01 --end 2026-12-31 --out "out/aux2026_A_run${run}.json" || exit 25
  "$PY" generator.py --path C --start 2026-01-01 --end 2026-12-31 --out "out/aux2026_C_run${run}.json" || exit 26
  "$PY" assemble.py "out/emission_A_run${run}.json" "out/emission_C_run${run}.json" "out/artifact_run${run}.json" "out/agreement_run${run}.json" || exit 27
done
echo "EMISSIONS_OK"
