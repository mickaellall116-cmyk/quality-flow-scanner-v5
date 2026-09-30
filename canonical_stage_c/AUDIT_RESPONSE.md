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
