# Parity matrix + independent review matrix — XNYS_SESSION_SCHEDULE_V2 generation

Task: `QF-XNYS-SCHEDULE-GENERATION-CONTRACT-20261019-34 r1` (prep only —
this matrix is executed by the FUTURE authorized generation run and its
independent review, not by -34).

**Qualification rule (binding, from -30):** the generated artifact
qualifies ONLY by date-by-date parity against the primary record below
plus the pinned counts. Agreement between the two libraries (paths A/C)
is a correlated consistency check and appears only as review row R5 —
it can never substitute for any row in §§1–4. **Any row FAIL, any missing
field, any disagreement = HOLD. No partial credit, no pinned artifact.**

Source key: S1 = SEC 34-103356 (`5f0263f7…`); S2 = NYSE RM-24-12
(`305fab2e…`); S3 = ICE release Nov 10, 2023 (`564de593…`); S4 = ICE
release Nov 8, 2024 (`3b8a67d9…`); S5 = Carter notice Dec 30, 2024
(`e1cd4c1a…`); S6 = NYSE hours page capture (`79602f7b…`); S7 =
Trading_Days current (`f90b6d08…`); S8 = Trading_Days Dec-2024 vintage
(`dd349170…`); S9 = Trading_Days Nov-2025 vintage (`414d2ed3…`).

## 1. Core hours (2 rows)

| Row | Primary fact | Artifact check |
|---|---|---|
| HRS-01 | Regular open 09:30 ET on every session — Rule 1.1(d) quoted verbatim in S1 fn 42 ("9:30 a.m. Eastern Time through 4:00 p.m. Eastern Time"); S6 states the same for 2026 | EVERY session in the artifact has `open` = `09:30` |
| HRS-02 | Regular close 16:00 ET — S1 (rule text, mid-block) + S2 (operative 4 p.m. end at block start, rules "applicable every day") | EVERY session has `close` = `16:00`, EXCEPT the 5 dates in §3 whose close must be `13:00`; no other close value exists |

## 2. Dated full-day closures — artifact must contain NO session on the date (21 rows)

2024 segment (source S3):

| Row | Date | Fact |
|---|---|---|
| CLO-01 | 2024-11-28 | Thanksgiving Day |
| CLO-02 | 2024-12-25 | Christmas Day |

(The remaining eight 2024 closures in S3 fall before 2024-09-16 and are
out of the artifact interval; they bind only through CNT-2024, §4.)

2025 (sources S3 + S4, columns in exact agreement; Carter row = S5, tier-1 notice):

| Row | Date | Fact |
|---|---|---|
| CLO-03 | 2025-01-01 | New Year's Day |
| CLO-04 | 2025-01-09 | **Exceptional closure — National Day of Mourning (Carter)**, S5 |
| CLO-05 | 2025-01-20 | Martin Luther King, Jr. Day |
| CLO-06 | 2025-02-17 | Washington's Birthday |
| CLO-07 | 2025-04-18 | Good Friday |
| CLO-08 | 2025-05-26 | Memorial Day |
| CLO-09 | 2025-06-19 | Juneteenth National Independence Day |
| CLO-10 | 2025-07-04 | Independence Day |
| CLO-11 | 2025-09-01 | Labor Day |
| CLO-12 | 2025-11-27 | Thanksgiving Day |
| CLO-13 | 2025-12-25 | Christmas Day |

2026 segment, in-interval (source S6; corroborated by the 2026 columns of S3 + S4):

| Row | Date | Fact |
|---|---|---|
| CLO-14 | 2026-01-01 | New Year's Day |
| CLO-15 | 2026-01-19 | Martin Luther King, Jr. Day |
| CLO-16 | 2026-02-16 | Washington's Birthday |
| CLO-17 | 2026-04-03 | Good Friday |
| CLO-18 | 2026-05-25 | Memorial Day |
| CLO-19 | 2026-06-19 | Juneteenth National Independence Day |
| CLO-20 | 2026-07-03 | Independence Day (observed; Jul 4 = Saturday) — a CLOSURE, not an early close |
| CLO-21 | 2026-09-07 | Labor Day |

Boundary rows (post-interval source facts — S6 lists them for full-year
2026; they must NOT leak into the artifact):

| Row | Check |
|---|---|
| CLO-22 | Artifact contains NO session dated after 2026-10-16 (the S6 closures 2026-11-26 and 2026-12-25 are outside `coverage_end` and out of scope) |

## 3. Dated 13:00 ET early closes — artifact session must exist with close `13:00` (5 rows + 1 negative)

