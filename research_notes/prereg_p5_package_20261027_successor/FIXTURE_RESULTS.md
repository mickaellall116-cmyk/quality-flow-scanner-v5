# Fixture Results — P5 successor package staging run, 2026-10-27

Run in `~/workspace/qf_prereg_v10_stage/p5_package_successor/` before
commit. Generator: `python3 generate_p5_config.py` →
`7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9` —
byte-identical to the predecessor config (bb90d72); no parameter changed.

```
PASS  positive: committed config validates  [VALID: per_fill_config.json sha256=7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9]
PASS  positive: S8 example, exit +10% = 26.25 bps of entry notional  [total=$26.2500 on $10,000]
PASS  positive: S8 example, exit -4% = 24.5 bps of entry notional  [total=$24.5000 on $10,000]
PASS  positive: S8 equivalence note, TP1 leg = 6.25 bps of full notional at TP1 price  [tp1_leg=$6.8750]
PASS  idempotence: two generator runs byte-identical  [sha256=7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9]
PASS  idempotence: generator output == committed config
PASS  negative: tampered verdict_round_trip_bps 25 -> 30  [REJECT: pinned parameter verdict_round_trip_bps = 30, frozen text requires 25]
PASS  negative: missing parameter key (tp1_fill_rule)  [REJECT: parameter key set mismatch]
PASS  negative: unknown parameter key (bogus_fee_bps)  [REJECT: parameter key set mismatch]
PASS  negative: provenance flip PROPOSED -> PINNED  [REJECT: provenance key set mismatch: a PROPOSED entry carries exactly ['derivation', 'requires_review', 'status'], got ['citation', 'status']]
PASS  negative: provenance PINNED entry with spurious extra key (review_note)  [REJECT: provenance key set mismatch: a PINNED entry carries exactly ['citation', 'status'], got ['citation', 'review_note', 'status']]
PASS  negative: provenance PROPOSED entry missing requires_review  [REJECT: provenance key set mismatch: a PROPOSED entry carries exactly ['derivation', 'requires_review', 'status'], got ['derivation', 'status']]
PASS  negative: provenance PROPOSED entry missing derivation  [REJECT: provenance key set mismatch: a PROPOSED entry carries exactly ['derivation', 'requires_review', 'status'], got ['requires_review', 'status']]
PASS  negative: out-of-range e1_stop_slippage_atr = -0.5  [REJECT: pinned parameter e1_stop_slippage_atr = -0.5, frozen text requires 0.05]
PASS  negative: wrong expected hash  [REJECT: hash mismatch]
FIXTURES: 15/15 PASS
```

Exit code 0. All 12 predecessor fixtures pass with unchanged outcomes
(the provenance-flip fixture now rejects on the exact-key-set leg instead
of the status leg; the outcome — rejection — is the same). Negative
fixtures pass the tampered file's own correct hash to the validator, so
each rejection is issued by schema/value validation, not by the hash
check (the wrong-hash fixture covers the hash leg itself).

## Discrimination check — predecessor validator vs successor validator

Each successor tampered file (own correct hash) was also run against the
predecessor validator from bb90d72, to prove the new fixtures pin the
tightening and are not vacuous:

| Tampered config | Predecessor (bb90d72) | Successor |
|---|---|---|
| PINNED provenance entry + spurious `review_note` key | **VALID (rc 0)** — the gap | REJECT (rc 1), exact key set |
| PROPOSED provenance entry missing `derivation` | **VALID (rc 0)** — the gap (derivation was never checked) | REJECT (rc 1), exact key set |
| PROPOSED provenance entry missing `requires_review` | REJECT (rc 1), via its requires_review presence check | REJECT (rc 1), exact key set fires first |
