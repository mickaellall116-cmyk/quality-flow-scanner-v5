# QFAR1 Journal Header Authentication — -16 r1 Memo

**Task:** QF-YAHOO-QFAR1-JOURNAL-HEADER-AUTH-20261016-16 r1
**Spec:** GitHub Issue #1 comment 6208610183 (the -15 adjudication)
**Verdict: `QFAR1_JOURNAL_HEADER_AUTH_PASS`** (offline scope only)

## What was wrong (-15, parked at 1778dba)

The -15 frame (header 13 = magic/version/length/complement, tag after the
payload) classified `remaining < header + n + tag` as a torn final frame
*before* the header-covering SHA-256 could be reached. Coherently changing
both `n` and `~n` to a larger in-bound value made an interior frame swallow
the rest of a multi-frame journal and return an empty verified prefix;
recovery would then truncate the later, valid frames. Complement redundancy
does not authenticate that case.

## The -16 fix (candidate `qfar1_publisher_h16.py`, new isolated package)

Frame v2 layout — a fixed 53-byte header, payload, whole-frame digest:

```
header(53) = magic "QFJ2"(4) || version u8(1) || seq u64be(8)
             || length u32be(4) || length complement u32be(4)
             || header digest(32) = SHA-256(header bytes [0:21])
tag(32)    = SHA-256(header || payload)
```

Parse order is the fix (spec req 1):

1. With a full header available, the parser verifies magic, version, seq
   (against the running frame index), complement, and the 1 MiB bound —
   and then the **independent header digest** — *before* the declared
   length is used to size the frame or to classify the tail as torn.
2. Only an authenticated header may produce the torn-tail classification
   (`remaining < header + length + tag` after step 1).
3. A partial header (< 53 bytes) is checked against the *known* fixed
   fields (magic, version, expected seq) for every byte present: a
   malformed available header raises `HOLD:JOURNAL_CORRUPT`; only a
   genuine byte-prefix tear recovers.
4. Payload/JSON/payload-seq and the whole-frame tag are verified exactly
   as in -15. Corruption anywhere raises `HOLD:JOURNAL_CORRUPT`;
   recovery (truncate to verified end + fsync) still runs before any
   append, under the per-capture fence, so an append never lands behind
   unvalidated bytes.

**Threat model, stated honestly (spec req 1):** the digests are *unkeyed*.
This defends the non-adversarial crash/corruption model — torn writes,
partial flushes, bit rot, accidental field damage. An actor who can
rewrite the entire journal can recompute every digest and forge a fully
self-consistent journal; no claim is made against that actor.

Retained from -15 unchanged (spec req 2): bounded length, exact
verified-end recovery, truncate+fsync-before-append, all-or-nothing
staging, intent fencing, crash reconciliation, validation pins, the
QFAR1 container/publisher body. Only the journal frame layer changed.

## Evidence (journal cases only, spec req 5 — run twice, byte-identical)

- **J-01** roundtrip append/read; file ends exactly at the verified end.
- **J-02** exhaustive cut→append→reopen at **every** byte offset of a
  3-frame journal (414 cuts): each recovers to exactly the complete-frame
  prefix plus the one new record, byte-exact.
- **J-03** the -15 blocker: interior first/interior frame with length+
  complement coherently set to a larger **in-bound** value (500,000,
  n+16, n = MAX, n = MAX+1) while later valid frames exist → every variant
  `HOLD:JOURNAL_CORRUPT` on read *and* on append, file bytes untouched
  (never truncated).
- **J-04** a bit flip in every fixed-header field/digest class (magic,
  version, seq, length, complement, header digest, payload, whole-frame
  tag) on frames 0 and 1 → all `HOLD:JOURNAL_CORRUPT`, file untouched.
- **J-05** malformed available header (full garbage header, short tail
  with bad magic, partial header with wrong seq) → `HOLD:JOURNAL_CORRUPT`;
  a genuine byte-prefix tear recovers and the next append completes it,
  truncating the torn bytes exactly.
- **J-06** real-process torn append (`crash_worker_h16.py` writes 3/5 of
  a genuine frame, fsyncs, `os._exit(3)`) → a fresh append recovers to
  exactly [record 0, record 1], journal ending exactly at the verified
  end.

Totals per run: **474 checks, 0 failures**; `results_run1.json` and
`results_run2.json` byte-identical (sha256 `aef4b094…` each). Staging,
fencing, crash-reconciliation, validation-pin and ceiling evidence is
reused from pins `1778dba` / `cf929e0` per spec req 5 — not rerun; no
64 MiB fixture.

## Scope confirmation

Offline only. Zero Yahoo/vendor/model/API calls, zero downloads beyond
the spec fetch, zero installs, zero spend, zero authenticated GitHub
operations, zero real publication/capture/backtest/holdout/production
changes. U-1 unprobed (HOLD). The -13 (1bb9b92), -14 (cf929e0) and -15
(1778dba) packages and the parked executor were never edited or run; all
verify byte-identical (executor `execute_capture.py` sha256 `8fe97abd…`).
This package is left uncommitted in the worktree.

Budget: ≤20 min, no repair allowance. Elapsed ≈ 4 minutes (spec fetch
05:26:59Z → packaging verified 05:30Z), no repair used, no defect found
in the candidate in-round.
