#!/bin/bash
# QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1 — single
# orchestrated offline execution (Family C only). Runs ENTIRELY inside
# `unshare -n` (invoked by caller). Steps: network probes -> offline
# venv build from pinned wheelhouse -> freeze equality vs TD lock ->
# proof driver (hash gates -> NLQUAL matrix x2) -> post-run re-hash of
# all pinned originals and candidates. Any env-stage failure stops
# before the driver; the driver stops at its first material failure.
# No retries anywhere in this script.
set -u
STAGE=/tmp/td47_stage
OUT=/tmp/td47_out
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
python3 -m venv /tmp/td47/venv >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (venv)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }
/tmp/td47/venv/bin/pip install --no-index --find-links "$WHEELS" \
  --require-hashes -r "$STAGE/requirements_hashes.txt" >> "$RECEIPT" 2>&1 || {
  echo "ENV_STAGE_FAILURE: ENV_BUILD (pip install)" >> "$RECEIPT"
  echo "ENV_BUILD" > "$OUT/run_status.txt"; exit 42; }

echo "=== identity ===" >> "$RECEIPT"
/tmp/td47/venv/bin/python -c "import sys, pandas_market_calendars as m, pandas as pd; print('python', sys.version.split()[0]); print('pandas', pd.__version__); print('pmc', m.__version__)" >> "$RECEIPT" 2>&1
/tmp/td47/venv/bin/pip freeze > "$OUT/freeze.txt" 2>> "$RECEIPT"
if diff -u "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT" 2>&1; then
  echo "FREEZE_EQUALS_LOCK" >> "$RECEIPT"
else
  echo "ENV_STAGE_FAILURE: ENV_FREEZE_MISMATCH" >> "$RECEIPT"
  echo "ENV_FREEZE_MISMATCH" > "$OUT/run_status.txt"; exit 42
fi
sha256sum "$STAGE/integration_requirements.lock" "$OUT/freeze.txt" >> "$RECEIPT"

echo "=== hash gates (pre-run; full closure in proof_results.json) ===" >> "$RECEIPT"
R=/home/hatch/workspace/quality-flow-scanner-v5
sha256sum "$R/research_notes/pilot_harness/validate_input.py" \
          "$R/research_notes/pilot_harness/construct_4h.py" \
          "$R/research_notes/pilot_harness/pilot_build.py" \
          "$R/research_notes/pilot_harness/verify_sources.py" \
          "$R/research_notes/pilot_harness/rate_limiter.py" \
          "$STAGE/candidate_validator.py" \
          "$STAGE/candidate_entrypoint.py" \
          "$STAGE/run_nlqual_matrix.py" \
          "$STAGE/nlqual_supplement.json" \
          "$STAGE/nlqual/td_lifecycle_repair_candidate/td_min_collector.py" \
          "$STAGE/nlqual/pilot_harness/validate_input.py" \
          "$STAGE/nlqual/pilot_harness/rate_limiter.py" \
          "$STAGE/nlqual/pilot_harness/verify_sources.py" \
          >> "$RECEIPT" 2>&1

echo "=== proof driver (ONE attempt) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
/tmp/td47/venv/bin/python "$STAGE/proof_driver.py" "$OUT" \
  > "$OUT/driver_stdout.txt" 2> "$OUT/driver_stderr.txt"
echo "driver exit: $?" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"

echo "=== post-run re-hash: pinned originals + candidates must be unchanged ===" >> "$RECEIPT"
sha256sum "$R/research_notes/pilot_harness/validate_input.py" \
          "$R/research_notes/pilot_harness/construct_4h.py" \
          "$R/research_notes/pilot_harness/pilot_build.py" \
          "$R/research_notes/pilot_harness/verify_sources.py" \
          "$R/research_notes/pilot_harness/rate_limiter.py" \
          "$STAGE/candidate_validator.py" \
          "$STAGE/candidate_entrypoint.py" \
          >> "$RECEIPT" 2>&1
echo "DRIVER_RAN" > "$OUT/run_status.txt"
echo "=== run end (UTC) ===" >> "$RECEIPT"
date -u +%Y-%m-%dT%H:%M:%SZ >> "$RECEIPT"
