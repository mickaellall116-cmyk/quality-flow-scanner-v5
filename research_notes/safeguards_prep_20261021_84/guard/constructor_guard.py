#!/usr/bin/env python3
"""
constructor_guard.py — CANDIDATE H3b: duplicate-index fail-closed guard
for the pinned 4H constructor boundary (task -84, Part A).

STATUS: isolated candidate module. It is NOT part of the pinned route,
NOT integrated, and NOT adopted. It wraps a constructor module exposing
construct_4h(...) — in this package, the pin-verified byte-copy of the
pinned constructor (guard/construct_4h_fixture_copy.py, sha256
d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd).

WHY THIS EXISTS: the -82 T3 fixture proved the pinned constructor does
NOT reject duplicate 1H timestamps: it sorts and aggregates, so a
duplicated bar is silently merged (fixture 09:30-bin Volume 507 vs the
single-copy expectation 406) and its OHLC enters the bin's
first/max/min/last. Duplicate safety today lives only in the validator
layer upstream. H3b adds defense-in-depth AT the constructor boundary.

FAILURE SEMANTICS (fail-closed, deterministic):
  - Any duplicated timestamp in the input 1H frame raises
    DuplicateTimestampError BEFORE the constructor is invoked. The
    guard never merges, never drops, never deduplicates silently.
  - Any duplicated timestamp in the constructed output raises the
    same error (defense in depth against a constructor regression).
  - The exception carries a stable machine-readable code and a
    deterministic message: duplicated timestamps are listed in
    first-appearance order for the given input, so two runs over the
    same input bytes produce byte-identical messages.

The guard changes behavior ONLY on invalid input: for duplicate-free
input the guarded path returns the constructor's output unmodified
(proven byte-identical by fixture G3 in test_constructor_guard.py).

Adoption is NOT this module's decision: adopting H3b means a new
constructor version + new pins + a full route re-proof (see
../SPEC_GUARD_H3B.md and ../REPROOF_PLAN.md). Editing the pinned
constructor in place is forbidden — the pin IS the evidence chain.
"""

GUARD_VERSION = "h3b-candidate-1"
DUPLICATE_CODE = "CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP"
INDEX_MISMATCH_CODE = "CONSTRUCTOR_GUARD_INDEX_MISMATCH"


class DuplicateTimestampError(ValueError):
    """Raised when a frame index contains duplicated timestamps."""

    code = DUPLICATE_CODE

    def __init__(self, stage, duplicates, total):
        self.stage = stage
        self.duplicates = [str(d) for d in duplicates]
        self.total = total
        super().__init__(
            f"{DUPLICATE_CODE}: stage={stage} "
            f"duplicated_timestamp_count={total} "
            f"duplicated_timestamps={self.duplicates}"
        )


class IndexMismatchError(ValueError):
    """Raised when a constructed frame's index != the expected index."""

    code = INDEX_MISMATCH_CODE

    def __init__(self, got, expected):
        self.got = [str(t) for t in got]
        self.expected = [str(t) for t in expected]
        super().__init__(
            f"{INDEX_MISMATCH_CODE}: got={self.got} expected={self.expected}"
        )


def find_duplicate_timestamps(index):
    """Duplicated labels in first-appearance order (deterministic)."""
    seen = set()
    dup_seen = set()
    dups = []
    for label in index:
        if label in seen and label not in dup_seen:
            dup_seen.add(label)
            dups.append(label)
        seen.add(label)
    return dups


def count_duplicated_rows(index):
    """Number of rows whose label is duplicated (all copies counted)."""
    if len(index) == 0:
        return 0
    mask = index.duplicated(keep=False)
    return int(mask.sum())


def assert_no_duplicate_timestamps(index, *, stage):
    """Raise DuplicateTimestampError if the index has any duplicates."""
    dups = find_duplicate_timestamps(index)
    if dups:
        raise DuplicateTimestampError(stage, dups, count_duplicated_rows(index))
    return 0


def assert_index_equality(frame, expected_index):
    """The -82 H1 assertion as a callable: exact index equality."""
    got = list(frame.index)
    expected = list(expected_index)
    if got != expected:
        raise IndexMismatchError(got, expected)
    return True


def guarded_construct_4h(constructor_module, frame, *args, **kwargs):
    """
    Fail-closed wrapper around a constructor module's construct_4h.

    Pre-check: the input 1H frame's index must be duplicate-free, or
    DuplicateTimestampError is raised BEFORE the constructor runs.
    Post-check: the constructed frame's index must be duplicate-free.
    On valid input the constructor's output is returned unmodified.
    """
    assert_no_duplicate_timestamps(frame.index, stage="input_1h")
    out = constructor_module.construct_4h(frame, *args, **kwargs)
    assert_no_duplicate_timestamps(out.index, stage="output_4h")
    return out
