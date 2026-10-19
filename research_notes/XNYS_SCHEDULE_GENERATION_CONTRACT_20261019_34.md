# XNYS schedule generation contract — static prep (-34)

Task: `QF-XNYS-SCHEDULE-GENERATION-CONTRACT-20261019-34 r1`
Spec: GitHub Issue #1 comment `6261572099` — accepts -33 as
`PRIMARY_SOURCE_CALENDAR_RECORD_COMPLETE__GENERATION_NOT_AUTHORIZED` and
dispatches this static-only integration prep (cap ≤ 25 min).
Package: `research_notes/xnys_schedule_generation_contract_20261019_34/`

## Verdict (the required return)

**`PREP_READY__AWAITING_EXPLICIT_GENERATION_GO`**

The generation contract is execution-ready: a future explicit GO needs no
further specification work. Nothing was installed, built, imported,
executed, or generated in this task. No schedule artifact exists. This
contract does not claim the environment was built, a schedule was
generated, or any data became qualified.

## What was bound

**Inputs → outputs, in one chain:**

1. **Primary record (qualification authority)** — -31 capture (commit
   `5d2060b`): live hours page `79602f7b…`; Trading_Days vintages
   `f90b6d08…` / `dd349170…` / `414d2ed3…` (counts 2024 = 252; 2025 = 251
   pre-notice → 250 final; 2026 = 251). -32 recovery (commit `d307439`):
   ICE releases `564de593…` (Nov 10, 2023) and `3b8a67d9…` (Nov 8, 2024)
   pinning every dated 2024/2025 closure and 13:00 early close; Carter
   notice `e1cd4c1a…` (Dec 30, 2024) pinning the exceptional 2025-01-09
   closure. -33 proof (commit `fdf1c34`): SEC 34-103356 `5f0263f7…`
   (Rule 1.1(d): core hours 09:30–16:00 ET) + RM-24-12 `305fab2e…`.
   Priority rule pinned: official event notice > dated calendar release >
   count cross-check; unresolvable contradiction = HOLD.
2. **Environment** — -29 Route A (commit `99b2096`): the 11-wheel closure
   (wheelhouse manifest `210b8273…`; lock file `f5e8440d…`; accepted NL
   freeze `08b38cfa…`; pandas_market_calendars 4.5.1 `7b4f3478…`;
   exchange_calendars 4.13.2 `fc5a2ad0…`; CPython 3.12.3, linux x86_64),
   referenced without modification.
3. **Pinned code paths (-30, commit `29ab49e`)** — Path A:
   pandas_market_calendars keyed to the **native `NYSE`** only (registry
   `f5e70a90…`, class module `135ba9dc…`, rule tables `e85f5edb…`); the
   PMC `XNYS` mirror key (`3aaf6345…`) is FORBIDDEN — it is
   exchange_calendars observed twice. Path C: exchange_calendars keyed
   directly `XNYS` (registry `7d12d534…`, class module `baa39f07…`, rule
   tables `a2444bd7…`). Classification `COMMON_ANCESTOR_BUT_SEPARATE_RULE_TABLES`:
   **library agreement is a logged correlated consistency check, never
   qualification.** (-29's "independent implementations" wording is
   superseded by -30 and flagged as such in the contract.)
4. **Consumer** — `XNYS_SESSION_SCHEDULE_V2` schema exactly as enforced by
   `fold_materializer_v3.py` (`e1b0dfed…`, -28 Amendment v4): `exchange`
   `XNYS`, `timezone` `America/New_York`, `coverage_start` `2024-09-16`,
   **`coverage_end` fixed at `2026-10-16`** (the frozen interval end),
   sessions `{date, open, close}`; canonical serialization fixed
   (UTF-8, sorted keys, compact separators, ascending dates, one trailing
   newline).

## Deliverables (package contents)

- `GENERATION_CONTRACT.md` — bindings (§§1–3), generator contract (§4:
  deterministic inputs, emission rules, schema instance, serialization),
  the **inert execution sequence** (§5: pre-flight hash verification →
  isolated offline `--no-index --require-hashes` install from the pinned
  wheelhouse → freeze acceptance vs `08b38cfa…` → member-pin verification
  → dual emission PMC-native-`NYSE` + EC-`XNYS` → agreement + assembly →
  parity review → consumer synthetic + real-artifact parse → receipt +
  commit/pin), 12 fail-closed conditions (§6), and the exact authority
  statement (§7).
- `SOURCE_SET_MANIFEST.json` — machine-readable enumeration of all 9
  primary artifacts (paths, full SHA-256s, commits, facts), the
  environment binding, the -30 code-path pins, and the consumer binding.
- `RECEIPT_TEMPLATE.md` — the future run's receipt: GO reference, env
  build evidence, commands as executed (verbatim), stdout/stderr hashes,
  source + member verification tables, generator hash, emission counts,
  disagreement log, per-year counts, exception list, artifact SHA-256,
  consumer results, elapsed/repair minutes, verdict line.
- `PARITY_MATRIX.md` — **48 fail-closed rows**: 21 in-interval dated
  closures (+1 boundary row), 5 dated 13:00 early closes (+1 negative
  assertion: zero 2026 in-interval early closes), 2 core-hours rows,
  3 count checks (2024 = 252 auxiliary full-year, 2025 = 250 in-interval,
  2026 = 251 auxiliary full-year), 1 master date-by-date sweep over all
  761 calendar days of [2024-09-16, 2026-10-16], 4 structural rows,
  8 independent-review rows (hash verification, zero-network proof, both
  key pins, consistency-log semantics, determinism, both consumer
  checks), 2 corroboration/reconciliation rows. Any FAIL = HOLD.
  **Row-count identity:** 2 HRS + 22 CLO (21 in interval + 1 boundary)
  + 6 EC (5 dated + 1 negative) + 3 CNT + 1 MST + 4 STR + 8 R + 2 COR
  = **48**.
  *(Correction, -34 r2: r1 stated 47 rows in this memo, the parity
  matrix, and receipt guidance; the enumerated matrix always contained
  48. Totals corrected to 48 with the identity above; no other change.)*

## The GO this contract requires (verbatim from contract §7)

> Generation requires a separate explicit GO: a distinct future task ID
> authorizing (a) isolated environment creation from the pinned wheelhouse
> under this contract, and (b) `XNYS_SESSION_SCHEDULE_V2` generation,
> parity review, and pinning. Until that GO is issued, the state remains
> `PREP_READY__AWAITING_EXPLICIT_GENERATION_GO`.

## Compliance

Static prep only: no installs, no environment builds, no imports or
execution of any candidate or consumer code (the consumer file was READ
to bind its schema — never run), no generator written or run, no schedule
bytes emitted, no market/OHLC data, no network beyond the read-only public
spec fetch and the git push, no credentials, no holdout access, no
production/live/ledger writes, no Issue #9. -29 through -33 preserved
unedited (referenced by hash only).
