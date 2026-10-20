#!/bin/bash
# QF-TD-ROUTE-TRANSACTION-WORKSPACE-STAGE-CONTINUATION-20261020-56 r1 -
# single orchestrated offline execution. Runs ENTIRELY inside
# `unshare -n` (invoked by caller). Steps: network probes -> offline
# venv build from pinned wheelhouse -> freeze equality vs TD lock ->
# proof driver v8 (hash gates -> P0 receipt -> git-aware staging +
# blob proof -> P1 -> P2 -> P3 -> shadow removal) -> post-run re-hash.
# Any env-stage failure stops before the driver; the driver stops at
# its first material failure. No retries anywhere in this script.
set -u
STAGE=/home/hatch/workspace/qf_td56_stage
OUT=/home/hatch/workspace/qf_td56_stage/out
WHEELS=/home/hatch/workspace/td_nl_wheelhouse_20261016/wheels
mkdir -p "$OUT"
RECEIPT="$OUT/env_receipt.txt"
: > "$RECEIPT"
echo "=== run start (UTC) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
echo "=== network probes (all must FAIL) ===" >> "$RECEIPT"
python3 "$STAGE/network_probe.py" >> "$RECEIPT" 2>&1
PROBE_RC=$?
curl -sS -m 5 https://pypi.org >> "$RECEIPT" 2>&1
echo "curl exit: $?" >> "$RECEIPT"
if [ "$PROBE_RC" -ne 0 ]; then
  echo "ENV_STAGE_FAILURE: ENV_NETWORK_PROBE" >> "$RECEIPT"
  echo "ENV_NETWORK_PROBE" > "$OUT/run_status.txt"
  exit 42
fi
echo "=== build venv (offline, pinned wheelhouse) ===" >> "$RECEIPT"
python3 -m venv /home/hatch/workspace/qf_td56_stage/venv >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (venv)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }
/home/hatch/workspace/qf_td56_stage/venv/bin/pip install --no-index --find-links "$WHEELS" \
  --require-hashes -r "$STAGE/requirements_hashes.txt" >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (pip install)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }
echo "=== identity ===" >> "$RECEIPT"
/home/hatch/workspace/qf_td56_stage/venv/bin/python -c "import sys, pandas_market_calendars as m, pandas as pd; print('python', sys.version.split()[0]); print('pandas', pd.__version__); print('pmc', m.__version__)" >> "$RECEIPT" 2>&1
/home/hatch/workspace/qf_td56_stage/venv/bin/pip freeze > "$OUT/freeze.txt" 2>> "$RECEIPT"
if diff -u "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT" 2>&1; then
  echo "FREEZE_EQUALS_LOCK" >> "$RECEIPT"
else
  echo "ENV_STAGE_FAILURE: ENV_FREEZE_MISMATCH" >> "$RECEIPT"
  echo "ENV_FREEZE_MISMATCH" > "$OUT/run_status.txt"; exit 42
fi
sha256sum "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT"
echo "=== proof driver (ONE attempt) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
/home/hatch/workspace/qf_td56_stage/venv/bin/python "$STAGE/proof_driver.py" "$OUT" \
  > "$OUT/driver_stdout.txt" 2> "$OUT/driver_stderr.txt"
echo "driver exit: $?" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
echo "=== post-run re-hash: pinned originals must be unchanged ===" >> "$RECEIPT"
R=/home/hatch/workspace/td56_wt/research_notes
sha256sum "$R/pilot_harness/construct_4h.py" \
          "$R/pilot_harness/validate_input.py" \
          "$R/pilot_harness/pilot_build.py" \
          "$R/pilot_harness/verify_sources.py" \
          "$R/pilot_harness/credit_ledger.json" \
          >> "$RECEIPT" 2>&1
echo "DRIVER_RAN" > "$OUT/run_status.txt"
echo "=== run end (UTC) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
