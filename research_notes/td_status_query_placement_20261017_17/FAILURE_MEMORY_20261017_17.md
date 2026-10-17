# FAILURE MEMORY — QF-TD-STATUS-QUERY-PLACEMENT-20261017-17

## Canonical entry: STATUS_URL_QUERY_PARAM_ASSUMPTION

**Class:** fixture/boundary shape ASSUMED from a nearby name instead of
DERIVED from the real counterpart's declaration.

**What happened.** The -15 executor's final URL boundary required the
credential query key to be `access_token`. That string is the vault
ENTRY name (the `entry_name` selector in the helper API), not the
query parameter. The registered placement for `custom.twelvedata`
declares `{"query_param": "apikey"}`. The -15 offline fixtures were
built to the same wrong assumption (`good_token.py` emitted an
`access_token` shape), so the suite was self-consistent and green
while disagreeing with the only real counterpart. Live run -16's real
helper produced the `apikey` shape; the boundary refused pre-transport
(STATUS_URL_BOUNDARY, 0 requests transmitted, 0 credits) and the
one-use clearance was consumed on a HOLD.

**Lesson.** Any fixture that stands in for a real counterpart must
have its shape DERIVED from that counterpart's own declaration/record
(here: the placement record attested in committed evidence), with the
derivation cited and hash-pinned in the fixture. Self-consistency of
a fixture suite proves nothing about the counterpart. When a name
appears in two roles (entry name vs query parameter), treat the
collision as a hazard and prove which role the boundary consumes.

**-17 confirmations of the lesson.** (a) The corrected boundary's
expected key is pinned as a proven input fact (PLACEMENT_PROOF.md).
(b) The -17 repair itself re-hit the class: the inherited fixture
default helper (the -11 stub) returns the bare URL unchanged — an
empty query the r2 boundary tolerated and the r3 boundary correctly
refuses; the -17 default fixture helper is now placement-faithful by
construction (`helper_stub_placement.py` appends exactly the proven
pair via urlencode, dummy value).

**Distinction preserved.** A consumed status SLOT (journal
`status_calls: 1`) is not a transmitted request. -16 transmitted 0
requests; slot count and transmitted count are reported separately
everywhere.