| Row | Date | Source |
|---|---|---|
| EC-01 | 2024-11-29 | S3 (day after Thanksgiving) |
| EC-02 | 2024-12-24 | S3 (Christmas Eve) |
| EC-03 | 2025-07-03 | S3 + S4 |
| EC-04 | 2025-11-28 | S3 + S4 |
| EC-05 | 2025-12-24 | S3 + S4 |
| EC-06 | Negative assertion: NO other artifact session has close `13:00`; in particular the 2026 segment contains ZERO early closes (S6's two 2026 early closes, 2026-11-27 and 2026-12-24, fall after `coverage_end`) | S6 |

## 4. Session counts (3 rows)

| Row | Check | Sources |
|---|---|---|
| CNT-2024 | Auxiliary full-calendar-2024 emission = **252** sessions (the artifact interval covers only Sep 16–Dec 31, 2024; the full-year count binds the libraries' complete 2024 behaviour, including the 8 pre-interval closures) | S8 |
| CNT-2025 | Artifact sessions in calendar 2025 = **250** (2025 lies fully inside the interval; reconciles 261 weekdays − 11 closures incl. CLO-04) | S9 (final vintage); S8's 251 is the pre-notice vintage — see COR-02 |
| CNT-2026 | Auxiliary full-calendar-2026 emission = **251** sessions (the interval ends 2026-10-16; the full-year count binds the post-interval behaviour incl. the Nov/Dec closures and early closes) | S7; corroborated by S8 (2026 = 251) |

## 5. Master date sweep (1 row)

| Row | Check |
|---|---|
| MST-01 | For EVERY calendar date in the closed interval [2024-09-16, 2026-10-16]: (a) Mon–Fri and not a §2 closure date ⇒ a session exists with the §1/§3 times; (b) Sat/Sun or a §2 closure date ⇒ no session exists. This sweep is the date-by-date completeness proof; §§2–3 enumerate its exceptions so a sweep implementation cannot silently share a defect with the emissions |

## 6. Structural / schema assertions (4 rows)

| Row | Check |
|---|---|
| STR-01 | Artifact parses under `fold_materializer_v3.py` (`e1b0dfed…`) header rules: `artifact` = `XNYS_SESSION_SCHEDULE_V2`, non-empty `source`/`version`, `exchange` = `XNYS`, `timezone` = `America/New_York`, `coverage_start` = `2024-09-16`, `coverage_end` = `2026-10-16` |
| STR-02 | Sessions strictly ascending by date, unique, non-empty; first session = first session on/after 2024-09-16; last session = 2026-10-16 (a Friday session date) |
| STR-03 | Canonical serialization per contract §4 (UTF-8, sorted keys, compact separators, one trailing newline); SHA-256 recorded in the receipt before any consumer use |
| STR-04 | No session on a Saturday/Sunday; every `close` > `open`; every `close` after `09:30` (Amendment v3 anchor admissibility) |

## 7. Independent review matrix (8 rows — performed by the reviewer, not the generator)

| Row | Review check |
|---|---|
| R1 | **Source hash verification:** recompute SHA-256 of all 9 primary artifacts; each must equal `SOURCE_SET_MANIFEST.json`. Any mismatch = HOLD |
| R2 | **Zero-network execution proof:** install used `--no-index --require-hashes --find-links` against the pinned wheelhouse inside a no-network context; receipt §2 records the enforcement mechanism and zero attempted accesses |
| R3 | **PMC key pin:** generation code + logs show path A invoked with key `NYSE` ONLY; the mirror module (`calendars/mirror.py`) never imported for emission. Any `XNYS` key inside pandas_market_calendars = run invalid |
| R4 | **EC key pin:** path C invoked directly with key `XNYS` on exchange_calendars (not via any PMC wrapper) |
| R5 | **Consistency log:** emission A vs emission C compared session-for-session; result recorded as CORRELATED CONSISTENCY ONLY (common-ancestor classification, -30). Agreement never substitutes for §§1–5; disagreement = HOLD |
| R6 | **Determinism:** the full dual emission repeated; artifact bytes identical across repetitions |
| R7 | **Consumer synthetic:** the frozen -28 fixture expectations for `fold_materializer_v3.py` still pass with the consumer byte-unmodified |
| R8 | **Consumer real-artifact parse:** the generated artifact parsed by the consumer using SYNTHETIC timestamps spanning the interval (no market data): no `SCHEDULE_*` error; reported coverage first/last sessions equal the artifact's first/last sessions |

## 8. Corroboration / reconciliation rows (2 rows)

| Row | Check |
|---|---|
| COR-01 | The 2025 columns of S3 and S4 agree exactly (established in -32). The artifact must be consistent with BOTH; disagreement with either = HOLD |
| COR-02 | Count-vintage reconciliation: S8 states 2025 = 251, S9 states 250. Resolved by the contract priority rule (S5 tier-1 notice, dated Dec 30, 2024, postdates S8's vintage and accounts for exactly one January session). CNT-2025 therefore binds at **250**. Any NEW count source contradicting 250 without a dated priority-resolving notice = HOLD |

## Coverage summary

- Primary facts bound: **21** in-interval dated closures (+1 boundary row),
  **5** dated 13:00 early closes (+1 negative assertion), **2** core-hours
  rows, **3** count checks, **1** master date sweep over all **761**
  calendar days of the interval, **4** structural rows, **8** independent
  review rows, **2** corroboration rows — **47 rows total**, every one
  fail-closed.
