# TD closed-session classifier — offline implementation (QF-TD-CLOSED-SESSION-CLASSIFIER-OFFLINE-20261014-17 r1)

Date: 2026-10-14. Canonical task + adjudication: GitHub Issue #1 comment 6176337687 (SCOPED ACCEPT of the -15 design). Spec: `TD_CLOSED_SESSION_SEMANTICS_20261014.md` (commit `3b47426`, sha `bac660f9…`) §5/§7. Mode: OFFLINE only — zero vendor/auth/network calls, zero credits, zero spend, no merge, no live-state/ledger/manifest mutation, no frozen-system change, no SPT08 dispatch. Budget: 60 min incl. one repair pass ≤15 min — used 0 repair passes (first-pass green; see trials).

## Verdict: HOLD (scoped to offline classifier correctness)

The classifier is implemented and its logic is proven 14/14 on the required fixture matrix plus run-loop proofs — **but the candidate is marked HOLD**, per the canonical rule, because the pinned calendar dependency (`pandas_market_calendars`) is **unavailable in the standing environment**: with zero stubs, the real mechanism raises `ModuleNotFoundError`, classification is disabled, and the exact SPT-07 payload takes the pre-existing HOLD path (proven end-to-end, §5). A PASS becomes attainable in an environment providing the pinned mechanism at the pinned version, with zero code changes. No live call and no P2-SPOT v2 adoption is implied by anything here; P2 v1 remains UNMET and SPT08 remains NOT ATTEMPTED.

## 1. Material discrepancy found (disclosed first)

The -15 memo (§3/§5.2) describes the preserved SPT-07 body as `{"code":400,"status":"error","message":"…"}` and states "the error payload carries no `meta`". The **raw preserved bytes** (180 B, sha `3339c341…`) in fact end with `"meta":{"symbol":"AAPL","interval":"1h","exchange":""}` — the sanitized -14 facts omitted it. The classifier is therefore keyed to the **exact observed schema** (below), which includes the meta object; the memo's key-set description is superseded by the bytes. This makes the class *stricter* than the memo's sketch, not looser: any meta deviation routes to HOLD.

## 2. Candidate

| Pin | Value |
|---|---|
| Commit | `ab254c3458697dd450356146abcf4ad4f75ecef4`, tree `fe3c8b34e65153ceece66533c313ea3b62baedf8`, single parent `b18db3ce` |
| Ref | `refs/heads/td-closed-session-classifier-20261014` (pushed; ls-remote verified) |
| Diff vs `b18db3ce` | 3 files, +548/−5 (the 5 deletions are the extended signature/summary/outcome/docstring lines; no logic removed) |
| `td_min_collector.py` | sha256 `b683d277…` (base `bd003c3c…`) |
| `p2_spot_supplement_v2.json` (new) | sha256 `cccd5226…` |
| `test_closed_session_classifier.py` (new) | sha256 `3122bdfc…` |

Main untouched except this report + evidence dir; PR #8 untouched; nothing merged.

## 3. Implementation (isolated candidate only)

**Supplement** (`p2_spot_supplement_v2.json`): versions "P2-SPOT v2" — `supplement_id`/`version`, base manifest id + file sha (`ddff040f…`) + canonical digest (`748ca957…`), calendar pins (mechanism `pandas_market_calendars:XNYS via pilot_harness/validate_input.py::xnys_schedule`; mechanism module sha `1b83cdcd…`; `expected_library_version` `5.5.0`, basis recorded in-file: most recent in-repo recorded mechanism run, CP1 audit 2026-10-04; the -11/-12 runtime version was not recorded), and entries for REQ-SPT-07/08 with `expected_bars == 0` + exact request canonical digests (`a259901e…` / `f547d8fe…`). It does not rewrite P2 v1 and does not convert SPT-07's HOLD.

**Collector changes** (all additive; with no supplement supplied, behavior is byte-identical — proven by supplementary test S2 and the untouched 19/19 lifecycle suite):

