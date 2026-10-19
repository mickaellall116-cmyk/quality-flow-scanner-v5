# Generation receipt — QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r2

Filled per `RECEIPT_TEMPLATE.md` of the -34 r2 contract package
(`xnys_schedule_generation_contract_20261019_34`, commit `a3761ef`).
r2 is the clean rerun of r1: r1's artifact bytes were correct but its run
was held unusable on provenance (`HOLD__ARTIFACT_BYTES_REVIEWED__PROVENANCE_GATE_FAILED`)
because the worker repaired two failures mid-run. r2 ran the identical
contract with the pinned r1 generator v2 bytes, a correct mirrored
consumer-suite layout staged before the run, and a hard first-failure-stop
rule. **Exactly one attempt ran; zero repairs, zero retries, zero second
invocations of any component.**

## 1. Run identity

- Generation task ID (the explicit GO): `QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r2`
- GO reference: USER GO recorded Issue #1 comment `6267293436` / `6272648131` (r1 GO + r2 queueing); queue released Issue #1 comment `6277380279` (2026-10-19T21:09:36Z, after -37 r2 acceptance)
- Contract package commit this run executed under: `a3761efdff45127aaa5cad39186b07658b0cad32` (-34 r2)
- Operator: Muse
- Run window UTC: pre-run staging 2026-10-19T21:27Z .. 21:31Z · THE ATTEMPT (single `unshare -n` invocation of `run_all.sh`): 2026-10-19T21:31:19Z .. 2026-10-19T21:31:53Z
- Elapsed minutes: ~20 total task window (cap: 60) · Repair minutes: **0**

## 2. Environment (built by this run, isolated, offline)

