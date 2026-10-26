# Tier 3 Mechanical Symbol-Selection Rule — FROZEN v1.0

**Status:** Frozen 2026-10-26, before any list generation and before any price
outcomes were viewed for any candidate symbol.
**Authority:** Preregistration v0.3 §2 (Tier 3 definition; firewall rule 4 —
"Muse sets the liquidity cutoff and list source"), §15 open item O7,
freeze-blocker checklist item C5. Adopted universe decision: B1 REDUCED
(Mike + ChatGPT, 2026-10-26) — holdout universe = 19 defect-free Tier 2 names
+ Tier 3 additions, subject to a Clean §9 audit and the §6 ≥20-symbol
validity floor.
**Tier 3 definition (v0.3 §2, unchanged):** new symbols chosen by a
pre-declared mechanical rule, never in any prior study. Confirmatory on the
holdout window; supplementary on the DEV window.

---

## 1. Sources (dated, archived, hashed)

| # | Source | Role | Date |
|---|---|---|---|
| S1 | NASDAQ Trader symbol directory `nasdaqlisted.txt` (nasdaqtrader.com/dynamic/symdir/) | Listing universe — NASDAQ-listed | File Creation Time 2026-10-26 15:41 ET |
| S2 | NASDAQ Trader symbol directory `otherlisted.txt` (same directory) | Listing universe — other exchanges | File Creation Time 2026-10-26 15:41 ET |
| S3 | NASDAQ screener export `nasdaq_screener_raw.json` (api.nasdaq.com/api/screener/stocks) | IPO year per symbol (listing metadata only) | Retrieved 2026-10-26 |
| S4 | Yahoo Finance daily bars, 2026-09-01 → 2026-10-25 (completed sessions only) | Current liquidity metadata (ADV20, last close) for candidate symbols only — never UX51/X2 names, never any 2023-10-19 → 2024-09-15 data | Retrieved 2026-10-26 |

Raw copies of S1–S3 are archived in `sources/` beside this document; their
SHA-256 hashes are recorded in `REPRODUCIBILITY_RECORD.md`. S4 is used only
through the aggregates the script emits (ADV20, last close, bar count); no
candidate price series is stored, and no return or outcome of any kind is
computed for any symbol.

## 2. Eligibility — applied in this exact order

A symbol is eligible only if it passes every step.

1. **Listed:** present in S1 or S2 (if in both, the S1 row governs).
2. **Exchange:** NASDAQ (any market category in S1), NYSE (S2 Exchange = `N`),
   or NYSE American (S2 Exchange = `A`). All other exchange codes excluded.
3. **Real security, not a test issue:** Test Issue = `N`; ETF flag = `N`;
   NextShares flag = `N` (S1).
4. **Common stock only** — the Security Name must NOT match any of these
   case-insensitive patterns: `%`; `\bPreferred\b`; `\bPreference\b`;
   `\bUnits?\b`; `\bRights?\b`; `\bWarrants?\b`; `\bNotes?\b`.
   (Depositary shares representing ordinary shares are eligible; depositary
   *preferred* shares are caught by the Preferred pattern.)
5. **Plain ticker:** symbol matches `^[A-Z]{1,6}$` (letters only — no class
   slashes, dots, or special codes; avoids symbol-mapping ambiguity in later
   captures).
6. **Never in any prior study:** symbol is not in the frozen 250-name
   forward pool = UX51 (51) ∪ FROZEN X2 cohort (199), exported from
   `hybrid_exit_test.py` (`UNIVERSE_X`) and `v54_universe_x2.py`
   (`UNIVERSE_X2`) in the scanner repo and archived as
   `exclusion_universes.json` (hash in the reproducibility record). This pool
   contains every prior-study universe on record.
7. **Listed before the holdout window:** IPO year in S3 ≤ 2023 and present
   (missing IPO year = ineligible). Year granularity is a disclosed
   limitation: downstream capture qualification (§9-style defect census)
   verifies actual bar coverage in the window; selection asserts listed
   status only, from metadata.
8. **Liquidity (Muse's cutoff, set here per §2 rule 4):** from S4, using the
   20 most recent completed sessions strictly before 2026-10-26:
   - at least 20 valid bars (Volume > 0) in the fetched window, and
   - **ADV20 = mean(Close × Volume) ≥ $25,000,000**, and
   - last close in the window ≥ $5.00.
   A symbol whose bars cannot be fetched is ineligible (fail-closed) and is
   counted in the stage log.

## 3. Ranking, tie-breaking, list size

- Rank eligible symbols by **ADV20 descending**; ties broken by **symbol
  ascending** (byte order). No other ranking input exists.
- **Frozen list size: top 12.**
- Resulting holdout universe if all 12 later pass capture qualification:
  19 + 12 = **31 symbols** vs the ≥20 floor. Headroom arithmetic: at the
  UX43-in-window defect experience (25 of 44 names defective), ~5 of 12
  additions would survive the defect census → 19 + 5 = 24 ≥ 20. The list is
  not extended if names later fail qualification — any shortfall is a
  reported outcome, not a reason to re-run selection.

## 4. Procedure (exact)

1. Archive S1–S3 raw; record SHA-256 of each.
2. Run `generate_tier3_list.py` (hash recorded). It applies §2 in order,
   logs the survivor count after every step, fetches S4 only for symbols
   surviving step 7, and writes `tier3_list.json`.
3. Re-run the script unchanged on the same archived sources. The two
   `tier3_list.json` outputs must be byte-identical; both SHA-256 values
   are recorded in `REPRODUCIBILITY_RECORD.md`.

## 5. What this rule never does

- No returns, forward returns, performance, or signal computations on any
  symbol, candidate or otherwise.
- No data from the sealed holdout window (2023-10-19 → 2024-09-15) for any
  symbol. The only historical fact used is IPO year (listing metadata).
- No hand edits: a name enters or leaves the list only by re-running the
  frozen script on archived sources. Any change to sources, cutoffs,
  patterns, or list size is a new rule version, re-frozen before use and
  logged in the preregistration changelog.

## 6. Known limitations (disclosed, not hidden)

- Survivorship: selection uses the 2026-10-26 listing universe; names
  delisted before that date cannot be selected. Inherited from the standing
  program disclosure, unchanged.
- IPO year is year-granular (step 7); bar-level coverage is a later,
  separate qualification step — exactly as the 19 Tier 2 names were
  qualified by defect census, not by selection.
- ADV20 is a 20-session snapshot of current liquidity, used only as an
  eligibility/ranking gauge; it asserts nothing about holdout-window
  liquidity or about any symbol's returns.
