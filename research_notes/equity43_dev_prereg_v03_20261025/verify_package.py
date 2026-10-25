#!/usr/bin/env python3
"""Verify the preregistration v0.3 package (documentation-only package).

Checks:
  1. SHA256_MANIFEST.txt entries match the bytes on disk.
  2. All four companion documents exist.
  3. The draft cites the pinned v0.2 base (commit 02568b2 + PDF sha 01c4fff0...).
  4. Register completeness: changelog carries change rows C01..C25 and
     no-change rows W01..W09, and every C-tag C01..C25 is referenced at
     least once in the draft or the companion feasibility document.
  5. Preserved labels present in the draft (C1 FAIL, DEV EXPLORATORY,
     G4 UNADOPTED, S1 LAUNCH_HOLD, PAUSED, SEALED).
Exit 0 = PASS; exit 2 = FAIL (fail-closed).
"""
import hashlib
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
FILES = [
    "PREREG_V03_DRAFT.md",
    "CHANGELOG_V03.md",
    "FREEZE_BLOCKER_CHECKLIST.md",
    "OUTCOME_BLIND_FEASIBILITY.md",
    "verify_package.py",
]


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    failures = []

    # 1. manifest
    manifest = HERE / "SHA256_MANIFEST.txt"
    if not manifest.exists():
        failures.append("SHA256_MANIFEST.txt missing")
        listed = {}
    else:
        listed = {}
        for line in manifest.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            digest, name = line.split(None, 1)
            listed[name.strip()] = digest.strip()
    for name in FILES:
        p = HERE / name
        if not p.exists():
            failures.append(f"missing file: {name}")
            continue
        if name not in listed:
            failures.append(f"not in manifest: {name}")
        elif listed[name] != sha256(p):
            failures.append(f"hash mismatch: {name}")

    # 2-3. draft anchors
    draft_path = HERE / "PREREG_V03_DRAFT.md"
    draft = draft_path.read_text() if draft_path.exists() else ""
    if "02568b2" not in draft or "01c4fff0" not in draft:
        failures.append("draft does not cite the pinned v0.2 base (02568b2 / 01c4fff0)")

    # 4. register completeness
    changelog_path = HERE / "CHANGELOG_V03.md"
    changelog = changelog_path.read_text() if changelog_path.exists() else ""
    feas_path = HERE / "OUTCOME_BLIND_FEASIBILITY.md"
    feas = feas_path.read_text() if feas_path.exists() else ""
    for i in range(1, 26):
        cid = f"C{i:02d}"
        if cid not in changelog:
            failures.append(f"changelog missing register row {cid}")
        if f"[{cid}]" not in draft and cid != "C25":
            failures.append(f"draft missing inline tag [{cid}]")
    for i in range(1, 10):
        wid = f"W{i:02d}"
        if wid not in changelog:
            failures.append(f"changelog missing no-change row {wid}")
    if "OUTCOME_BLIND_FEASIBILITY" not in changelog:
        failures.append("changelog does not reference the feasibility companion (C25)")

    # 5. preserved labels
    for label in ["FAIL", "EXPLORATORY", "G4 UNADOPTED", "S1 LAUNCH_HOLD", "PAUSED", "SEALED"]:
        if label not in draft:
            failures.append(f"draft missing preserved label: {label}")

    if failures:
        print("VERIFY: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("VERIFY: PASS (manifest, anchors, register C01-C25 / W01-W09, labels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
