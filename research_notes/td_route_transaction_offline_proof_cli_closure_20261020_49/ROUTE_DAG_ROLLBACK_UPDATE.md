# ROUTE DAG / ROLLBACK UPDATE — task -49 candidate revision (offline only)

Status: OFFLINE_CANDIDATE_NOT_ADOPTED. This record updates ONLY the route leg
of the -48 candidate transaction set. It is a new candidate file in the -49
package; no -48 file is edited.

## What changed vs the -48 candidate set

The -48 pin DAG (14 nodes / 27 edges, `dag.json` in the -48 package) is
carried unchanged for the readiness chain: supplement v2
(`55ad6f40509ac77f0634b8ab4208bf39017219ae065e240af852ac581c1acca5`) →
driver r5 (`d11c6b587c028c26c718c44966478c4635be6073217e0deb063d1f448958df83`)
→ gate r5 (`94ef967ca832faea4a4a21c666e1a310395961b6df342e098963728ce622555b`)
→ adapter r5 (`6980b5b3c887ea7e7c51c98ce5f77740b909539a838258fdcc7734ffae3422a5`)
→ executor r5 (`bbc23616b0b8c62f0a712ea7dc04b212f56f660d8020e7b0f2b4426fd6034541`).
None of those candidates pins a route member (entrypoint/constructor) in its
operative schema, so per task -49 spec §B.3 they stay byte-identical.

Route leg substitution (the only DAG change):

| node | -48 candidate pin | -49 candidate pin |
|---|---|---|
| entrypoint | `pilot_build_v6_dstfix.py` `442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6` | `pilot_build_v7_clibound.py` `84ccd2c68aea0f0c9b7e3e97e92ad870bbb3af84a125b75b2c1f3e57d20d7772` |
| constructor | `pilot_harness/construct_4h.py` `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd` (unchanged original) | `construct_4h_v3_cliguard.py` `3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb918402f8645a3fe0ad1` |
| validator | `validate_input_v3_dstfix.py` `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6` | unchanged |

New edges: entrypoint v7 → constructor candidate (exact-path binding, the
v7 file's only delta); entrypoint v7 → validator candidate (binding
unchanged from v6). Removed edges: entrypoint → pinned construct_4h.py
(superseded inside the candidate set only; the pinned file is untouched and
remains the accepted route member until a designation decision).

The updated pin record is `ROUTE_MANIFEST_CANDIDATE_V2.json` in this package
(canonical bytes, sha256
`3a6f86f1b19555cb9303ce4d035deef9df21f5d283b3f430703b44d875d02370`).

## Atomicity / inconsistent intermediates

The atomic set is unchanged in shape: designation, if ever decided, applies
to the whole candidate set at once (supplement/proof → driver → gate →
adapter → executor, plus the route leg entrypoint v7 → validator →
constructor candidate). The six inconsistent intermediate states identified
in -48 still fail closed at the existing hash checks; the route leg adds no
new intermediate state because the v7 entrypoint refuses (ImportError /
hash-visible binding) any constructor other than the exact-path candidate,
and the constructor candidate refuses direct CLI invocation (exit 3).

## Rollback

Unchanged from -48: rollback = withdraw the designation. Nothing is
overwritten by the candidate set — every candidate is an additive new file;
the pinned originals (`construct_4h.py` d47e8df1…, `pilot_build.py`,
`validate_input.py` 1b83cdcd…) and every accepted r4 file remain byte-stable
and become the route again on withdrawal. No state, ledger, or production
file is touched by this package.

## Open requirement carried

REQ-S2 (D−1…D+1 split exclusion at 4H assembly) remains unimplemented and
is a hard HOLD on any corrected-performance use. This update neither
implements nor waives it.
