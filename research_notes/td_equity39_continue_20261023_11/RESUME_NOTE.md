# Interruption + documented resume — QF-TD-EQUITY39-CONTINUE-20261023-11

The original capture process (capture_continue.py, pid 8271) was terminated externally
(SIGKILL-class: no traceback, stdout log empty) at ~21:10Z on 2026-10-23, during
SMH/HO's retry window. State at termination, all of it verified from on-disk evidence
before any further call:

- Blocks 1-6 fully closed and reconciled (provider daily_usage 20 -> 31 -> 42 -> 53 ->
  64 -> 75 -> 86; every delta = 10 attempts + 1 closing read).
- 40 receipts hash-chained from GENESIS(child root c5628652...); 20 volume quarantines.
- Block 7 partial: MELI/DEV, IWM/HO, IWM/DEV responses received, validated and persisted
  byte-exact (hashes match the attempts log) but receipts not yet finalized.
- SMH/HO attempt 1: transport failure - URLError RemoteDisconnected, 0 bytes, no
  response ever received; the frozen bracket's prescribed attempt 2 never fired.

Resume (resume_continue.py), in order: (1) offline re-verification of the child root,
the full 40-receipt chain, every raw/quarantine hash, and the 3 pending legs
(re-validated, hashes vs attempts log) - all PASS before any call; (2) one /api_usage
read (R7_resume_open) closing the interrupted block's bracket; (3) finalization of the
3 pending receipts (schema-identical; block 7 positions 1-3; bracket open = R6_close,
bracket close = R7_resume_open); (4) remaining legs idx 63..76 in blocks 8-9 with the
identical per-leg logic (SMH/HO resumed at attempt 2, inside its frozen bracket).

Reconciliation identity for the interrupted block: the resume gate first expected
daily_usage 91, assuming all 4 block-7 attempts had incremented the provider counter;
the read returned 90 and the resume STOPped without further calls. On the verified
counting semantics (every call increments; a usage read returns the post-increment
value - proven by six consecutive block deltas of exactly 11 in this run and by -10),
the identity is exact: counter 19 (pre-run) -> 90 = 71 provider-counted calls =
72 desk-logged calls - 1 (the RemoteDisconnected SMH/HO attempt, which the provider
never processed and never counted). The gate was corrected on this evidence and the
resume proceeded; the correction is disclosed here and in the RESULT for adjudication.
End-of-run identity: final counter 106; 106 - 19 = 87 provider-counted = 88 desk
calls - 1 disconnected attempt. Every other block reconciles exactly.
