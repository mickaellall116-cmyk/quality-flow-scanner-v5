# Stage C audit response — repair patch (Run 1 preserved)

Date: 2026-09-29. Auditor: Mike. Verdict on Run 1 (`66bc1e8`): **HOLD /
REDLINE REQUIRED**. Nothing downstream starts. No frozen strategy rules
need changing.

Run 1 is preserved untouched at commit
`66bc1e8b1eb4cce020f4d19c2acc8258e948301a`. This patch (new commit, on
top) contains only the narrow repairs below. **No rerun has been executed;
the rerun (Run 2) happens only after Mike approves this patch** — B8.3(b)
independent review is Mike's call on this patch.

## The three findings and what was actually wrong

### 1. Acquisition not reproducible (committed fetch_4h.py lacked the fallback)
Mike: "committed fetch_4h.py has no period='max' fallback, yet GEV/RDDT/TEM
were produced with period=max and the manifest contains fields the committed
script never writes."

Confirmed exactly. The committed Run 1 `fetch_4h.py` called only
`period="730d"` with retries of the same call, wrote raw files only as
`{SYM}_p730.csv`, and wrote 5-field manifest records
(symbol/fetched_at_utc/completed_at_utc/n_1h/error). But the committed
manifest's GEV record carries 8 fields including
`fetch_shape: "period=max (period=730d server-errors for this ticker)"`,
`first_1h`, `last_1h` — and the raw file on disk is `GEV_pmax.csv`. The
actual Run 1 acquisition used an uncommitted fallback path, and the
manifest was augmented after the fact. `build_4h.py` (loads both `p730`
and `pmax` tags) and `STAGE_C_REPORT.md` (documents the period="max"
recovery) already described the real path — only the fetch script lied.

**Repair:** `fetch_4h.py` rewritten to BE the exact path: primary
`period="730d"` with bounded retries, then a deterministic `period="max"`
fallback (same endpoint/interval/prepost/auto_adjust) when the primary is
exhausted; per-symbol manifest records `fetch_shape`, `first_1h`,
`last_1h`, `n_1h`, `error`, `attempts`; raw files named `{SYM}_p730.csv` /
`{SYM}_pmax.csv` matching the shape used. Frozen-rule basis (B8.3a):
rev-6.1 §11 (fresh 4H cache construction; no quarantined reuse).

### 2. Gate C comparator checked the wrong field
Mike: "rev-6.1 §5B requires comparison against expected_4h; compare_4h.py
actually calculates its gaps and exactness against actual_4h."

Confirmed. Run 1 `compare_4h.py` computed `bar_count_gap =
t["actual_4h"] - m["n_4h"]`. §5B: "Check against coverage_report.json's
expected bar counts". The fields differ on real symbols (GEV: expected 933
vs actual 936; XYZ: expected 837 vs actual 839).

**Repair:** `bar_count_gap` and `bar_count_gap_from_effective` now use
`t["expected_4h"]`; `target_actual_4h` is still recorded per symbol for
reference. The stale docstring line claiming the rebuilt cache "starts
2024-09-30" (false; it starts 2023-10-31) was corrected. Frozen-rule basis
(B8.3a): rev-6.1 §5B.

### 3. Pre-run hash lock not evidenced
Mike: "the Stage C hashes are post-run and don't contain the full
rebuild-code/spec/docs lock required by B8/§15."

Confirmed. Run 1's `artifact_hashes.json` hashes outputs after the fact.
B8.1 requires the frozen spec, the six docs, all rebuild code, and the
cache manifest hash-locked BEFORE the run and recorded in the run log.

