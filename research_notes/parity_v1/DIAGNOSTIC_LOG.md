# Databento Parity — Diagnostic Ladder Log

Run: 2026-11-03 ~21:32–21:40 ET (America/New_York)
Outcome: **CONFIRMED BLOCKER — HTTP 401 on every endpoint × construction. Full parity job NOT executed.**

## Credential facts (no key value recorded)
- Source: `~/.databento-qfs-credentials` (JSON, key `DATABENTO_API_KEY`, mode 0600), supplied directly by Mike for this task.
- Key shape: 35 characters, `db-` prefix — matches Databento's standard key format exactly (no truncation, no stray whitespace).
- Account: created 2026-11-03 ~20:56 ET; portal verified live (per task brief). Key is ~40 minutes old at time of test.

## Ladder results (exact HTTP status per step)

| Step | Endpoint | Construction | Status |
|---|---|---|---|
| (a) | GET /v0/metadata.dataset.list | Basic auth (key as username, empty password) | **404** — route does not exist (Databento's actual route is `metadata.list_datasets`); auth not evaluated |
| (a′) | GET /v0/metadata.list_datasets | Basic auth | **401** `auth_authentication_failed` |
| (a″) | GET /v0/metadata.list_datasets | Authorization: Bearer | **401** `auth_authentication_failed` |
| (b) | GET /v0/metadata.list_schemas?dataset=EQUS.MINI | Basic auth | **401** `auth_authentication_failed` |
| (b′) | GET /v0/metadata.list_schemas?dataset=EQUS.MINI | Authorization: Bearer | **401** `auth_authentication_failed` |
| (c)(i) | POST /v0/timeseries.get_range (SPY, ohlcv-1h, 2024-06-03→06-04) | Streaming, Basic auth, form-encoded | **401** `auth_authentication_failed` |
| (c)(ii) | POST /v0/timeseries.get_range (same probe) | Streaming, Bearer header | **401** `auth_authentication_failed` |
| (c)(iii) | metadata.list_datasets + metadata.list_schemas via official `databento` pip package v0.90.0 (`db.Historical(key)`, venv in this dir) | Official client (Basic under the hood) | **401** `BentoClientError: auth_authentication_failed` on both calls |

Error body (all 401s, identical): `{"detail":{"case":"auth_authentication_failed","message":"Authentication failed.","status_code":401,"docs":"https://databento.com/docs/portal/api-keys","payload":null}}`

## Interpretation (for the propagation-vs-entitlement decision)
- The 401 is uniform across raw HTTP (Basic + Bearer) and the official client, on metadata and timeseries alike — this rules out client-side construction error. The key is well-formed (35 chars, `db-` prefix).
- Two live hypotheses remain, not decidable from the API side:
  1. **Propagation/activation lag** — key minted ~20:56 ET, first probes ~21:32 ET; if Databento keys activate asynchronously, a retest after a longer interval (e.g. next morning) would clear it.
  2. **Entitlement/plan state** — the account may need a completed step (payment method, plan selection, or key-scope setting in the portal) before the Historical API accepts the key, even though the portal itself is live.
- Suggested decider: check the key's status/scope on the portal API-keys page; if it shows active, wait and retest the ladder once; if it shows pending/scoped, fix the portal state first.

## Not done (blocked upstream)
- No `metadata.get_cost` call (requires auth).
- No Databento pull, no comparison, no PARITY_RECEIPT.md / parity_detail.csv — Step 2 never started.
- Nothing posted or committed.
