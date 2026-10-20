#!/bin/bash
# QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1 — single orchestrated
# offline execution. Runs ENTIRELY inside `unshare -n` (invoked by caller).
# Steps: network probes -> offline venv build from pinned wheelhouse ->
# freeze equality vs TD lock -> hash gates -> ONE proof-driver run.
# Any env-stage failure stops before the driver; the driver itself stops
# at its first material failure. No retries anywhere in this script.
set -u
STAGE=/tmp/td43_stage
OUT=/tmp/td43_out
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
python3 -m venv /tmp/td43/venv >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (venv)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }
/tmp/td43/venv/bin/pip install --no-index --find-links "$WHEELS" \
  --require-hashes -r "$STAGE/requirements_hashes.txt" >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (pip install)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }

echo "=== identity ===" >> "$RECEIPT"
/tmp/td43/venv/bin/python -c "import sys, pandas_market_calendars as m, pandas as pd; print('python', sys.version.split()[0]); print('pandas', pd.__version__); print('pmc', m.__version__)" >> "$RECEIPT" 2>&1
/tmp/td43/venv/bin/pip freeze > "$OUT/freeze.txt" 2>> "$RECEIPT"
if diff -u "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT" 2>&1; then
  echo "FREEZE_EQUALS_LOCK" >> "$RECEIPT"
else
  echo "ENV_STAGE_FAILURE: ENV_FREEZE_MISMATCH" >> "$RECEIPT"
  echo "ENV_FREEZE_MISMATCH" > "$OUT/run_status.txt"; exit 42
fi
sha256sum "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT"

echo "=== hash gates ===" >> "$RECEIPT"
R=/home/hatch/workspace/quality-flow-scanner-v5
sha256sum "$R/research_notes/pilot_harness/construct_4h.py" \
          "$R/research_notes/pilot_harness/pilot_build.py" \
          "$R/research_notes/pilot_harness/validate_input.py" \
          "$R/canonical_baseline/scripts/fetch_4h.py" \
          "$R/research_notes/xnys_isolated_calendar_generation_20261019_35_r2/XNYS_SESSION_SCHEDULE_V2.json" \
          >> "$RECEIPT" 2>&1

echo "=== proof driver (ONE attempt) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
/tmp/td43/venv/bin/python "$STAGE/proof_driver.py" "$OUT" \
  > "$OUT/driver_stdout.txt" 2> "$OUT/driver_stderr.txt"
echo "driver exit: $?" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
echo "DRIVER_RAN" > "$OUT/run_status.txt"
echo "=== run end (UTC) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
