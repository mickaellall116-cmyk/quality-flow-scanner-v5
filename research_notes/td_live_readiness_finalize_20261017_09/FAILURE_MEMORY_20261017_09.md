# FAILURE MEMORY — 2026-10-17 (-09)

Searchable keys: `ACCOUNT_STATUS_ENDPOINT_UNQUALIFIED`, `API_USAGE_COSTS_ONE_CREDIT`, `API_USAGE_SCHEMA_NO_STANDING_NO_MINUTE_CAP`.

- **Defect class:** an authorization precondition assumed a vendor endpoint was free; the vendor's own current documentation prices it. Twelve Data `GET /api_usage` is documented at https://twelvedata.com/docs#api-usage as **"API credits cost: 1 per request"** (fetched 2026-10-17). Any future packet that wants a "$0 account check" must first obtain a genuinely $0 route or an adjudication that explicitly prices the check (e.g., 1 credit inside a stated ceiling) — never assume account/usage endpoints are free.
- **Schema gap:** the documented `/api_usage` response is `{timestamp, current_usage, plan_limit, daily_usage, plan_daily_limit, plan_category}` — no standing field, no minute-cap field. Gate 3's required facts (Basic / good standing / fresh ≥51 / minute cap) cannot all be attested by this endpoint even if called; a future account-evidence design must name where standing and minute cap are attested, or amend gate 3 by adjudication.
- **Disposition in -09:** fail-closed at spec step 2. Zero authenticated calls, zero helper invocations, zero credits, zero ledger writes. The shared ledger remains the legacy bytes `7e5ccef0…`; the -07 candidate remains unadopted.
