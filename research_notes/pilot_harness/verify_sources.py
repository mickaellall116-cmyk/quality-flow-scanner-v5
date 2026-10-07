#!/usr/bin/env python3
"""
verify_sources.py — Fail-closed archival source verification.

Asserts the byte identity of the pinned archival sources before the harness
runs. Any mismatch aborts with a non-zero exit.

Pinned identities (from SHA256_MANIFEST.txt, commit b641242):
  pine_backtest.py : 447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5
  scanner_rules.py : 7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac

NOTE (ChatGPT 6037625281, blocker 1): the v2 pilot plan's signal command
contained an INCORRECT pine_backtest.py SHA-256 (447a9a13d0b7...). The value
above is the manifest-verified correct one. The v3 plan corrects it.
"""
import hashlib
import sys
from pathlib import Path

ARCHIVAL_DIR = Path(__file__).resolve().parent.parent / \
    "recovery_4h_20261004" / "cp1_evidence_closure" / "archival_sources_v1"

PINNED = {
    "pine_backtest.py":
        "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
    "scanner_rules.py":
        "7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    failures = []
    for name, expected in PINNED.items():
        p = ARCHIVAL_DIR / name
        if not p.exists():
            failures.append(f"MISSING: {p}")
            continue
        actual = sha256_file(p)
        status = "OK " if actual == expected else "MISMATCH"
        print(f"[{status}] {name}")
        print(f"  expected: {expected}")
        print(f"  actual:   {actual}")
        if actual != expected:
            failures.append(f"HASH MISMATCH: {name}")
    if failures:
        print("\nFAIL-CLOSED: archival source verification failed:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nAll pinned archival sources verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
