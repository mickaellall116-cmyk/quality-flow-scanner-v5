# Fixtures — task -87 (offline, synthetic, stdlib-only)

Run any suite with `python3 <file>`; exit 0 = all checks PASS.
Outputs of the author's runs are saved as `output_<suite>.txt`
beside the suites (all four suites re-run after final edits:
13/13, 8/8, 11/11, 10/10 = 42/42 PASS).

| Suite | Gate | What it proves |
|---|---|---|
| `verify_calendar_candidate.py` | 1 | The -81 candidate artifact (pin-checked) regenerates exactly from weekday enumeration minus the ICE instruments' closure sets; abuts -35 V2; union 751 sessions |
| `crypto_calendar_spec.py` + `test_crypto_calendar_spec.py` | 1 | The proposed crypto continuous calendar S-C1…S-C6: session/bin shape, DST absorption, phase-invariance, 09:30/13:30 anchor alignment, XNYS isolation |
| `test_e3_freeze_modes.py` | 2 | The Gate-2 freeze texts' semantics, executed against the -84 producer core: fail-closed switch, mode A exclusion + equality boundary, mode B flag + RETROSPECTIVE_NON_TRADABLE basis, provenance refusals |
| `test_s2_invariance_and_seam.py` | 3 | Uniform-adjustment invariance, mixed-basis seam detectability, and S2's {prev, D, next} exclusion shape over the pinned calendar bytes |

Inputs (`inputs/`) are byte copies of committed artifacts, each
pin-verified inside its suite before use:

- `XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json` —
  sha256 `8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2`,
  from `research_notes/nyse_calendar_2023_evidence_20261021_81/` (commit `9c59ea1`).
- `XNYS_SESSION_SCHEDULE_V2.json` —
  sha256 `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`,
  from `research_notes/xnys_isolated_calendar_generation_20261019_35_r2/`.
- `split_event_producer.py` —
  sha256 `ffa14a8d8dd28975e8e64d7f8c8ccb5df44d14aa361d654cb351fa971f61e9c9`,
  from `research_notes/safeguards_prep_20261021_84/producer/` (commit `f7725bf`).
  Isolated candidate in its home package; copied here so Gate 2's
  fixtures run against the exact pinned bytes. Not integrated.
