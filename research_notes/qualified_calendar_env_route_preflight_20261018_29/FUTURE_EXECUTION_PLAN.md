# Future execution plan — qualified calendar environment (PLAN ONLY, -29 r1)

Status: proposed for a separately authorized future task. Nothing here was
installed or run in -29. Each step names the gate that must clear first.

## Step 0 — authorization gate
A distinct task ID authorizing (a) isolated environment creation from the
proposed hash-lock, and (b) schedule generation. -29 authorizes neither.

## Step 1 — isolated environment build (offline, hash-pinned)
- Create a fresh venv on CPython 3.12.3 (never the system site-packages;
  the system set — pandas 2.1.4+dfsg, dateutil 2.8.2, pytz 2024.1, no
  calendar packages — is UNQUALIFIED and must not be used or extended).
- Install with `--no-index --require-hashes -r PROPOSED_HASH_LOCK.txt
  --find-links <wheelhouse>/wheels` after re-verifying the wheelhouse
  manifest (sha256 210b8273…) wheel-by-wheel.
- Acceptance: `pip freeze` in the new env is byte-identical to the
  accepted NL lock (sha256 08b38cfa…) — the exact test the 2026-10-16
  rebuild already passed once with these same wheels.

## Step 2 — dual-implementation schedule generation
The closure deliberately contains TWO independent calendar
implementations: `pandas_market_calendars` 4.5.1 (which itself wraps
`exchange_calendars`) and `exchange_calendars` 4.13.2 used directly.
The future generator emits the XNYS session list for the requested
interval TWICE — once via each access path — and the two emissions must
agree session-for-session (date, open, close, early-close flag) before
anything is pinned. Any disagreement = HOLD (qualification gate, below).

## Step 3 — artifact emission in the consumer's form
- Emit exactly one `XNYS_SESSION_SCHEDULE_V2` artifact (the -28 form:
  exchange=XNYS, timezone=America/New_York, coverage_start=2024-09-16,
  coverage_end frozen pre-outcome, per-session date/open/close).
- Record in the generation receipt: generator source hash, environment
  lock hash (08b38cfa…), wheelhouse manifest hash (210b8273…), both
  library versions, the artifact SHA-256, and the dual-emission
  agreement result.
- The artifact is committed and its hash pinned BEFORE any market
  timestamps or OHLC are supplied to the fold materializer.

## Step 4 — qualification gate (independent, pre-registered in -29 memo)
See the memo §Qualification gate. All clauses must pass; disagreement
between the two implementations, or between the artifact and the
independently pinned cross-check, = HOLD with no partial credit.

## Step 5 — consumption (already frozen, no new work)
`fold_materializer_v3.py` (sha256 e1b0dfed…) consumes the pinned
artifact unchanged. Qualified market timestamps are then qualified BY
that consumption: the materializer validates every supplied timestamp
against the pinned schedule (anchors, early closes, coverage span) and
fails closed on any mismatch — no separate timestamp source or second
qualification track is needed.

## What this plan never does
No unpinned `pip install`; no system-environment mutation; no schedule
built from prose; no OHLC or performance input during qualification;
no holdout access (the artifact's coverage starts 2024-09-16, the day
after the sealed holdout ends, by construction of the V2 contract).