- Interpreter: Python 3.12.3 (expect CPython 3.12.3) ✓
- Platform: linux x86_64, glibc 2.39 (≥ 2.17) ✓
- Venv path (outside repo, outside system site-packages): `~/workspace/qf35_r2_work_20261019/venv` (fresh scratch for r2; r1's `qf35_work_20261019/` untouched; venv itself not committed)
- Wheelhouse manifest SHA-256: observed `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b` = expected ✓
- Wheel-by-wheel verification: 11/11 PASS vs wheelhouse manifest (incl. pandas_market_calendars 4.5.1 wheel `7b4f3478…`, exchange_calendars 4.13.2 wheel `fc5a2ad0…`)
- Lock file SHA-256: observed `f5e8440d4fce1704dfdb40387b0ba7c9b6e007e76f9a8564efb4f8b06405b809` = expected ✓
- `pip freeze` SHA-256: observed `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` = NL lock, byte-identical ✓ (copy: `freeze.txt`)
- Network during install/generation: NONE — enforcement: the entire attempt executed inside ONE `unshare -n` invocation (fresh network namespace, no interfaces) with all proxy env vars unset (`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy`); pip additionally constrained by `--no-index --no-cache-dir --require-hashes --find-links <wheelhouse>`. Attempted accesses: 3 deliberate probes in the build context, ALL FAILED — urllib `URLError [Errno -3] Temporary failure in name resolution`, curl `Could not resolve host`, raw socket `OSError [Errno 101] Network is unreachable` (build log); 1 further probe in the emissions context also `Network is unreachable`. Zero successful network accesses.

## 3. Commands as executed (verbatim, placeholders resolved)

```text
# pre-flight (read-only, before any install — NOT part of the attempt)
sha256sum of all 9 primary artifacts vs SOURCE_SET_MANIFEST.json  -> 9/9 PASS
sha256sum PROPOSED_HASH_LOCK.txt                                  -> f5e8440d... PASS
sha256sum wheelhouse SHA256_MANIFEST.txt + 11 wheels              -> 210b8273... + 11/11 PASS
sha256sum pinned generator/assembler/parity/parse/materializer    -> 2995b124 / 6a6308f9 / 12a48d7e / 3e9505b5 / e1b0dfed PASS

# THE ATTEMPT — one invocation, strict sequence, first failure aborts:
unshare -n env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy bash run_all.sh

  # phase BUILD (scripts/build_env.sh -> logs/build_stdout.txt / build_stderr.txt)
  python3.12 -m venv ~/workspace/qf35_r2_work_20261019/venv
  venv/bin/python -m pip install --no-index --no-cache-dir --require-hashes \
    -r research_notes/qualified_calendar_env_route_preflight_20261018_29/PROPOSED_HASH_LOCK.txt \
    --find-links ~/workspace/td_nl_wheelhouse_20261016/wheels
  venv/bin/pip freeze > freeze.txt        # sha256 08b38cfa... == NL lock, asserted in-script
  venv/bin/python scripts/check_members.py   # 8/8 installed-member pins, asserted in-script

  # phase EMISSIONS (scripts/run_emissions.sh -> logs/emissions_stdout.txt / emissions_stderr.txt)
  venv/bin/python generator.py --path A --start 2024-09-16 --end 2026-10-16 --out out/emission_A_run1.json
  venv/bin/python generator.py --path C --start 2024-09-16 --end 2026-10-16 --out out/emission_C_run1.json
  venv/bin/python generator.py --path A --start 2024-01-01 --end 2024-12-31 --out out/aux2024_A_run1.json
  venv/bin/python generator.py --path C --start 2024-01-01 --end 2024-12-31 --out out/aux2024_C_run1.json
  venv/bin/python generator.py --path A --start 2026-01-01 --end 2026-12-31 --out out/aux2026_A_run1.json
  venv/bin/python generator.py --path C --start 2026-01-01 --end 2026-12-31 --out out/aux2026_C_run1.json
  venv/bin/python assemble.py out/emission_A_run1.json out/emission_C_run1.json out/artifact_run1.json out/agreement_run1.json
  # ... the same 7 commands repeated in full with run2 outputs (determinism pass) ...

  # phase SUITE (single invocation, mirrored -25..-28 layout staged BEFORE the run)
  cd notes_mirror/validation_fold_coverage_boundary_20261018_28 && python3 test_fold_coverage_boundary.py

  # phase PARSE
  venv/bin/python consumer_parse.py   # fold_materializer_v3.materialize on 1043 synthetic timestamps

  # phase PARITY
  python3 parity_check.py             # -> PARITY 48/48 PASS
```

stdout/stderr files (this package, `logs/`): build_stdout.txt `d31d98cc…` / build_stderr.txt `e3b0c442…` (empty);
emissions_stdout.txt `caead2d3…` / emissions_stderr.txt `e3b0c442…` (empty);
suite_stdout.txt `8057cee1…` / suite_stderr.txt `e3b0c442…` (empty);
parse_stdout.txt `1e5b61c6…` / parse_stderr.txt `e3b0c442…` (empty);
parity_stdout.txt `0fdbd8e7…` / parity_stderr.txt `e3b0c442…` (empty);
ATTEMPT_STATUS.txt `00d6d8ac…` (final state: ATTEMPT_COMPLETE).

## 4. Source-set verification (before generation) — 9/9 PASS

| Source artifact | Expected SHA-256 | Observed | Result |
|---|---|---|---|
| SEC 34-103356 PDF | `5f0263f767a7e9b387ded9e7cd4132f9dc20e6e2762196d23aaab14912034e58` | same | PASS |
| NYSE RM-24-12 PDF | `305fab2e09c33969f1928a3d57c26a20e99496327ac6ae3bd974927b7f0eb982` | same | PASS |
| ICE release Nov 10, 2023 | `564de593a271484e29af86b2c7054075b21c16df85c3fbc831e0ef6d3f6b8c10` | same | PASS |
| ICE release Nov 8, 2024 | `3b8a67d90f57fcaa836e1f6f047c50629fc98170465b8e88b5a7293f0b5ce7e1` | same | PASS |
| Carter notice Dec 30, 2024 | `e1cd4c1a21a9db1b05e201f03c74caac13a00b9246d3323db751da2c0eae2ee7` | same | PASS |
| NYSE hours page capture | `79602f7be5a8f1d39c2b1cac4dd02c4c07f18cf9f92d70602834069154719bad` | same | PASS |
| Trading_Days current | `f90b6d08c4f3e82af53e6139837058abb7a1e7770ea6c716b1ab5dbcb413139f` | same | PASS |
| Trading_Days Dec-2024 vintage | `dd3491706421f635fcfc489a28146902e5056f7e75f4efef1eb6b06ea9da7803` | same | PASS |
| Trading_Days Nov-2025 vintage | `414d2ed348c6e36fd9cb163f7d7ba6e7cb70d8d57c793db696cf1e4697f5cd87` | same | PASS |

## 5. Installed-member pins (before generation) — 8/8 PASS

Verified in-script during the BUILD phase (`scripts/check_members.py`,
hash-search over the fresh venv's site-packages):

| Member | Expected SHA-256 | Observed | Result |
|---|---|---|---|
| PMC `calendar_registry.py` | `f5e70a904464ced8b055a39756c59f51c12f693e7f4b0c290f955a5002614756` | same | PASS |
| PMC `calendars/nyse.py` | `135ba9dc683eb6797fba014d8e5979d0dc12537fa23fcabd7f2302c94712f4e3` | same | PASS |
| PMC `holidays/nyse.py` | `e85f5edb348f4b6455ac92b97e10b81a70975bab7c7e97cf7a616c82c56ac4b3` | same | PASS |
| PMC METADATA | `1d40c845ac4b7db1d0d9fe46cfdd8b881732977208fdd376c00b1f7ce9e71525` | same | PASS |
| EC `calendar_utils.py` | `7d12d53482fe295bd5a9b272a635df2292528b8dc19538c93649fa4ee84b40e6` | same | PASS |
| EC `exchange_calendar_xnys.py` | `baa39f07163abafcf2800b69edc5d920c3db0a64f8bbb30dc7d522883d0b5bd7` | same | PASS |
| EC `us_holidays.py` | `a2444bd7aef3ff651faff3f9117c47a0d41e9e7c312f38ecf42403e4d996830e` | same | PASS |
| EC METADATA | `b0d856a2f790e0d645d5847880ccd21de2771921a7ed78464184da4cd73289ec` | same | PASS |

Library versions as installed: pandas_market_calendars 4.5.1, exchange_calendars 4.13.2, pandas 2.2.3, numpy 1.26.4, tzdata 2026.5 (full freeze: `freeze.txt`, sha `08b38cfa…`).

## 6. Generator

- Generator source: `generator.py` (this package) · SHA-256 `2995b124f9cd42ef3ddb0122684311e29bf2690177656e31e890ef1de2488114` — the pinned r1 v2 bytes, copied byte-exact and hash-verified BEFORE the run; NOT edited.
- Assembler: `assemble.py` SHA-256 `6a6308f9dda44c04cce972e3532398d72ebc82ca6d7445cdfcc84dbc6f9191e4` (pinned r1 bytes, unmodified).
- Parity checker: `parity_check.py` SHA-256 `12a48d7e64337eae42e476ee205eccbf5faddae9a266f94f6e4f0dc6e46ff30b` (pinned r1 bytes, unmodified).
- Consumer parse: `consumer_parse.py` SHA-256 `3e9505b5abb2f254ae19417de415ebb3cee5c395a5e450a43fd329050719e2c2` (pinned r1 bytes, unmodified).
- Path A key used: exactly `NYSE` · mirror key/module used: NO (confirmed — source contains no mirror reference; R3)
- Path C key used: exactly `XNYS` (direct on exchange_calendars)

## 7. Emissions and consistency (NOT qualification)

- Emission A sessions (interval): 524 · file SHA-256 `ac52dd41f0dcb8fda686bdbbfe6504acce07abbc047597009ae2b61e191b79d9`
- Emission C sessions (interval): 524 · file SHA-256 `ac52dd41f0dcb8fda686bdbbfe6504acce07abbc047597009ae2b61e191b79d9` (byte-identical file)
- A vs C agreement: AGREE — logged as a CORRELATED CONSISTENCY check only (common-ancestor libraries, -30). Qualification rests solely on §8.
- Disagreement log: none (agreement.json: AGREE, differences [])
- Determinism: second full repetition byte-identical (emissions A, C, both aux years, and both assemblies): PASS — run2 artifact also `3358f2d9…` (committed under `emissions/run2/`)
- Auxiliary emissions: 2024 full-year 252 sessions (A == C, file `b77b32e84f99c224a27440e1185f26f47ac34cc340171f8ad8facc19413f9cbe`); 2026 full-year 251 sessions (A == C, file `26b0ab7c53d7f5f412472151855e7ec9f522b7ab109d00491ba59f554afd6d45`)
- **Byte identity vs r1: r2's emissions and artifact are byte-identical to r1's held artifact (`3358f2d9…`) and emissions (`ac52dd41…`). The bytes did not change; the provenance did — this run is the first clean production of them.**

## 8. Parity results (qualification — per PARITY_MATRIX.md; full row detail in `parity_results.json`)

- Rows total: 48 (identity: 2 HRS + 22 CLO + 6 EC + 3 CNT + 1 MST + 4 STR + 8 R + 2 COR = 48) · PASS: 48 · FAIL: 0
- Family tally (recounted from the enumeration): HRS 2/2, CLO 22/22, EC 6/6, CNT 3/3, MST 1/1, STR 4/4, R 8/8, COR 2/2
- Master date sweep [2024-09-16, 2026-10-16]: PASS (761/761 calendar days)
- Session counts: 2024 auxiliary = 252 (expect 252) · 2025 = 250 (expect 250) · 2026 auxiliary = 251 (expect 251) · interval total = 524
- Exception list emitted by the artifact (equals the matrix exactly):
  closures (21): 2024-11-28, 2024-12-25, 2025-01-01, 2025-01-09 (Carter), 2025-01-20, 2025-02-17, 2025-04-18, 2025-05-26, 2025-06-19, 2025-07-04, 2025-09-01, 2025-11-27, 2025-12-25, 2026-01-01, 2026-01-19, 2026-02-16, 2026-04-03, 2026-05-25, 2026-06-19, 2026-07-03, 2026-09-07;
  13:00 early closes (5): 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24. Zero 2026 in-interval early closes (EC-06).

## 9. Artifact

- Path (committed): `research_notes/xnys_isolated_calendar_generation_20261019_35_r2/XNYS_SESSION_SCHEDULE_V2.json`
- SHA-256: `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` · Bytes: 28046 · Sessions: 524
- Header check: artifact `XNYS_SESSION_SCHEDULE_V2`; exchange `XNYS`; timezone `America/New_York`; coverage_start `2024-09-16`; coverage_end `2026-10-16`: PASS (STR-01)

## 10. Consumer checks (fold_materializer_v3.py, SHA-256 `e1b0dfed43c7c0817d2816f5398a1601a3886b107f7eb882e2e46a316f53d4c8`, unmodified)

- Frozen -28 synthetic fixture expectations: PASS 25/25, exit 0, on the suite's SINGLE invocation — run in the mirrored -25..-28 tree staged before the run (the r1 layout failure cannot recur; the frozen repo packages were never written to); the run's TEST_RESULTS.json is identical to the frozen committed copy (parity row R7).
- Real-artifact parse with SYNTHETIC timestamps spanning the interval (no market data): PASS · 1043 synthetic timestamps · coverage_first_session `2024-09-16` · coverage_last_session `2026-10-16` · calendar_digest `f0c346b083f563fd66d041312bef8d34da4bfd07363a23dba9ac34c01942be79` · folds materialized: 4 (`consumer_parse_result.json`)

## 11. Verdict

**SCHEDULE_GENERATED_AND_PINNED (all checks PASS)** — task verdict:
**`GENERATED__AWAITING_INDEPENDENT_REVIEW`** (not final qualification;
ChatGPT independently inspects the pinned bytes and adjudicates).

Failure-memory keys: NONE — no §6 fail-closed condition fired; no failure
of any component occurred at any step.

Disclosure of failed attempts / repairs / deviations during this run:
**NONE.** Exactly one attempt ran (one `unshare -n` invocation,
2026-10-19T21:31:19Z–21:31:53Z), comprising the contract's fixed sequence
(build → emissions ×2 for determinism → single suite invocation → parse →
parity). Zero repairs, zero retries, zero re-invocations, zero edits to
any pinned byte. No network access at any point after the read-only public
spec fetch; no downloads; no vendor/API/model calls; no market, OHLC, or
real timestamp data; no holdout access; no backtest/performance; no
production/trading/ledger change (the V5.4 harness was not touched); no
Issue #9 work; no prior frozen record edited. The r1 package
(`xnys_isolated_calendar_generation_20261019_35/`) is untouched.
