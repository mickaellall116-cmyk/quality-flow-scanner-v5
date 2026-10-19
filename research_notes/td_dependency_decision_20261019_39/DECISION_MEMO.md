# QF-TD-DEPENDENCY-DECISION-20261019-39 r1 — DECISION MEMO

**RETURN: `DECISION_MEMO_READY__AWAITING_ADJUDICATION`** (all named sources were available and independently inspected; no HOLD condition met.)

Read-only static inspection, one attempt. Spec: Issue #1 comment `6278682899`. Nothing was acquired, installed, imported, run, or altered. This memo does **not** repeat the -38 interface matrix or test plan; it decides nothing — it frames the one decision -38 left open (blockers B1–B3) with the code/evidence consequences of each branch, for adjudication. Elapsed ~10 min of the ≤30 cap. Repair minutes: 0.

---

## 1. Pin origins — independently re-verified today (all sha256 recomputed from committed bytes)

| Byte | Source | sha256 |
|---|---|---|
| Classifier / collector `td_min_collector.py` | commit `ab254c3`, branch `td-closed-session-classifier-20261014` | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` |
| Pin carrier `p2_spot_supplement_v2.json` | commit `ab254c3` | `cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31` |
| Pinned validator `validate_input.py` | commit `ab254c3` | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` |
| Classifier fixture suite | commit `ab254c3` | `3122bdfc5df432932395948216e4ec6cc50e438abe2518cd0a5984154c4d71d0` |
| TD integration lock (`integration_requirements.lock`) | commit `ab254c3` | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` |
| Pilot harness requirements | commit `ab254c3` | `812c526fc0392dd81a4c6224e004eab169e973ec48a3103939f2f61b2ff85066` |

**The 5.5.0 pin's origin (the supplement states it verbatim):** `expected_library_version: "5.5.0"`, basis = *"Most recent in-repo recorded run of the pinned mechanism (CP1 audit 2026-10-04 records mcal.__version__=5.5.0). The -11/-12 runtime library version was not recorded; if the runtime version differs from this pin, classification is disabled (fail-closed)."* The CP1 record is real and was re-read today: `cp1_followup/audit_52symbol.json` (`"mcal_version": "5.5.0"`, repeated per-symbol) and `cp1_evidence_closure/RESAMPLER_XNYS_EVIDENCE.md` ("`pandas_market_calendars` XNYS v5.5.0, consulting `market_open`/`market_close`"). **But the CP1 audit was a different lineage** — the scanner cache-grid forensic audit of 2026-10-04 — not a TD environment.

**The conflict, at the same commit:** both TD dependency locks pin **4.5.1** (`pandas_market_calendars==4.5.1` in `integration_requirements.lock` — the 11-member closure: exchange_calendars 4.13.2, korean_lunar_calendar 0.4.0, numpy 1.26.4, pandas 2.2.3, PMC 4.5.1, pyluach 2.3.0, python-dateutil 2.9.0, pytz 2024.2, six 1.17.0, toolz 1.2.0, tzdata 2026.5 — and in `pilot_harness/requirements.txt`), and `integration_results.json` at `ab254c3` records an actual integration run under PMC **4.5.1**. The committed lineage record `TD_CALENDAR_LINEAGE_20261014.md` (origin/main) already resolved the fact question: *"The supplement's 5.5.0 pin is PROVEN only for a different lineage… The TD lineage's proven version is 4.5.1 (-12: lock + two independent run records). 5.5.0 is proven only for the unrelated CP1 audit environment"* — and names the supplement's basis a conflation of the two environments, "the exact laundering risk comment `6180155845` flagged."

**The gate mechanics (unchanged from -38, re-read today):** `td_min_collector.py:527` — `str(mcal.__version__) != str(cal["expected_library_version"])` disables classification (exact string equality, fail-closed); the mechanism module is separately byte-pinned (`1b83cdcd…`); the validator's oracle is `mcal.get_calendar("XNYS")` → `schedule(start=end=day)` → `market_open`/`market_close` tz-converted to America/New_York (`validate_input.py::xnys_schedule`).

## 2. The exact 5.5.0 dependency gap

- **Missing artifact:** the `pandas_market_calendars==5.5.0` wheel (py3-none-any) — absent from the persistent wheelhouse (exactly the 11-wheel 4.5.1 closure; PMC wheel `7b4f3478…`), absent from the host (system Python has no PMC at all), absent from the repository.
- **Missing evidence:** no committed lock, manifest, or freeze anywhere records 5.5.0's wheel hash or its `Requires-Dist` transitive closure. The gap is therefore **not enumerable offline**: whether 5.5.0's closure is compatible with the standing lock's pinned pandas 2.2.3 / exchange_calendars 4.13.2 / tzdata lines cannot be known until the wheel's metadata is physically in hand.
- **Missing semantics (B2):** whether 5.5.0's `get_calendar("XNYS")` resolves natively or via the exchange_calendars call-through (the -30 audit established the mirror/call-through trap for the versions it inspected) is uninspectable without the wheel. The -38 preregistration handles this honestly — as probe item P8, evidence to be recorded, not assumed.

## 3. Option A — Preserve the 5.5.0 pin; acquire the dependency under a separate GO

**Code consequences:** none. Supplement, classifier, validator bytes all stand; the -38 preregistered 29-check proof (F2 + N12 + S3 + V4 + P8) becomes executable exactly as written once the closure exists.

**Evidence consequences:** a PASS would prove the classifier under an environment **no TD run ever used** — the CP1 audit's environment. It does not repair the provenance defect the lineage record identified; it entrenches it, and creates a second maintained wheelhouse + lock (the 5.5.0 closure) alongside the NL lock, diverging from every TD runtime on record. If 5.5.0's closure conflicts with the pinned pandas/tzdata lines, the proof environment diverges further still. B2's answer would at least be obtained (P8).

**Risk:** provenance/laundering risk (qualifying a TD mechanism against a foreign lineage's environment — the precise failure mode flagged in comment `6180155845`); unquantifiable closure risk until acquisition; permanent dual-lineage maintenance if adopted afterward.

**Minimal future GO sequence:** (1) a scoped acquisition GO naming the exact artifact (public-index `pandas_market_calendars==5.5.0` wheel; hash recorded at capture; closure resolved and frozen into a NEW lock; no install/run in that step); (2) a separate GO to execute the -38 preregistered proof; (3) a keep-vs-repin adjudication (B3) informed by the proof and P8. Three gated steps, the first of which is a network act the current clarification (comment `6278682899`) expressly does **not** authorize.

## 4. Option B — Formally reversion the supplement to the qualified 4.5.1 lineage

**This option is already built and already tested — the decision is adoption, not construction.** On origin/main today:

- Re-pinned candidate supplement `p2_spot_supplement_v2_nl20261015_candidate.json`, sha256 `9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32` — content-identical to the -17 supplement in `entries`, `base_manifest_digest` (`748ca957…`), class, and lifecycle event; **only** the calendar block and lineage metadata differ (PMC 4.5.1, NL lock `08b38cfa…`, mechanism `1b83cdcd…`, qualification commit `7de7950`).
- Real-calendar qualification already executed against it (NLQUAL, 2026-10-15): **28/28 cases PASS, run twice, byte-identical outputs** — the -17 F/N/S fixture families re-expressed against the REAL PMC 4.5.1 and the REAL `validate_input.xnys_schedule`, no calendar stubbing on any positive path, including N10 drift controls (version drifted to 9.9.9 → HOLD; import blocked → HOLD; mechanism raising → HOLD). Provenance body under test was the preserved live REQ-SPT-07 rejection bytes (`3339c341…`), not a reconstruction.
- Adoption packet already drafted: `td_closed_session_classifier_nlqual_evidence_20261015/P2_SPOT_V2_ADOPTION_PACKET_DRAFT.md` (DRAFT, not adopted).

**Code consequences:** one governance act — a new supplement version adopting the candidate bytes (the -17 supplement is never edited in place; its hash identity and the fail-closed design forbid that), plus the collector merged as-is (the draft records: NLQUAL modified zero candidate bytes). The qualified XNYS V2 JSON artifact remains a non-substitute for this gate — unchanged, unrelated lane.

**Evidence consequences:** the classifier aligns with the only lineage ever proven for TD (-12 lock + two independent run records + the NL rebuild/qualification chain). P2 v1 remains UNMET; REQ-SPT-07's v1 HOLD is untouched; REQ-SPT-08 remains NOT ATTEMPTED and still needs its own dispatch task. Check-count honesty: NLQUAL's 28 and the -38 prereg's 29 are **different suites for different pins**, not interchangeable totals. One genuine delta: the -38 P-family mechanism probes (P1–P8, primary-record dates incl. the Carter closure and DST boundaries through the real oracle) have no counterpart in NLQUAL's 28; a small separately-versioned offline delta-proof could cover them under 4.5.1 with **no acquisition** — or adjudication may accept NLQUAL's matrix as sufficient. That judgment is the adjudicator's, not this memo's.

**Risk:** principally process risk — reversioning must be an explicit adjudicated adoption with the -17 candidate formally superseded, so no future consumer cites the stale 5.5.0 supplement. Technical risk is the smaller of the two options: every byte and behavior is already on record and twice-run.

**Minimal future GO:** one adjudicated adoption step (adopt candidate supplement `9c712330…` + collector merge as-is + the NL-20261015 environment requirement), optionally preceded by the offline P-family delta-proof. **No network act at any point.**

## 5. The contrast in one paragraph

Option A spends a network acquisition and two further gated steps to test the classifier in an environment the project's own lineage record has already judged misattributed — and even a PASS leaves the provenance defect in place. Option B asks for a single adjudicated adoption of artifacts that already exist, already hash-pin cleanly, and already carry a twice-run byte-identical real-calendar qualification under the lineage every TD record supports. The 5.5.0 pin is not evidence about TD; it is a CP1 audit fact that wandered into the wrong supplement. The decision itself — and any adoption — belongs to adjudication; this memo's finding is limited to the asymmetry above and to the minimal GOs stated per option.

## 6. Standing state (unchanged by this memo)

-38 verdict stands (`DEPENDENCY_ARTIFACT_MISSING__HOLD` on the 5.5.0 path); the 29-check proof remains preregistered, unrun, and unauthorized. -20 clearance (B5) is independent and untouched. Yahoo HOLD, V5.4 PAUSED, TD data/performance HOLD.

— Muse (worker, -39 r1)
