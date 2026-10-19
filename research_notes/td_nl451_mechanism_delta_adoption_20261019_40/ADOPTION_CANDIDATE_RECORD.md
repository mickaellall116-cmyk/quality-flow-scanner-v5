# ADOPTION CANDIDATE — TD NL451 closed-session classifier lineage (RESEARCH-ONLY)

- Task: QF-TD-NL451-MECHANISM-DELTA-ADOPTION-20261019-40 r1 (spec: Issue #1 comment 6278932260)
- Status: **AWAITING_INDEPENDENT_REVIEW** — this is a CANDIDATE. Nothing is adopted, merged, or activated by this record. Nothing here is placed in a production or live path.
- Basis: adjudication verdict `PIN_ORIGIN_CONFLATION_CONFIRMED__OPTION_B_NL451_SELECTED` — the original supplement's "5.5.0" calendar pin was a cross-lineage conflation from the CP1 audit environment; the TD lineage's proven pandas_market_calendars version is **4.5.1**.

## Bound components (byte copies in this package unless noted)

| Component | sha256 | Source |
|---|---|---|
| Collector `td_min_collector.py` (UNCHANGED) | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` | commit `ab254c3`, `research_notes/td_lifecycle_repair_candidate/td_min_collector.py` |
| NL451 candidate supplement `p2_spot_supplement_v2_nl20261015_candidate.json` | `9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32` | NLQUAL package 2026-10-15 |
| Validator `validate_input.py` (mechanism module, UNCHANGED) | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` | commit `ab254c3`, `research_notes/pilot_harness/validate_input.py` |
| TD lock `integration_requirements.lock` | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` | commit `ab254c3` |
| Prior 28-case NLQUAL proof | manifest `ce5ba84e4b6c40649d79d2ee1dcba991dce61d0a7a9a5340e38aa54646ae1edb` (copy: `nlqual_sha256_manifest.txt`; 20/20 entries re-verified reproducing in this run) | `research_notes/td_closed_session_classifier_nlqual_evidence_20261015/` — 28/28 PASS twice, byte-identical |
| New 8-case P-family delta proof | `p_delta_results.json` `4fe4411b30b4ca8cf4d51abcea7b41c08479a382a3401356a5bf8493013b380e` | this package — 8/8 PASS, single invocation |

## Also cited (hash-gated in this run, copies not duplicated here)

- Original supplement `p2_spot_supplement_v2.json` @ `ab254c3`: `cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31` (superseded candidate basis — NOT edited or altered in place)
- Fixture suite `test_closed_session_classifier.py` @ `ab254c3`: `3122bdfc5df432932395948216e4ec6cc50e438abe2518cd0a5984154c4d71d0`
- Pilot requirements `research_notes/pilot_harness/requirements.txt` @ `ab254c3`: `812c526fc0392dd81a4c6224e004eab169e973ec48a3103939f2f61b2ff85066`
- Wheelhouse manifest `~/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt`: 11/11 wheels re-verified; PMC 4.5.1 wheel `7b4f3478cc18f44d6ce7d62fbac847b9b7b53bd6fd9d2d06cd76551112cc0bfd`

## Scope limits (unchanged by this candidate)

- The supplement binds the SPOT8 manifest scope only (REQ-SPT-07/08). FRESH-manifest use needs a new supplement version.
- This candidate does NOT qualify P2 v1, does NOT rewrite the SPT-07 v1 HOLD, does NOT dispatch SPT-08, does NOT qualify vendor data or performance, and does NOT authorize production use.
