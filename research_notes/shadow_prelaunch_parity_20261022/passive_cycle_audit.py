#!/usr/bin/env python3
"""Strict offline audit of an *existing* ordinary-cycle V5.4 output.

This reader never imports the scanner or a network package and never writes to
production or a shadow journal. A PASS only describes the readiness of the
upstream artifact for *further* independent parity review, NOT launch approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

FROZEN_RULE = '2026-09-15-v54'
EXPECTED_COHORT = {'UX51': 51, 'X2': 199}


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return ts if ts.tzinfo and ts.utcoffset() is not None else None


def evaluate(snapshot: dict, *, now: datetime, pause_sentinel: bool,
             producer_grid_proof: dict | None = None, digest: str | None = None) -> dict:
    """Return named hold reasons. Proof is only accepted with *external* pins."""
    problems: list[str] = []
    if not pause_sentinel:
        problems.append('PAUSE_SENTINEL_NOT_PRESENT')
    if not isinstance(snapshot, dict):
        return {'verdict': 'HOLD', 'reasons': ['INVALID_ENVELOPE'],
                'sha256': digest, 'qualified_count': 0}

    produced = parse_time(snapshot.get('generated_at'))
    if produced is None or produced > now or now - produced > timedelta(minutes=20):
        problems.append('MISSING_FUTURE_OR_STALE_CYCLE_TIMESTAMP')
    if snapshot.get('interval') != '4h' or snapshot.get('rule_version') != FROZEN_RULE:
        problems.append('UNEXPECTED_STRATEGY_VERSION_OR_INTERVAL')
    if snapshot.get('source') != 'v54-engine-local':
        problems.append('UNKNOWN_SOURCE')
    forward = snapshot.get('forward_test') or {}
    if (forward.get('universe_size') != 250 or
            forward.get('cohort_sizes') != EXPECTED_COHORT):
        problems.append('WRONG_OR_UNVERIFIED_250_COHORT')
    cycle = forward.get('last_cycle') or {}
    if cycle.get('cycle_status') != 'HEALTHY' or cycle.get('errors'):
        problems.append('ORDINARY_CYCLE_NOT_HEALTHY')
    if cycle.get('entries_paused') is not True or cycle.get('entries_suppressed') is not True:
        problems.append('PAUSED_SYSTEM_NOT_PROVEN')
    coverage = cycle.get('coverage') or {}
    if (coverage.get('global_provider_status') != 'ok' or
            coverage.get('market_data_gap') not in (False, None) or
            coverage.get('degraded_symbols') or
            coverage.get('unresolved_security_events') or
            not isinstance(coverage.get('expected_symbols'), int) or
            coverage.get('expected_symbols') < 250 or
            coverage.get('fresh_symbols') != coverage.get('expected_symbols')):
        problems.append('COMPLETE_COHORT_AND_MARKET_NOT_PROVEN')

    results = snapshot.get('results')
    if not isinstance(results, list) or snapshot.get('count') != len(results):
        problems.append('RESULT_COUNT_OR_ARRAY_INVALID')
        results = []
    ids = set()
    bad_samples = []
    issue_counts = Counter()
    for row in results:
        row_issues = []
        if not isinstance(row, dict):
            row_issues.append('NONOBJECT_ROW')
            row = {}
        sid = row.get('signal_id')
        sym = row.get('symbol')
        start = parse_time(row.get('signal_bar_start_at'))
        close = parse_time(row.get('signal_bar_close_at'))
        if not sid or not sym or not start or not close:
            row_issues.append('MISSING_ID_SYMBOL_OR_AWARE_BAR')
        if sid in ids:
            row_issues.append('DUPLICATE_ID')
        ids.add(sid)
        if start and close and close <= start:
            row_issues.append('NEGATIVE_OR_ZERO_BAR')
        if close and produced and close > produced:
            row_issues.append('UNCLOSED_SIGNAL_AT_PRODUCTION')
        if sid and sym and close:
            wanted = f'v54:{sym}:4h:{row.get("signal_bar_close_at")}:{FROZEN_RULE}'
            if sid != wanted:
                row_issues.append('NONCANONICAL_SIGNAL_ID')
        if row_issues and len(bad_samples) < 5:
            bad_samples.append({'symbol': sym, 'signal_id': sid, 'issues': row_issues})
        issue_counts.update(row_issues)
    if issue_counts:
        problems.append('BAD_SIGNAL_ROWS')

    # These must come from a separate frozen and independently verified
    # launch attestation, NOT a field embedded in the producer payload.
    if not isinstance(producer_grid_proof, dict) or any(
        not isinstance(producer_grid_proof.get(key), str) or
        len(producer_grid_proof[key]) != 64 or
        any(c not in '0123456789abcdef' for c in producer_grid_proof[key])
        for key in ('scanner_stack_sha256', 'universe_sha256', 'calendar_sha256')
    ) or producer_grid_proof.get('grid_id') != 'SESSION_ANCHORED_XNYS_AND_CRYPTO_V1':
        problems.append('NO_INDEPENDENT_CORRECT_GRID_ATTESTATION')

    # The current legacy producer has NO verified matching external proof.
    # Do not allow this tool to mint one from historical outputs.
    return {
        'verdict': 'HOLD' if problems else 'STRUCTURAL_CANDIDATE_ONLY',
        'scope': 'read-only existing output; NEVER a launch GO',
        'sha256': digest, 'qualified_count': len(results),
        'reasons': sorted(set(problems)),
        'row_issue_counts': dict(sorted(issue_counts.items())),
        'bad_row_examples': bad_samples,
    }


def read_bytes_stable(path: Path, max_bytes: int = 10_000_000) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing/redirected ordinary-cycle file')
    before = path.stat()
    if before.st_size > max_bytes:
        raise ValueError('oversized ordinary-cycle file')
    raw = path.read_bytes()
    after = path.stat()
    if len(raw) != before.st_size or (before.st_dev, before.st_ino,
        before.st_mtime_ns, before.st_size) != (after.st_dev, after.st_ino,
        after.st_mtime_ns, after.st_size):
        raise ValueError('ordinary-cycle file changed mid-read')
    return raw


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', required=True, type=Path)
    args = p.parse_args()
    root = args.repo_root.resolve()
    source = root / 'latest_v54_signals.json'
    sentinel = root / 'forward_test' / 'PAUSE_NEW_ENTRIES'
    try:
        raw = read_bytes_stable(source)
        data = json.loads(raw)
        result = evaluate(data, now=datetime.now(timezone.utc),
                          pause_sentinel=sentinel.is_file(),
                          digest=hashlib.sha256(raw).hexdigest())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {'verdict': 'HOLD', 'reasons': ['READ_FAILED'],
                  'detail': str(exc)[:250]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2  # Always HOLD pending separately verified running-stack grid


if __name__ == '__main__':
    raise SystemExit(main())
