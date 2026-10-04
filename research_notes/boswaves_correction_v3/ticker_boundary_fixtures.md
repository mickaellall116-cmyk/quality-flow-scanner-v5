# Ticker-Boundary Fixtures (preserved per 2026-10-03 review)

Hand-verified by Claude (source review): every segment boundary checked for gaps
and overlaps; every date in the 2009-01-02 → 2026-09-30 sample window resolves to
exactly one ticker per security. Re-verified by builder unit tests below.

## Rename histories (effective dates verified against exchange/company sources)

| Security | Ticker | From | To |
|----------|--------|------|----|
| Capri Holdings | KORS | data start | 2019-01-01 |
| Capri Holdings | CPRI | 2019-01-02 | present |
| Baker Hughes | BHGE | data start | 2019-10-17 |
| Baker Hughes | BKR | 2019-10-18 | present |
| Jacobs Solutions | JEC | data start | 2019-12-09 |
| Jacobs Solutions | J | 2019-12-10 | present |
| Corpay | FLT | data start | 2024-03-24 |
| Corpay | CPAY | 2024-03-25 | present |
| Fiserv | FISV | data start | 2023-06-06 |
| Fiserv | FI | 2023-06-07 | 2025-11-10 |
| Fiserv | FISV | 2025-11-11 | present |

## Reconciliation

- Universe: 831 ticker strings. Fiserv contributes 2 distinct strings ("FISV",
  "FI"); the third timeline segment reuses the "FISV" string. 826 securities +
  5 collapsed pairs = 831. ✓
- FISV.json vs FI.json: byte-identical content, 4,463 bars each, 2009-01-02 →
  2026-09-30, 100% identical closes. Direction never affected P&L; history
  recorded for label correctness.

## Builder unit-test evidence (2026-10-03)

- ticker_at(): FISV@2020, FI@2024, FISV@2026; KORS@2014-01-28, CPRI@2020;
  BHGE@2019-08-01, BKR@2020; JEC@2019-01-01; CPAY@2025 — all pass.
- Exact mom_score ties (the expected case for duplicate files): winner identical
  across all input permutations (stable tie-break: lexicographically smallest
  raw ticker); admitted label always date-appropriate.