- Optional constructor arg `closed_session_supplement` (default `None`); its canonical digest is computed once.
- `_classify_closed_session(req, status, body)` — consulted ahead of the `status != 200` front gate only; returns a proof record iff **every** conjunct holds, else `None` (fall-through to the existing HOLD path byte-for-byte):
  1. **Exact wire match** — HTTP 400; JSON object; keys exactly `{code, message, status, meta}` (any `values` or extra field rejects); `code` is the *integer* 400; `status == "error"`; `message` byte-equal to `"No data is available on the specified dates. Try setting different start/end dates."`; `meta` exactly `{symbol, interval, exchange}` with symbol/interval bound to the request and `exchange == ""` (the exact observed schema; meta is never identity evidence).
  2. **Preregistration binding** — supplement id/version match; `base_manifest_digest` == the collector's manifest digest; entry exists for the request with `expected_bars == 0` (strict int) and `request_digest` == `canonical_digest(req)`.
  3. **Pinned-calendar proof** — the runtime `pandas_market_calendars.__version__` equals the supplement pin, the `validate_input` module bytes hash to the supplement pin, and `xnys_schedule` returns `None` for **every** date in `[start_date, end_date]` (window length capped at 366 days). Any exception (library absent, module mismatch, unresolvable date) → `None`: **classification disabled, fail-closed**. No package was installed and no substitute calendar exists anywhere in the code.
- On classification: raw body preserved write-once as `<rid>.closed_day.bin`; lifecycle event `CLOSED_DAY_EVIDENCED` carrying body sha256/bytes, request digest, manifest digest, supplement digest, calendar proof digest (mechanism + library version + module sha + per-date closed results) and `lifecycle_class=EXPECTED_EMPTY_CLOSED_SESSION`. **No receipt is written, no RECEIVED/COMPLETED event is emitted, bar validation is never invoked, no venue/completion/construction claim exists.** The credit reservation stands spent.
- Run loop: a `CLOSED_SESSION` sentinel (neither success nor HOLD) records the request under `closed_day_evidenced` in pilot state and **continues to the next request** — the single behavioral change, per contract. Terminal outcome string becomes `COMPLETE_WITH_CLOSED_DAY_EVIDENCED` when any request classified. Restart safety: evidenced requests are excluded from the crash-reconcile AMBIGUOUS set and are skipped without redispatch on re-run (digest-checked), so a spent credit can never be re-spent (supplementary test S3).

## 4. Fixture matrix (network-disabled, loopback-only socket guard)

New suite `test_closed_session_classifier.py`: **18 tests, OK** (evidence: `classifier_suite_output.txt`, `matrix_results.json`).

- **F1 PASS** — preserved payload (byte-identical, provenance asserted: 180 B, sha `3339c341…`) + single closed day → classified; run **continued**; following stubbed request dispatched + completed.
- **F2 PASS** — multi-day all-closed window (2026-07-03→05) → classified; run continued.
- **N1–N12 all PASS** — mixed window; one-char message mutation; code/status missing/retyped/altered (4 variants); HTTP-200 empty values; HTTP-200 error body; auth-style 400; 401/403/429/500 (4 variants); unparseable body; not preregistered (absent + nonzero variants); calendar unavailable/version-mismatch (3 variants); `values` field present; manifest/request digest mismatch (2 variants). Every negative asserts the following request was **not** dispatched (transport count == 1) and the batch ends HOLD.
- Supplementary: S1 meta-symbol mismatch → HOLD; S2 no supplement → pre-existing behavior; S3 restart never redispatches an evidenced request.
- Calendar-stub disclosure: in the unit harness the pinned mechanism is stubbed at its interface (`xnys_schedule` results + library `__version__`), the established accepted-dependency pattern of this codebase's suites; the stub's module identity is the real pinned `validate_input.py` bytes, whose hash the classifier verifies. The **real** mechanism's availability is probed separately (§5) — nothing is silently substituted.

## 5. Real-environment fail-closed proof (zero stubs)

