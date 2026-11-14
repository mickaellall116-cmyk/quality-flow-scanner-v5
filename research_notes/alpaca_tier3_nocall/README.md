# Alpaca Tier-3 no-call reviewer package

This is a preparation-only package for the frozen 11-symbol Tier-3 historical
capture route. It performs no vendor calls, reads no credentials, purchases
nothing, and does not open or compute the holdout.

Current decision: `RIGHTS_GATE=HOLD`. The manifest has no affirmative immutable
record covering all four required rights: private raw persistence, deterministic
replay, internal research use, and a pinned retention/deletion window. The guard
therefore stops before credential lookup and before any injected network callable.

The pinned smoke request is one IREN SIP request over 2024-04-04 through
2024-04-23 inclusive (exclusive API end 2024-04-24). The adopted calendar has 14
regular sessions, so the exact 30-minute grid is 182 input rows and 98 derived
rows (six paired 09:30-anchored hours plus one separately flagged 15:30 terminal
half-hour per session). Native clock-hour aggregation is forbidden.
The validator normalizes RFC3339 timestamps to UTC using the standard-library
`zoneinfo` rules for America/New_York; it does not assume a fixed UTC offset and
includes a fall-DST boundary fixture.
The response validator follows Alpaca's documented single-symbol schema
(`bars`, `symbol`, `next_page_token`). Feed and timeframe are validated from the
pinned request metadata because the response does not echo those fields.
The full-window grid is session-close-aware: the two adopted 13:00 closes
(2023-11-24 and 2024-07-03) contribute seven half-hour inputs and four derived
rows each. Total expected coverage is 2,939 half-hour inputs and 1,583 derived
rows per symbol, not a regular-session count multiplied blindly by 13 or 7.

Run the offline proof:

```bash
python -m unittest -v test_alpaca_guard.py
MANIFEST_SHA=$(python -c 'import hashlib,json; x=json.load(open("manifest.json")); print(hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest())')
python alpaca_guard.py --manifest manifest.json --expected-manifest-sha256 "$MANIFEST_SHA"
```

The second command must exit 3 with `RIGHTS_GATE_NOT_GO` and `calls_used=0`.
Any future GO requires a new, hash-pinned manifest and adjudication record plus
separate recorded authority for the call. Changing only an environment variable
cannot clear the gate.
