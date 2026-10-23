import json, hashlib, os
EQ = ["NVDA","PLTR","TSLA","SOFI","SMCI","AMD","AAPL","MSFT","META","COIN","MSTR","AVGO","GOOGL","AMZN","NFLX","CRM","MU","INTC","LRCX","AMAT","QCOM","ARM","HOOD","APP","NET","SNOW","DDOG","CRWD","SHOP","RKLB","ASTS","LUNR","PYPL","NU","MELI","SPY","IWM","SMH","ARKK","XLF","NIO","MRNA","PFE","F"]
CR = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD","AVAX-USD","LINK-USD","XRP-USD"]
ordered = EQ + CR
od = hashlib.sha256(("\n".join(ordered)+"\n").encode()).hexdigest()
body = {
 "manifest_id":"QF-CAPTURE-MANIFEST-CANDIDATE-20261023-01",
 "status":"CANDIDATE_NOT_ADOPTED - authorizes nothing; capture requires Mike's GO (see AUTHORIZATION_CARD.md)",
 "lineage":"-85 plan ad9fda5 -> -88 manifest 6b0f5d0 -> -91 BLOCK-BRACKET-10 correction db9e0f3 -> -93 receipt-schema amendment 96cd2bb -> this candidate re-issue 2026-10-23",
 "provider":"Twelve Data","endpoint_class":"/time_series (data legs) + /api_usage (preflight, 1 per execution day, never retried)",
 "universe":{"name":"UX51 (Option A freeze, commit 2705c02)","membership_sha256_sorted":"b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2",
   "ordered_symbols":ordered,"ordered_digest_sha256":od,"equities":44,"crypto":7},
 "calendar":{"equity":"751-session XNYS union (adopted, three-gate freeze a126ce5): -81 extension 227 sessions 2023-10-19..2024-09-15 + XNYS_SESSION_SCHEDULE_V2 524 sessions 2024-09-16..2026-10-16","crypto":"S-C1..S-C6 continuous: session = ET date, [D 09:30 ET, D+1 09:30 ET)",
   "disclosed_assumption":"CH-1 carried per freeze (2023 core-hours documentation pursued in parallel, non-blocking)"},
 "rule_version":"2026-09-15-v54",
 "request":{"interval":"1h","adjust":"splits (uniform split-adjusted basis; E3 Mode A decision-time; S2 rejected/retired)","outputsize":5000,
   "bar_stamp":"bar open","timezone":"America/New_York","response_at_5000_rows":"fail-closed truncation defect by construction (largest legit leg 4,993 bars)"},
 "windows":{"W_HO":{"equity_sessions":"2023-10-19..2024-09-15","crypto_dates":"2023-10-19..2024-09-15 (333 dates)","note":"capture does NOT open the sealed holdout; bytes are qualification input only; single governed use remains -25 S50"},
   "W_DEV":{"equity_sessions":"2024-09-16..2026-10-16 (dev ends at last adopted-calendar session; extension is a separate decision)","crypto_dates":"2024-09-16..2026-10-16 (761 dates)"}},
 "legs":{"equity":"44 symbols x 2 window legs = 88 (expected rows HO 1,583 / DEV 3,653, calendar-derived; mismatch enumerated in receipt, adjudicated by completeness checker, never silently accepted)",
   "crypto":"7 symbols x 6 date-bounded chunks (<=208 ET dates each, max 4,993 bars) = 42; chunk bounds per -88 S3.2 table",
   "data_legs_total":130,
   "accounting":"BLOCK-BRACKET-10 (-91): program 146 expected / 289 worst case; pilot 19 expected / 37 worst (5 session-bound full-span symbols + BTC-USD 6 chunks)",
   "ceiling_proposal":"300 credits (Mike's open ruling: 300 vs ~320; a ceiling is not a GO)"},
 "expected_schema":{"columns":{"datetime":"string, ISO bar-open stamp, America/New_York","open":"number, finite","high":"number, finite","low":"number, finite","close":"number, finite","volume":"number, finite, >= 0"},
   "meta_required":["symbol","interval","currency","exchange","type"],"status_required":"ok"},
 "policies":{"missing":"row-count vs calendar expectation enumerated in receipt; zero-row session = COMPLETENESS_FAIL at qualification; no silent acceptance, no re-chunking",
   "duplicate":"duplicate UTC instant within a leg = fail-closed refusal (instant comparison, never wall-clock - the -94 lesson)",
   "gaps":"intra-leg continuity checked on UTC instants; a gap is a coverage finding for the checker, never papered over",
   "pagination":"none permitted; a 5000-row response aborts the leg as a truncation defect",
   "retries":"at most 2 attempts per leg (bracket accounting); /api_usage never retried; any leg exhausting its bracket STOPS the capture"},
 "destination":{"archive":"qf-data-archive (private), captures/td_capture_<EXEC_DATE>/ - append-only, write-once, SHA256SUMS verified by re-fetch; deletion only on Mike's approval",
   "local":"working store under ~/workspace, byte-identical to archive copies"},
 "receipt":"see receipt_schema.json (kind-discriminated, hash-chained, root digest over this manifest)"
}
canon = json.dumps(body, sort_keys=True, separators=(",",":")).encode()
body["root_digest_sha256"] = hashlib.sha256(canon).hexdigest()
out = os.path.expanduser("~/workspace/qf_data_route_stage/pkg/capture_manifest.json")
json.dump(body, open(out,"w"), indent=1)
print("ordered digest", od); print("root digest", body["root_digest_sha256"]); print("written", out)