`real_env_probe.py` (evidence) ran the candidate collector with the real `pilot_harness` dependencies, the real REQ-SPT-07/08 requests, and the real supplement (probe-local copy with `base_manifest_digest` recomputed for the 2-request probe manifest — the only deviation, disclosed in the script): `xnys_schedule` → `ModuleNotFoundError: No module named 'pandas_market_calendars'` (absent from the standing environment: system dist-packages contain pandas 2.1.4 only, and the standing python cannot import the library. **Correction, recorded after first delivery:** a filesystem-wide search that was still running during the task completed afterward and found exactly one copy on the box — an ephemeral venv at `/tmp/td14_venv` (pandas_market_calendars **4.5.1**) left over from the -14 live-screen run. `/tmp` does not survive VM replacement and that venv is not the standing environment, and 4.5.1 in any case *differs* from the pinned 5.5.0, so classification would fail closed on the version conjunct even if that interpreter were used. The fail-closed outcome and the HOLD verdict are unchanged. Open pin question for adjudication: the TD lineage's own recent runs appear to have used 4.5.1 (the -14 venv), while the supplement pins 5.5.0 from the CP1 audit's recorded mechanism run — if ChatGPT prefers the lineage's version as the pin, that is a one-line supplement change plus a re-run of the matrix and a real-mechanism positive test under that interpreter, as a follow-up task.) Outcome: `HOLD: HTTP 400 for REQ-SPT-07`; transport called exactly once (SPT-08 never dispatched); rejected evidence preserved; **no** `closed_day.bin`, **no** `CLOSED_DAY_EVIDENCED` event; state HOLD. **FAIL-CLOSED CONFIRMED.**

## 6. Regression suites (same environment, guard; base vs candidate diffed)

| Suite | Base `b18db3ce` | This candidate | Delta |
|---|---|---|---|
| Collector lifecycle (19) | 19 run, OK (baseline) | **19 run, OK** | none |
| Pinned integration (16) | 16 run, FAILED (4F/3E) + writer `PackageNotFoundError` | 16 run, FAILED (4F/3E) + identical writer error | **failure sets identical** (diff-verified) |
| Adapter (41) | 41 run, FAILED (4F/1E) + writer `PackageNotFoundError` | 41 run, FAILED (4F/1E) + identical writer error | **failure sets identical** (diff-verified) |

The integration/adapter failures are **pre-existing standing-environment gaps** (real-calendar validation tests need the absent `pandas_market_calendars`; adapter isolation tests hit sandbox transport limits; both suites' results writers require the library's metadata). They are unchanged by this task — the collector suite most exposed to the change is fully green, and the adapter suite does not import the collector. In the -12 disposable environment (which had the library) these suites were 16/16 and 41/41. Socket guard log: the only blocked attempt is the adapter suite's own RFC-5737 `192.0.2.1` blackhole probe, handled fail-closed by design.

## 7. Trials

1. New classifier suite — first run: **18/18 OK**. No repair pass used.
2. Integration + adapter suites initially reported only the post-run `PackageNotFoundError`; inspection showed the tests run first and outcomes land in `test_output.txt` — re-ran capturing those, then diffed failure sets against a pristine base worktree (identical). Investigation only; no code change resulted.
3. Real-env probe — first run: FAIL-CLOSED CONFIRMED as designed.

## 8. Protected-artifact verification (byte-identical before/after)

Live credit ledger `7e5ccef0…` (spent 8); SPOT8 state `80950fcb…`/`04b26958…`; SPT-07 rejected `3339c341…`; -09 P1H state `8c59a56c…`/`fbdbd1c3…` + receipt `c47bf899…`; manifests V1 `66a31e10…`, V2 `4a6e3a55…`, SPOT8 `ddff040f…`; base candidate ref `b18db3ce` unchanged (ls-remote). All work ran in disposable `/tmp` worktrees/state dirs; the live state directories were never opened by any run in this task.

## 9. What does not change

P2 v1 UNMET; REQ-SPT-08 **NOT ATTEMPTED** (and never dispatched in this task — the only SPT-08 appearances are stubbed fixtures and a probe transport that was never called); SPOT8 terminal HOLD untouched; 1H→4H `CONSTRUCTION_HOLD` unchanged (this class is never construction-admissible); no merge; PR #8 untouched; vendor documentation for the 400 remains UNKNOWN with exactly one empirical observation — the class is keyed to that single observation's exact bytes and widens for nothing.

Evidence: `research_notes/td_closed_session_classifier_evidence_20261014/` (`matrix_results.json`, `candidate_manifest.json`, suite outputs, `netguard_log.txt`, `real_env_probe.py` + output, guard runner). Deliverables left uncommitted in the main worktree for the parent to commit/push/post.
