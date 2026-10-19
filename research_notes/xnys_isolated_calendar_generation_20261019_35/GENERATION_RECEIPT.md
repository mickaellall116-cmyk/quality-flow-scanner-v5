# Generation receipt — QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1

Filled per `RECEIPT_TEMPLATE.md` of the -34 r2 contract package
(`xnys_schedule_generation_contract_20261019_34`, commit `a3761ef`).

## 1. Run identity

- Generation task ID (the explicit GO): `QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1`
- GO reference: GitHub Issue #1 comment `6267293436` (user GO recorded by ChatGPT; contract §7 GO)
- Contract package commit this run executed under: `a3761efdff45127aaa5cad39186b07658b0cad32` (-34 r2)
- Operator: Muse
- Run window UTC: 2026-10-19T12:40:23Z .. 2026-10-19T12:44:58Z
- Elapsed minutes: ~5 (cap: 60) · Repair minutes: ~2 (see §11 disclosure)

## 2. Environment (built by this run, isolated, offline)

- Interpreter: Python 3.12.3 (expect CPython 3.12.3) ✓
- Platform: linux x86_64, glibc 2.39 (≥ 2.17) ✓
- Venv path (outside repo, outside system site-packages): `~/workspace/qf35_work_20261019/venv` (scratch; evidence committed here, venv itself not committed)
- Wheelhouse manifest SHA-256: observed `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b` = expected ✓
- Wheel-by-wheel verification: 11/11 PASS vs contract §2 table
- Lock file SHA-256: observed `f5e8440d4fce1704dfdb40387b0ba7c9b6e007e76f9a8564efb4f8b06405b809` = expected ✓
- `pip freeze` SHA-256: observed `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` = NL lock, byte-identical ✓ (copy: `freeze.txt`)
- Network during install/generation: NONE — enforcement: every build/run command executed inside `unshare -n` (fresh network namespace, no interfaces) with all proxy env vars unset (`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy`); pip additionally constrained by `--no-index --no-cache-dir --require-hashes --find-links <wheelhouse>`. Attempted accesses: 3 deliberate probes, ALL FAILED — urllib `URLError [Errno -3] Temporary failure in name resolution`, curl `Could not resolve host`, raw socket `OSError [Errno 101] Network is unreachable` (build log); 1 further probe in the emissions context also `Network is unreachable`. Zero successful network accesses.

## 3. Commands as executed (verbatim, placeholders resolved)

```text
# pre-flight (read-only, before any install)
sha256sum of all 9 primary artifacts vs SOURCE_SET_MANIFEST.json  -> 9/9 PASS
sha256sum PROPOSED_HASH_LOCK.txt                                  -> f5e8440d... PASS
sha256sum wheelhouse SHA256_MANIFEST.txt + 11 wheels              -> 210b8273... + 11/11 PASS

# environment build + emissions + consumer checks — ALL inside:
unshare -n env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy bash <script>

python3.12 -m venv ~/workspace/qf35_work_20261019/venv
venv/bin/python -m pip install --no-index --no-cache-dir --require-hashes \
  -r research_notes/qualified_calendar_env_route_preflight_20261018_29/PROPOSED_HASH_LOCK.txt \
  --find-links ~/workspace/td_nl_wheelhouse_20261016/wheels
venv/bin/pip freeze > freeze.txt        # sha256 08b38cfa... == NL lock

venv/bin/python generator.py --path A --start 2024-09-16 --end 2026-10-16 --out emission_A.json
venv/bin/python generator.py --path C --start 2024-09-16 --end 2026-10-16 --out emission_C.json
venv/bin/python generator.py --path A --start 2024-01-01 --end 2024-12-31 --out aux2024 (A and C)
venv/bin/python generator.py --path A --start 2026-01-01 --end 2026-12-31 --out aux2026 (A and C)
# ... each emission repeated in full (run 2) for determinism ...
venv/bin/python assemble.py emission_A.json emission_C.json artifact.json agreement.json   (x2)

cd <mirrored -25..-28 tree>/validation_fold_coverage_boundary_20261018_28 && python3 test_fold_coverage_boundary.py
python3 consumer_parse.py   # fold_materializer_v3.materialize on 1043 synthetic timestamps
```

stdout/stderr files (this package, `logs/`): build_stdout.txt `4647ffce…` / build_stderr.txt `d2b9b0cf…`;
emissions_stdout.txt `77fb4cda…` / emissions_stderr.txt `98262137…`;
suite_stdout.txt `42ce60f1…` / suite_stderr.txt `47bf1890…`;
parse_stdout.txt `1e5b61c6…` / parse_stderr.txt `e3b0c442…` (empty);
attempt-1 (v1) emissions logs preserved as attempt1_v1_emissions_stdout.txt `aac7cf46…` / attempt1_v1_emissions_stderr.txt `60913848…`.

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

- Generator source: `generator.py` (this package) · SHA-256 of the version that produced the committed emissions (v2, hashed BEFORE its first run): `2995b124f9cd42ef3ddb0122684311e29bf2690177656e31e890ef1de2488114`
- Assembler: `assemble.py` SHA-256 `6a6308f9dda44c04cce972e3532398d72ebc82ca6d7445cdfcc84dbc6f9191e4` (hashed before first run)
- v1 generator SHA-256 `994cc7cf9cfc25ba8491f0199bbc4662d32de5fbd6f631d69216bb1cc0c27bbf` — FAILED on path C (see §11 disclosure); superseded by v2 within this run. NOTE: v2's path-A emission is byte-identical to v1's path-A emission (both `ac52dd41…`), so the repair changed no emitted A content.
- Path A key used: exactly `NYSE` · mirror key/module used: NO (confirmed — source contains no mirror reference; R3)
- Path C key used: exactly `XNYS` (direct on exchange_calendars)

