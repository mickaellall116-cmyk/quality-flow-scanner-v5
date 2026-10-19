#!/usr/bin/env bash
# QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r2 — environment build.
# Runs ONLY inside `unshare -n` (no network). Installs ONLY from the pinned
# wheelhouse with --no-index --no-cache-dir --require-hashes --find-links.
set -u
W="$(cd "$(dirname "$0")" && pwd)"
REPO="$HOME/workspace/quality-flow-scanner-v5"
WH="$HOME/workspace/td_nl_wheelhouse_20261016/wheels"
LOCK="$REPO/research_notes/qualified_calendar_env_route_preflight_20261018_29/PROPOSED_HASH_LOCK.txt"

echo "== network probes (all must FAIL) =="
python3 -c "import urllib.request; urllib.request.urlopen('https://pypi.org', timeout=5)" 2>&1 | tail -1 || true
curl -sS -m 5 https://pypi.org 2>&1 | head -1 || true
python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('8.8.8.8',53))" 2>&1 | tail -1 || true

echo "== venv build =="
python3.12 -m venv "$W/venv" || exit 11
"$W/venv/bin/python" -m pip install --no-index --no-cache-dir --require-hashes \
  -r "$LOCK" --find-links "$WH" || exit 12
"$W/venv/bin/pip" freeze > "$W/freeze.txt" || exit 13
F=$(sha256sum "$W/freeze.txt" | cut -d' ' -f1)
echo "freeze sha256: $F"
[ "$F" = "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068" ] || { echo "FREEZE MISMATCH"; exit 14; }
echo "== installed member pins =="
"$W/venv/bin/python" "$W/check_members.py" || exit 15
echo "BUILD_OK"
