#!/usr/bin/env bash
# QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r2 — THE single attempt.
# Invoked once, inside `unshare -n`. Strict sequence; the FIRST failing
# step aborts the whole run (status recorded in logs/ATTEMPT_STATUS.txt).
# No retries, no repairs, no second invocations of any component.
W="$(cd "$(dirname "$0")" && pwd)"
cd "$W" || exit 30
echo START > logs/ATTEMPT_STATUS.txt
echo BUILD > logs/ATTEMPT_STATUS.txt
bash build_env.sh > logs/build_stdout.txt 2> logs/build_stderr.txt || { echo "FAILED_AT_BUILD rc=$?" >> logs/ATTEMPT_STATUS.txt; exit 31; }
echo EMISSIONS > logs/ATTEMPT_STATUS.txt
bash run_emissions.sh > logs/emissions_stdout.txt 2> logs/emissions_stderr.txt || { echo "FAILED_AT_EMISSIONS rc=$?" >> logs/ATTEMPT_STATUS.txt; exit 32; }
echo SUITE > logs/ATTEMPT_STATUS.txt
(cd notes_mirror/validation_fold_coverage_boundary_20261018_28 && python3 test_fold_coverage_boundary.py) > logs/suite_stdout.txt 2> logs/suite_stderr.txt || { echo "FAILED_AT_SUITE rc=$?" >> logs/ATTEMPT_STATUS.txt; exit 33; }
echo PARSE > logs/ATTEMPT_STATUS.txt
"$W/venv/bin/python" consumer_parse.py > logs/parse_stdout.txt 2> logs/parse_stderr.txt || { echo "FAILED_AT_PARSE rc=$?" >> logs/ATTEMPT_STATUS.txt; exit 34; }
echo PARITY > logs/ATTEMPT_STATUS.txt
python3 parity_check.py > logs/parity_stdout.txt 2> logs/parity_stderr.txt || { echo "FAILED_AT_PARITY rc=$?" >> logs/ATTEMPT_STATUS.txt; exit 35; }
echo ATTEMPT_COMPLETE > logs/ATTEMPT_STATUS.txt
echo "RUN_ALL_OK"
