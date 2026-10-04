# Data Inventory — TOP-vs-BROAD (2026-10-04)

**Scope:** non-performance inventory only. No signals, indicators, or returns computed. No sealed-4H reads.

- Universe: 225 US stocks (250-name pool minus 25 crypto pairs).
- Source: Yahoo Finance 1H, `prepost=False`, `auto_adjust=False` (raw OHLCV), `actions=True`.
- Download window: 2024-10-07 → 2026-09-15. NOTE: 2024-10-01 was requested but Yahoo rejects
  1H ranges starting more than 730 days back (verified error 2026-10-04); 2024-10-07 is the earliest feasible start.
- Consolidated study window: 2025-03-10 → 2026-09-14. Warmup contract: ≥215 4H bars before study start.
- 4H bars built with the corrected session-anchored resampler
  (`scanner_rules.resample_closed_4h_session_anchored`), used ONLY to count bars — no signal use.

## KEY FINDING: warmup vs the 2025-03-10 start

Yahoo's 730-day 1H boundary (earliest start 2024-10-07) supplies only ~210-211 4H bars
before 2025-03-10 for continuously-listed symbols — BELOW the 215-bar contract.
A 2025-03-17 study start supplies 216 bars and satisfies the contract.
Both cutoffs are audited per symbol below (columns warmup_4h_mar10 / warmup_4h_mar17).

## Summary counts

- Total stocks: 225
- Successful 1H downloads: 225
- Failed downloads: 0
- Warmup ≥215 4H bars before 2025-03-17 (PASS): 218
- Warmup ≥215 4H bars before 2025-03-10 (PASS): 0
- Resampler errors: 0
- Symbols with splits in window: 15
- Late listers (first 1H bar after 2024-10-15): 5

## Warmup failures vs 2025-03-17 (reasons)

- BMNR: late lister (first 1H 2025-06-05 10:30 EDT); only 0 4H bars before 2025-03-17
- CLSK: only 214 4H bars before 2025-03-17
- CRWV: late lister (first 1H 2025-03-28 12:30 EDT); only 0 4H bars before 2025-03-17
- GLXY: late lister (first 1H 2025-05-16 09:30 EDT); only 0 4H bars before 2025-03-17
- NBIS: late lister (first 1H 2024-10-21 09:30 EDT); only 196 4H bars before 2025-03-17
- SBET: only 212 4H bars before 2025-03-17
- XYZ: late lister (first 1H 2025-01-21 09:30 EST); only 76 4H bars before 2025-03-17

Near-miss detail (verified against XNYS calendar):
- CLSK (214 bars): exactly one trading day missing from Yahoo 1H — 2024-11-08 (vendor gap, not a halt).
- SBET (212 bars): no missing trading days; 4 bars short from partial sessions; also a 1:12 reverse split in window (0.0833).

## Warmup vs 2025-03-10 (consolidated start)

Symbols reaching ≥215 bars before 2025-03-10: 0/225.
Continuously-listed symbols show 210-211 bars — the 730-day boundary makes the 215-bar
contract unreachable at a 2025-03-10 start for any symbol without pre-Oct-2024 cached 1H.
Symbols failing at Mar-10 but passing at Mar-17 are marked accordingly in the table.

## Splits in window (reported, not adjusted)

Raw (unadjusted) prices are used for the contemporaneous dollar-volume ranking input.
Any split in the ranking lookback would distort raw price × volume; these are flagged for
the implementation to handle before the run (e.g., split-aware raw series).
Clean integer ratios are likely real splits; fractional values are Yahoo artifacts or
special distributions — verify before use.

