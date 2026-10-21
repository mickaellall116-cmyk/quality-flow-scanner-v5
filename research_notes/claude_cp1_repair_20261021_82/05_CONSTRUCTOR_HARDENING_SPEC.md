# ITEM 5 — CONSTRUCTOR HARDENING: FIXTURES + SPEC
## (No pinned code modified; the constructor under test is a byte-copy)

**Subject:** `construct_4h.py` (pinned constructor, sha256
d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd,
`research_notes/pilot_harness/construct_4h.py`). The fixture suite
runs against `fixtures/construct_4h_fixture_copy.py`, extracted
byte-for-byte from origin/main; the suite refuses to run if the
copy's hash differs from the pin. Environment: CPython 3.12.3 /
pandas 2.2.3 (pinned wheelhouse), `unshare -n`. Results:
`fixtures/TEST_EVIDENCE.md` (7/7 PASS, exit 0, repeat-identical).

## H1 — Index-equality assertion [FIXTURE_PROVEN]

Requirement: a constructed 4H frame's index must equal the expected
session-bar index EXACTLY — full sessions contribute {09:30, 13:30},
a 13:00-close session contributes {09:30} only, labels in
America/New_York, no extra, missing, or shifted bars.

Fixture T1 builds three sessions (two full, one 13:00 early close)
from synthetic 1H bars with explicit interval ends and pinned
session closes, and asserts exact index equality plus aggregation
identities (bin Open = first constituent open; bin Volume = sum of
constituents). PASS — the constructed index is exactly
[2024-01-02 09:30, 2024-01-02 13:30, 2024-01-03 09:30,
2024-01-03 13:30, 2024-07-03 09:30] ET. This is the regression the
2026-10-03 candle failure would have failed: there, live bars landed
at 06:30/10:30/14:30 ET because of a resample origin anchored to
midnight UTC; an index-equality assertion against the expected grid
detects that class of defect mechanically, before any strategy sees
the frame.

## H2 — Warnings-as-errors [FIXTURE_PROVEN]

Requirement: construction must run clean under
`warnings.simplefilter("error")`, so a deprecation or pandas
behavior-change warning in the construction path surfaces as a
failure instead of silently altering bars in a future environment.

Fixture T2 first proves the filter is engaged (a probe warning
raises), then runs the full T1 construction under it. PASS — zero
warnings raised. The fixture is environment-sensitive by design: it
must be re-run whenever the pinned wheelhouse changes.

## H3 — Duplicate timestamps [FIXTURE_PROVEN — FINDING RECORDED]

Requirement (as specified for this repair): duplicate 1H timestamps
must be rejected, or handled deterministically, with the behavior
proven by fixture.

Fixture T3 duplicates one 1H bar (2024-01-02 10:30) and runs
construction twice. Result: the behavior is DETERMINISTIC (both runs
byte-identical, output sha 26cc2504…) — and the behavior is a silent
MERGE: **the pinned constructor does not reject duplicate
timestamps.** It sorts and aggregates, so the duplicated bar is
counted twice (fixture 09:30-bin Volume 507 vs the single-copy
expectation 406) and its OHLC enters the bin's first/max/min/last.
Determinism is the floor, not the goal: a duplicated vendor bar
would silently corrupt volume and range in a constructed frame.

Where duplicate safety actually lives today: the VALIDATOR layer.
The cleared entrypoint runs validate_input before construction, and
the frozen fold materializer raises DUPLICATE_TIMESTAMP on its input
contract. The constructor's own docstring says the same thing
("Calling construct_4h.py --input directly bypasses validation and is
NOT the cleared path"). The hardening requirement this evidence
supports:

- **H3a (process, no code change):** no assembly path may call the
  constructor except through the validated entrypoint; any new
  assembly point must demonstrate a duplicate-rejection step
  upstream of construction, with a fixture.
- **H3b (code, SEPARATE GO):** add an explicit duplicate-index guard
  to the constructor itself (raise on `index.duplicated()`), as a
  defense-in-depth change to the pinned chain. This modifies a pinned
  file, so it requires its own adjudicated task, a new pin, and a
  full route re-proof — it is NOT done here and NOT bundled into this
  repair.

**Status: fixtures FIXTURE_PROVEN (H1, H2, H3-determinism);
H3b REQUIRES_SEPARATE_GO.** Owner: Muse (fixtures + spec).
