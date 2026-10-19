# Generation receipt template — FUTURE RUN ONLY (inert; do not fill in during -34)

For the separately authorized generation run under
`GENERATION_CONTRACT.md` (package `xnys_schedule_generation_contract_20261019_34`,
contract state `PREP_READY__AWAITING_EXPLICIT_GENERATION_GO`).
The future run copies this template, fills every `<FILL:…>` field, and
commits it with the artifact. Any field left unfilled, or any check not
PASS, means the run's verdict is HOLD and no artifact is pinned.

The exact commands the future run executes are fixed in
`GENERATION_CONTRACT.md` §5 (pre-flight verification → isolated offline
install from the pinned wheelhouse → freeze acceptance → member pins →
dual emission → agreement + assembly → parity review → consumer checks →
receipt). This template additionally requires the run to record the
commands **as actually executed** (verbatim, with placeholders resolved)
in §3 below, so the receipt is self-contained evidence.

---

## 1. Run identity

- Generation task ID (the explicit GO): `<FILL>`
- GO reference (comment/message id authorizing this run): `<FILL>`
- Contract package commit this run executed under: `<FILL>`
- Operator: Muse
- Run window UTC: `<FILL start>` .. `<FILL end>`
- Elapsed minutes: `<FILL>` (cap: per GO) · Repair minutes: `<FILL>`

## 2. Environment (built by this run, isolated, offline)

- Interpreter: `<FILL python --version>` (expect CPython 3.12.3)
- Platform: `<FILL>` (expect linux x86_64, glibc ≥ 2.17)
- Venv path (outside repo, outside system site-packages): `<FILL>`
- Wheelhouse manifest SHA-256 (expect `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b`): `<FILL observed>`
- Wheel-by-wheel verification (11/11 vs manifest): `<FILL PASS/FAIL>`
- Lock file SHA-256 (expect `f5e8440d4fce1704dfdb40387b0ba7c9b6e007e76f9a8564efb4f8b06405b809`): `<FILL observed>`
- `pip freeze` SHA-256 (expect NL lock `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`): `<FILL observed>`
- Network during install/generation: NONE — enforcement mechanism used: `<FILL>`; any attempted access: `<FILL none/details → HOLD>`

## 3. Commands as executed (verbatim)

```text
<FILL: the exact commands run, in order, placeholders resolved —
 install, freeze, member-pin hashing, both emissions, auxiliary-year
 emissions, the repetition pass, assembly, consumer checks>
```

stdout file: `<FILL path>` SHA-256 `<FILL>` · stderr file: `<FILL path>` SHA-256 `<FILL>`

## 4. Source-set verification (before generation)

| Source artifact (per SOURCE_SET_MANIFEST.json) | Expected SHA-256 | Observed | Result |
|---|---|---|---|
| SEC 34-103356 PDF | `5f0263f7…` | `<FILL>` | `<FILL>` |
| NYSE RM-24-12 PDF | `305fab2e…` | `<FILL>` | `<FILL>` |
| ICE release Nov 10, 2023 | `564de593…` | `<FILL>` | `<FILL>` |
| ICE release Nov 8, 2024 | `3b8a67d9…` | `<FILL>` | `<FILL>` |
| Carter notice Dec 30, 2024 | `e1cd4c1a…` | `<FILL>` | `<FILL>` |
| NYSE hours page capture | `79602f7b…` | `<FILL>` | `<FILL>` |
| Trading_Days current | `f90b6d08…` | `<FILL>` | `<FILL>` |
| Trading_Days Dec-2024 vintage | `dd349170…` | `<FILL>` | `<FILL>` |
| Trading_Days Nov-2025 vintage | `414d2ed3…` | `<FILL>` | `<FILL>` |

## 5. Installed-member pins (before generation)

| Member | Expected SHA-256 | Observed | Result |
|---|---|---|---|
| PMC `calendar_registry.py` | `f5e70a90…` | `<FILL>` | `<FILL>` |
| PMC `calendars/nyse.py` | `135ba9dc…` | `<FILL>` | `<FILL>` |
| PMC `holidays/nyse.py` | `e85f5edb…` | `<FILL>` | `<FILL>` |
| PMC METADATA | `1d40c845…` | `<FILL>` | `<FILL>` |
| EC `calendar_utils.py` | `7d12d534…` | `<FILL>` | `<FILL>` |
| EC `exchange_calendar_xnys.py` | `baa39f07…` | `<FILL>` | `<FILL>` |
| EC `us_holidays.py` | `a2444bd7…` | `<FILL>` | `<FILL>` |
| EC METADATA | `b0d856a2…` | `<FILL>` | `<FILL>` |

Library versions as installed: pandas_market_calendars `<FILL 4.5.1>`,
exchange_calendars `<FILL 4.13.2>`, pandas `<FILL>`, numpy `<FILL>`,
tzdata `<FILL>`.

## 6. Generator

- Generator source file: `<FILL path>` · SHA-256 (hashed BEFORE first run): `<FILL>`
- Path A key used (must be exactly `NYSE`): `<FILL>` · mirror key/module used: NO `<FILL confirm>`
- Path C key used (must be exactly `XNYS`): `<FILL>`

## 7. Emissions and consistency (NOT qualification)

- Emission A sessions (interval): `<FILL n>` · file SHA-256 `<FILL>`
- Emission C sessions (interval): `<FILL n>` · file SHA-256 `<FILL>`
- A vs C agreement: `<FILL AGREE / DISAGREE>` — logged as a CORRELATED
  CONSISTENCY check only (common-ancestor libraries, -30).
- Disagreement log (every differing date/open/close; any entry = HOLD):
  `<FILL none / list>`
- Determinism: second full repetition byte-identical: `<FILL PASS/FAIL>`
- Auxiliary emissions: 2024 full-year `<FILL n>` sessions; 2026 full-year `<FILL n>` sessions.

## 8. Parity results (qualification — per PARITY_MATRIX.md)

- Rows total: `<FILL>` · PASS: `<FILL>` · FAIL: `<FILL — any FAIL = HOLD, list row ids>`
- Master date sweep [2024-09-16, 2026-10-16]: `<FILL PASS/FAIL>`
- Session counts: 2024 auxiliary = `<FILL>` (expect 252) · 2025 = `<FILL>` (expect 250) · 2026 auxiliary = `<FILL>` (expect 251) · interval total = `<FILL>`
- Exception list emitted by the artifact (must equal the matrix exactly):
  closures `<FILL list>`; 13:00 early closes `<FILL list>`

## 9. Artifact

- Path (committed): `<FILL>`
- SHA-256: `<FILL>` · Bytes: `<FILL>` · Sessions: `<FILL>`
- Header check: artifact `XNYS_SESSION_SCHEDULE_V2`; exchange `XNYS`;
  timezone `America/New_York`; coverage_start `2024-09-16`;
  coverage_end `2026-10-16`: `<FILL PASS/FAIL>`

## 10. Consumer checks (fold_materializer_v3.py, SHA-256 `e1b0dfed…`, unmodified)

- Frozen -28 synthetic fixture expectations: `<FILL PASS/FAIL + counts>`
- Real-artifact parse with SYNTHETIC timestamps spanning the interval
  (no market data): `<FILL PASS/FAIL>` · coverage_first_session `<FILL>` ·
  coverage_last_session `<FILL>`

## 11. Verdict

`<FILL: SCHEDULE_GENERATED_AND_PINNED (all checks PASS) | HOLD — reason + failing row/check ids>`

Disclosure of any failed attempt, repair, or deviation during this run:
`<FILL none / full description>`