- ANET: split factor sum 4.0 in window — likely real
- BKNG: split factor sum 25.0 in window — VERIFY (non-standard)
- CRWD: split factor sum 4.0 in window — likely real
- FDX: split factor sum 1.241 in window — VERIFY (non-standard)
- HON: split factor sum 2.0145 in window — VERIFY (non-standard)
- KLAC: split factor sum 10.0 in window — likely real
- LCID: split factor sum 0.1 in window — VERIFY (non-standard)
- NFLX: split factor sum 10.0 in window — likely real
- NOW: split factor sum 5.0 in window — likely real
- PANW: split factor sum 2.0 in window — likely real
- PPLT: split factor sum 10.0 in window — likely real
- SBET: split factor sum 0.0833 in window — VERIFY (non-standard)
- WDC: split factor sum 1.323 in window — VERIFY (non-standard)
- XLE: split factor sum 2.0 in window — likely real
- XLK: split factor sum 2.0 in window — likely real

## Per-symbol table

warmup_4h_mar10 = 4H bars before 2025-03-10 (consolidated start); warmup_4h_mar17 = 4H bars before 2025-03-17.

| symbol | first_1h | last_1h | rows_1h | trading_days | warmup_4h_mar10 | warmup_4h_mar17 | pass_215_mar17 | splits | notes |
|---|---|---|---|---|---|---|---|---|---|
| AAPL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ABBV | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ABNB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ADBE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| AFRM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| AI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ALB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| AMAT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| AMC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| AMD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| AMGN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| AMT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| AMZN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ANET | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 4.0 | passes only at Mar-17 start |
| APLD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| APP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ARKK | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ARM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ASML | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ASTS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| AVGO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| BA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| BAC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| BBAI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| BIIB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| BKNG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3372 | 485 | 206 | 216 | PASS | 25.0 | 8 div payments; passes only at Mar-17 start |
| BKR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| BMNR | 2025-06-05 10:30 EDT | 2026-09-14 15:30 EDT | 2226 | 320 | 0 | 0 | FAIL | 0.0 | late lister; 1 div payments |
| BP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| BRK-B | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CAT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| CCJ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 2 div payments; passes only at Mar-17 start |
| CDNS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CEG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| CIEN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CIFR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CLS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CLSK | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3359 | 484 | 204 | 214 | FAIL | 0.0 |  |
| CMG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| COHR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| COIN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| COP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| CORZ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| COST | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| CPER | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3364 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CRM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| CRSP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| CRWD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 4.0 | passes only at Mar-17 start |
| CRWV | 2025-03-28 12:30 EDT | 2026-09-14 15:30 EDT | 2545 | 367 | 0 | 0 | FAIL | 0.0 | late lister |
| CSCO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| CVX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| DAL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| DASH | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| DDOG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| DE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| DELL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| DHR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| DIA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 23 div payments; passes only at Mar-17 start |
| DIS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 4 div payments; passes only at Mar-17 start |
| DJT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| DKNG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| DLR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| DOCU | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| DVN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| EBAY | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ENPH | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| EOG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| EPD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| EQIX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| EQT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ET | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| EXPE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| F | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| FANG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| FCX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| FDX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 1.241 | 8 div payments; passes only at Mar-17 start |
| FIS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| FSLR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| FTNT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| GD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| GE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| GEV | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| GILD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| GLD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| GLXY | 2025-05-16 09:30 EDT | 2026-09-14 15:30 EDT | 2319 | 333 | 0 | 0 | FAIL | 0.0 | late lister |
| GM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| GME | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| GOOGL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| GPN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| GS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| HAL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| HD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| HON | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 2.0145 | 8 div payments; passes only at Mar-17 start |
| HOOD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| HPE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| HUBS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| HUT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| IBM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| ILMN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| INTC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| INTU | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| IONQ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ISRG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| IWM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| JBL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| JNJ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| JPM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| KLAC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 10.0 | 8 div payments; passes only at Mar-17 start |
| KMI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| KO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| LCID | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.1 | passes only at Mar-17 start |
| LIN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| LITE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| LLY | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| LMT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| LRCX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| LUNR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| LYFT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| MA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MARA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| MCD | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MDB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| MELI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| META | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| MPC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MRNA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| MRVL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MSFT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| MSTR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| MU | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NBIS | 2024-10-21 09:30 EDT | 2026-09-14 15:30 EDT | 3296 | 475 | 186 | 196 | FAIL | 0.0 | late lister |
| NEE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NEM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NET | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| NFLX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 10.0 | passes only at Mar-17 start |
| NIO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| NKE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NOC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NOW | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 5.0 | passes only at Mar-17 start |
| NU | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| NVDA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| NXPI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| OKE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| OKLO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| OKTA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ON | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| OPEN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ORCL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| OXY | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| PANW | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 2.0 | passes only at Mar-17 start |
| PATH | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| PEP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| PFE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| PG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| PLTR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| PPLT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 10.0 | passes only at Mar-17 start |
| PSX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| PYPL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 4 div payments; passes only at Mar-17 start |
| QBTS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| QCOM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| QQQ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| RBLX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| RBRK | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| RDDT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| REGN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3374 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| RGTI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| RIOT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| RKLB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| RTX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| S | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SBET | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3278 | 485 | 202 | 212 | FAIL | 0.0833 |  |
| SBUX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| SCHW | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| SHEL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| SHOP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SLB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| SLV | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SMCI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SMH | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 2 div payments; passes only at Mar-17 start |
| SMR | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SNAP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SNOW | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SNPS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SOFI | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SOUN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| SPY | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| STX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| T | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| TEAM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| TEM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| TLT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 23 div payments; passes only at Mar-17 start |
| TMO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| TSLA | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| TSM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| TTE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 6 div payments; passes only at Mar-17 start |
| TXN | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| UAL | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| UBER | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| UNG | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| UNH | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| UNP | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| UPST | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| USO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| UUUU | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| V | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| VEEV | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| VLO | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| VRT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| VRTX | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| VST | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| VZ | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| WDAY | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| WDC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3375 | 485 | 206 | 216 | PASS | 1.323 | 6 div payments; passes only at Mar-17 start |
| WFC | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| WMB | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| WMT | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| WULF | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| XLE | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 2.0 | 7 div payments; passes only at Mar-17 start |
| XLF | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 7 div payments; passes only at Mar-17 start |
| XLK | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 2.0 | 7 div payments; passes only at Mar-17 start |
| XOM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3365 | 485 | 206 | 216 | PASS | 0.0 | 8 div payments; passes only at Mar-17 start |
| XYZ | 2025-01-21 09:30 EST | 2026-09-14 15:30 EDT | 2876 | 414 | 66 | 76 | FAIL | 0.0 | late lister |
| ZM | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |
| ZS | 2024-10-07 09:30 EDT | 2026-09-14 15:30 EDT | 3366 | 485 | 206 | 216 | PASS | 0.0 | passes only at Mar-17 start |

## Provenance

- Raw 1H pickles: `data_inventory_scratch_20261004/h1_raw/` (225 files, scratch — not the published cache).
- Inventory JSON: `data_inventory_scratch_20261004/inventory_final.json`.
- Stock list: `data_inventory_scratch_20261004/stock_list_225.json`.
- Builder's data-readiness assessment: 218/225 symbols meet the 215-bar warmup at a 2025-03-17
  start; the consolidated 2025-03-10 start cannot satisfy the contract for fresh-download
  symbols (730-day boundary). 7 exclusions needed: 5 late listers (BMNR, CRWV, GLXY, NBIS, XYZ)
  + 2 near-miss vendor gaps (CLSK: 1 missing day; SBET: partial sessions + reverse split).
  15 symbols have splits in the window — split-aware raw series required before the run.
- This report's SHA-256 (computed after writing): see below.
- SHA-256 of this file (excl. this line): `ecb449a0e6d8fea0bec3595ffbfd661b11ce08c36b59f4bf2d736ee5593c1fe7`