**Repair:** `run2_prelock.json` (this directory) is the B8 pre-rerun hash
lock for Run 2: SHA-256 of the rev-6.1 spec, the six docs, the repaired
rebuild code, the whitelisted check target, and the Stage B input —
recorded before any rerun byte is fetched. (The Run 2 cache manifest
cannot be hashed before it exists; it will be hashed immediately after
Run 2's fetch, and both manifests retained per B8.3c.)

## Handoff-number correction (my error, owned)

In my Stage C handoff I reported "132,247 bars" and "662 early closes."
Both were wrong. The committed artifacts say **189,235 total 4H bars**
(`build_4h_summary.json`) and **912/912 early-close symbol-sessions**
(`STAGE_C_REPORT.md`). I recited those numbers from memory instead of
reading the artifacts I had just built — "132,247" doesn't even appear as
a bar count anywhere in the build (only as a volume figure inside raw 1H
CSVs). The dataset was right; my handoff was not. Corrected process going
forward: every number I report comes from a read artifact, cited.

## What happens next (Mike's call)

1. Mike reviews this patch (the two repaired scripts, `run2_prelock.json`,
   this note).
2. Only on his explicit approval: execute Run 2 with the repaired scripts
   verbatim, then the repaired comparator, then report Run 1 vs Run 2.
3. Both runs' outputs are retained and reported (B8.3c). No semantic
   changes: the repairs restore frozen-rule compliance (§11, §5B); nothing
   was adjusted to force a pass (B8.4).

---

## Round 2 — amended patch (ChatGPT review of 265354d; verdict HOLD, two redlines)

Reviewer: ChatGPT (B8.3(b) independent reviewer). Final decision-maker: Mike.
(Correction of my round-1 wording, which wrongly named Mike the B8.3(b)
reviewer.)

### R1 — §5B comparator: effective-window comparison is now the primary gate
Finding: swapping actual_4h→expected_4h fixed the field source, but the
primary/aggregate gap still used total raw cache bars. For admitted new
listings this is structurally wrong (BMNR: expected 592, from-effective
592, total 651 — the old aggregate reported a −59 "miss" on an exact
symbol).

Repair in compare_4h.py:
- `bar_count_gap` (primary, the only aggregated gap) =
  expected_4h − rebuilt_n_4h_from_effective. Total raw cache count is kept
  per symbol as `bar_count_gap_total_raw`, informational only, never
  aggregated.
- Every nonzero primary gap gets an explicit mechanical classification:
  exact / allowed_start_shift / frozen_yahoo_gap_day_effect /
  ticker_specific_availability / unclassified_finding. The classifier checks
  the identity rebuilt_from_effective == target_actual_4h − shift_bars + delta
  (shift_bars from the SPY daily session calendar, 2/day, 1 on half days).
  Anything not mechanically explained is unclassified_finding, and any
  unclassified finding stops the stage (nonzero exit after writing evidence).
- Validated against Run-1 data in a scratch dir (Run-1 artifacts untouched):
  131 compared → 51 allowed_start_shift, 68 frozen_yahoo_gap_day_effect,
  4 exact, 8 ticker_specific_availability, 0 unclassified. BMNR/ARM now read
  exact / +6 allowed shift instead of −59 / −53.

### R2 — Run 2 isolated on disk
Finding: all three scripts still read/wrote Run-1 paths, and build_4h.py
loads both p730 and pmax tags — a symbol changing fetch shape on Run 2
could merge stale Run-1 bytes with fresh Run-2 bytes.

Repair:
- fetch_4h.py, build_4h.py, compare_4h.py all accept --run-dir
  (or CANONICAL_RUN_DIR). Default = canonical_stage_c (Run-1 layout,
  byte-for-byte reproducible). Run 2 MUST use
  --run-dir canonical_stage_c/run2 → run2/raw_1h, run2/data_4h,
  run2/fetch_4h_manifest.json, run2/build_4h_summary.json,
  run2/stage_c_comparison.json.
- fetch_4h.py refuses (exit 1) to fetch into a raw_1h dir that already
  contains files — code-controlled proof against stale-tag mixing.
- New runbook helper hash_run_inputs.py: after a run's fetch and BEFORE
  build/compare, it hash-locks the fetch manifest plus every raw 1H file
  (per-file SHA-256 + combined inputs_digest) into <run>/run_input_lock.json.
  This is the B8 cache-manifest freeze for the downstream Stage-C steps.

### Run-2 runbook (executes only after Mike authorizes the rerun)
1. python3 fetch_4h.py --run-dir canonical_stage_c/run2
2. python3 hash_run_inputs.py --run-dir canonical_stage_c/run2   (B8 freeze)
3. python3 build_4h.py --run-dir canonical_stage_c/run2
4. python3 compare_4h.py --run-dir canonical_stage_c/run2
5. Report Run 1 vs Run 2, both retained (B8.3c).

No strategy rules changed. No rerun executed in this patch.

## Round 3 — no auto-pass on data drift (ChatGPT re-review, 2026-09-30)

ChatGPT re-reviewed 9e7622c and issued HOLD on one narrow point: the
comparator still auto-passed some Yahoo/data-drift discrepancies via the
hardcoded ticker list or the admitted-listing ±1 rule, which rev-6.1
forbids. Only exact, legitimate ±5td start shifts, and already-frozen
Yahoo missing-bar accounting may pass.

Change (compare_4h.py only): the classifier now passes a symbol only when
its rebuilt inventory matches the target's actual exactly (delta == 0,
shift within tolerance) in one of the three frozen categories. Any
inventory drift (delta != 0) or out-of-tolerance shift is a finding that
stops the stage: data_drifted when a documented cause exists (explanation
notes are documentation only and never confer a pass), unclassified_finding
otherwise.

Scratch validation on Run-1 data (Run 1 untouched): 51 allowed_start_shift,
69 frozen_yahoo_gap_day_effect, 2 exact, 9 data_drifted
(CRWV/DRAM/GEV/GLXY/RDDT/SNDK/SPCX/TEM/TLT), 0 unclassified -- exit 1 STOP
as designed. TMO passes via frozen accounting (delta 0, no list needed).

Prelock refreshed: compare_4h.py hash d955526281e924c3... ->
b05eb92632911815...; nothing else changed.