## 7. Emissions and consistency (NOT qualification)

- Emission A sessions (interval): 524 · file SHA-256 `ac52dd41f0dcb8fda686bdbbfe6504acce07abbc047597009ae2b61e191b79d9`
- Emission C sessions (interval): 524 · file SHA-256 `ac52dd41f0dcb8fda686bdbbfe6504acce07abbc047597009ae2b61e191b79d9` (byte-identical file)
- A vs C agreement: AGREE — logged as a CORRELATED CONSISTENCY check only (common-ancestor libraries, -30). Qualification rests solely on §8.
- Disagreement log: none (agreement.json: AGREE, differences [])
- Determinism: second full repetition byte-identical (emissions A, C, aux, and both assemblies): PASS
- Auxiliary emissions: 2024 full-year 252 sessions (A == C, file `b77b32e84f99c224a27440e1185f26f47ac34cc340171f8ad8facc19413f9cbe`); 2026 full-year 251 sessions (A == C, file `26b0ab7c53d7f5f412472151855e7ec9f522b7ab109d00491ba59f554afd6d45`)

## 8. Parity results (qualification — per PARITY_MATRIX.md; full row detail in `parity_results.json`)

- Rows total: 48 (identity: 2 HRS + 22 CLO + 6 EC + 3 CNT + 1 MST + 4 STR + 8 R + 2 COR = 48) · PASS: 48 · FAIL: 0
- Master date sweep [2024-09-16, 2026-10-16]: PASS (761/761 calendar days)
- Session counts: 2024 auxiliary = 252 (expect 252) · 2025 = 250 (expect 250) · 2026 auxiliary = 251 (expect 251) · interval total = 524
- Exception list emitted by the artifact (equals the matrix exactly):
  closures (21): 2024-11-28, 2024-12-25, 2025-01-01, 2025-01-09 (Carter), 2025-01-20, 2025-02-17, 2025-04-18, 2025-05-26, 2025-06-19, 2025-07-04, 2025-09-01, 2025-11-27, 2025-12-25, 2026-01-01, 2026-01-19, 2026-02-16, 2026-04-03, 2026-05-25, 2026-06-19, 2026-07-03, 2026-09-07;
  13:00 early closes (5): 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24. Zero 2026 in-interval early closes (EC-06).

## 9. Artifact

- Path (committed): `research_notes/xnys_isolated_calendar_generation_20261019_35/XNYS_SESSION_SCHEDULE_V2.json`
- SHA-256: `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` · Bytes: 28046 · Sessions: 524
- Header check: artifact `XNYS_SESSION_SCHEDULE_V2`; exchange `XNYS`; timezone `America/New_York`; coverage_start `2024-09-16`; coverage_end `2026-10-16`: PASS (STR-01)

## 10. Consumer checks (fold_materializer_v3.py, SHA-256 `e1b0dfed43c7c0817d2816f5398a1601a3886b107f7eb882e2e46a316f53d4c8`, unmodified)

- Frozen -28 synthetic fixture expectations: PASS 25/25, exit 0; the re-run's TEST_RESULTS.json is identical to the frozen committed copy (run in a mirrored -25..-28 tree so the suite's repo-relative preservation paths resolve; the frozen repo package was never written to)
- Real-artifact parse with SYNTHETIC timestamps spanning the interval (no market data): PASS · 1043 synthetic timestamps · coverage_first_session `2024-09-16` · coverage_last_session `2026-10-16` · calendar_digest `f0c346b083f563fd66d041312bef8d34da4bfd07363a23dba9ac34c01942be79` · folds materialized: 4 (`consumer_parse_result.json`)

## 11. Verdict

**SCHEDULE_GENERATED_AND_PINNED (all checks PASS)** — task verdict:
**`GENERATED__AWAITING_INDEPENDENT_CHATGPT_REVIEW`** (not final qualification;
ChatGPT independently inspects the pinned bytes and adjudicates).

Failure-memory keys: NO §6 fail-closed condition fired. Repair keys (run-internal,
disclosed, neither a §6 condition): `GENERATOR_EC_INDEX_TZ_COMPARISON`,
`CONSUMER_SUITE_RELATIVE_PATH_LAYOUT`.

Disclosure of failed attempts / repairs / deviations during this run:
1. Generator v1 (sha `994cc7cf…`, hashed before first run) completed path A but
   FAILED on path C with `TypeError: Cannot compare tz-naive and tz-aware
   timestamps` — exchange_calendars 4.13.2's schedule index is tz-naive while
   v1 compared it against tz-aware bounds. Repair (v2, sha `2995b124…`): the EC
   emitter filters on each session's derived local date instead of the index;
   no other change. All emissions were then regenerated with v2 into fresh
   run1/run2 files; v1 outputs and logs are preserved in this package
   (`logs/attempt1_v1_*`). v2's path-A bytes are identical to v1's.
2. The -28 consumer suite's first invocation (from a flat copy of the -28
   package alone) exited 1 at its preservation-hash step because the suite
   resolves sibling packages (-25/-26/-27) by repo-relative paths; it crashed
   BEFORE writing results (its apparent 25/25 at that point was the copied
   frozen file — not counted). Re-run in a mirrored tree containing all four
   packages: exit 0, 25/25 printed PASS, results file identical to frozen.
3. No other deviation. No network access at any point after the read-only
   public spec fetch; no downloads; no vendor/API/model calls; no market,
   OHLC, or real timestamp data; no holdout access; no backtest/performance;
   no production/trading/ledger change; no Issue #9 work; no prior frozen
   record edited.
