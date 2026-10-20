# I/O SCHEMA RECORD — the future 51-symbol validation dataset

Scope guard (spec §4): the 51-request FRESH manifest
(`TD-ACQUISITION-MANIFEST-V2-FRESH-20261016`, digest `71aade8b…`) covers
**20 symbols** — it is a vendor screen, NOT this dataset. The baseline
below is UX51 (51 symbols); its acquisition manifest has not been
specified or run, and no TD data has been acquired (1 credit spent to
date, -18 account check only).

## Construction INPUT (per symbol) — what the cleared path accepts

Source: pilot_build.py + validate_input.py (V1–V11) + construct_4h.py.

- Form: CSV (timestamp index) or DataFrame of vendor 1H bars.
- Index: tz-aware timestamps; America/New_York after the declared vendor
  timezone policy. Tz-naive input is REFUSED unless an explicit
  `--assume-tz` policy is declared and recorded (pilot_build.py:102–110;
  construct_4h.py:100–104). No silent localization anywhere.
- Columns (case-insensitive): `open, high, low, close, volume` required,
  finite, High ≥ max(Open,Close), Low ≤ min(Open,Close), Volume ≥ 0
  (V10). Optional documented `interval_end` column; if supplied, every
  end must equal the expected boundary (next grid start, else session
  close) — mismatch = FAIL (V9); if absent, the vendor contract scope
  stays UNKNOWN, never defaulted.
- Window discipline: a declared request window [window_start, window_end]
  (session dates); every expected session is enumerated — open day with
  due constituents missing = FAIL (V8b/V6), closed day with bars = FAIL
  (V4), bars outside the window = FAIL (V8), duplicates/non-monotonic =
  FAIL (V2), any bar start or end after the mandatory tz-aware `as_of` =
  FAIL (V11).
- Adjustment provenance: bars must arrive under the manifest's declared
  convention (`adjust=splits` on the FRESH line) WITH the Amendment v1 S1
  per-symbol split table, else the symbol is DATA_UNQUALIFIED. The
  constructor does not adjust; provenance is a dataset-level record.

## Construction OUTPUT (per symbol) — what the validation stack consumes

- 4H bars: tz-aware America/New_York DatetimeIndex whose values are
  EXACTLY the session anchors — 09:30 on every session, plus 13:30 on
  regular-close sessions; an early-close (13:00) session contributes
  exactly ONE row (09:30). This is a hard downstream contract:
  fold_materializer_v3 checks supplied bar timestamps against
  ANCHOR_TIMES ("09:30","13:30") and the artifact's per-session anchors,
  and requires EVERY scheduled session in [2024-09-16, coverage_end] to
  be present (COVERAGE_PREFIX/INTERIOR/SUFFIX_MISSING, OVERSHOOT).
- Columns: Open, High, Low, Close, Volume (agg first/max/min/last/sum);
  completed bins only (bin close ≤ as_of at construction time).
- Warm-up: ≥215 bars immediately before 2024-09-16 per symbol (frozen
  -21 contract field), constructed under the same semantics; their
  calendar source cannot be the V2 artifact (outside its coverage — see
  ARTIFACT_MAP).
- Split handling at dataset assembly: Amendment v1 S2 excludes bars AND
  candidate entries D−1…D+1 around each split's effective session D; S3
  recomputes all indicators after exclusion, no imputation. (Placement of
  S2 in the pipeline is decision D3 in the memo; neither constructor
  performs it.)
- The fold materializer itself consumes ONLY the bar timestamps
  (`YYYY-MM-DDTHH:MM`, America/New_York local) + the pinned artifact —
  produced and committed before any OHLC/outcome field reaches downstream
  computation (PREREGISTRATION.md:24, sha256 `ccf1a988…`).

## Route-by-route output match

- Cleared TD path (pilot_build/construct_4h): output shape MATCHES the
  consumption contract on every point above (anchors, early-close single
  row, completed-bins-only, OHLCV set). Open items are governance-only:
  file/env pins, precedence, artifact divergence, S2 placement.
- fetch_4h.resample_4h: output shape matches ONLY on well-formed input;
  it cannot guarantee session completeness, closed-day purity, or
  completed-bins-only — the materializer would (correctly) fail such a
  dataset with COVERAGE_* codes rather than consume it silently.
- Both constructors emit bars only; symbol identity, adjustment
  provenance, and the S1 split table travel as dataset-level sidecar
  records, not bar columns — any future dataset package must pin them
  alongside (hashes in INSPECTED_FILES.md are the current pin set).
