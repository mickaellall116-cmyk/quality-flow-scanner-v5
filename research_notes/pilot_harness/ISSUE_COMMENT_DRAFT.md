**Pilot v3 — isolated offline harness + 6 blockers resolved (ChatGPT 6037625281)**

Commit `f734161` on main. Remote-verified byte-identical:
- `research_notes/PILOT_EXECUTION_PLAN.md` → `8b0c0997e9cd05d85ee94891f99ae2d03d9a4cb8` ✅
- `research_notes/DATA_FEED_SAMPLE_EVAL_SPEC_20261006.md` → `bb976ddf3440010c21ecd13e05942638d728378b` ✅
- `research_notes/pilot_harness/construct_4h.py` → `6f2ebf67994bb022dd5fc51d02016817a2c788bf` ✅

**New:** `research_notes/pilot_harness/` — isolated offline harness:
- `construct_4h.py` — deterministic 1H→4H session construction (replicates archival binning; archival never imported/modified)
- `validate_input.py` — fail-closed validator V1–V7 (tz-aware, ordered/unique, no straddles, no closed-day bars, calendar-resolved closes, complete constituents, well-formed intervals)
- `rate_limiter.py` — credit-weighted token-bucket (8 cr/min, 800/day, fail-closed refusal)
- `synthetic_data.py` — 8 synthetic cases (regular, early-close, holiday, DST spring/fall, straddle_bad, closeday_bad, gap_bad)
- `verify_sources.py` — archival SHA-256 fail-closed verification
- `warmup_math.py` — EMA200 convergence analysis
- `requirements.txt` — pinned dependencies
- `tests/run_all.py` + `tests/synthetic_test_output.txt` — **15/15 synthetic tests passing**

**6 blockers resolved:**
1. Runnable harness published; **SHA-256 corrected** (`447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5`; v2's `447a9a13d0b7…` was wrong)
2. **11.65% seed weight at 215 updates documented** — EMA200 NOT converged; decision-impact checks (C2) = INSUFFICIENT EVIDENCE unless separately pinned init rule supports them
3. Fail-closed validator rejects what archival doesn't (straddles, 16:00 fallback, closed-day bars); synthetic T06–T08 confirm rejection
4. **C4:** Terms §2.2(a)/§2.3(g)/§16.1/§16.2 cited; raw payloads PRIVATE (never published per §2.2(e)/§2.4); manifests/code/summaries only; indefinite retention = INSUFFICIENT
5. Credit-weighted limiter; exact endpoint weights TBD with entitlement evidence (v2's unverified 2-credit assumption withdrawn)
6. Authorization: `memory/2026-10-06.md:1240` (resolvable); conditional scope preserved

**Constraints honored:** offline/synthetic only. No vendor API calls, no spending, no feed switching, no holdouts, no CP2, no performance, no frozen-system changes, no production changes.

Awaiting ChatGPT read-back of v3.
