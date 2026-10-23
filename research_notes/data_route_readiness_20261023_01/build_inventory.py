import json, hashlib, os, csv, glob

UX51_EQ = ["NVDA","PLTR","TSLA","SOFI","SMCI","AMD","AAPL","MSFT","META","COIN","MSTR","AVGO","GOOGL","AMZN","NFLX","CRM","MU","INTC","LRCX","AMAT","QCOM","ARM","HOOD","APP","NET","SNOW","DDOG","CRWD","SHOP","RKLB","ASTS","LUNR","PYPL","NU","MELI","SPY","IWM","SMH","ARKK","XLF","NIO","MRNA","PFE","F"]
UX51_CR = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD","AVAX-USD","LINK-USD","XRP-USD"]

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

inv = {"task":"QF-DATA-ROUTE-READINESS-20261023-01","artifacts":[]}

# 1) TD Day-1 probe bodies (local store; byte-identical copies archived in qf-data-archive 2f223cf)
store = os.path.expanduser("~/workspace/qf_td_probe_d1_20261021/store")
for f in sorted(glob.glob(store+"/REQ-ADJ-*.json")):
    if "receipt" in f or "attempts" in f: continue
    d=json.load(open(f)); m=d["meta"]; v=d["values"]
    inv["artifacts"].append({"kind":"td_probe_response_body","path":f,"symbol":m["symbol"],
      "interval":m["interval"],"rows":len(v),"first_bar":v[0]["datetime"],"last_bar":v[-1]["datetime"],
      "timezone":"America/New_York (vendor stamps, bar open)","sha256":sha(f),
      "provenance":"IMMUTABLE_ARCHIVED qf-data-archive captures/td_probe_day1_20261021/ commit 2f223cf, re-fetch verified 20/20",
      "reuse_eligible":False,
      "reuse_note":"Probe window only (3 symbols, non-cohort windows). NVDA window overlaps sealed holdout dates: qualification-evidence use only, never cohort bytes. TSLA 2022 legs carry C2 NOT_EVALUABLE (volume completeness failure). AAPL window (2026) is outside both capture windows."})

# 2) Canonical Stage C raw_1h (Yahoo yfinance, fetched 2026-09-29, local worktree only)
rawdir = os.path.expanduser("~/workspace/canonical-stage-a/canonical_stage_c/raw_1h")
files = sorted(glob.glob(rawdir+"/*.csv"))
syms = {}
for f in files:
    sym = os.path.basename(f).replace("_p730.csv","").replace("_pmax.csv","")
    with open(f) as fh:
        r=list(csv.reader(fh)); hdr, rows = r[0], r[1:]
    syms[sym] = {"file":os.path.basename(f),"rows":len(rows),"first_bar":rows[0][0],"last_bar":rows[-1][0],"sha256":sha(f)}
present_eq = [s for s in UX51_EQ if s in syms]; missing_eq = [s for s in UX51_EQ if s not in syms]
present_cr = [s for s in UX51_CR if s in syms]; missing_cr = [s for s in UX51_CR if s not in syms]
inv["artifacts"].append({"kind":"yahoo_raw_1h_csv_set","path":rawdir,"file_count":len(files),
  "schema":"t,o,h,l,c,v (ISO stamps with ET offset)","fetch":"yfinance period=730d (3 symbols period=max), auto_adjust=False, prepost=False, 2026-09-29, per fetch_4h_manifest.json + STAGE_C_REPORT.md in canonical-stage-a",
  "span_example_AAPL":{"rows":syms["AAPL"]["rows"],"first_bar":syms["AAPL"]["first_bar"],"last_bar":syms["AAPL"]["last_bar"]},
  "ux51_equity_coverage":f"{len(present_eq)}/44","ux51_equity_missing":missing_eq,
  "ux51_crypto_coverage":f"{len(present_cr)}/7","ux51_crypto_missing":missing_cr,
  "per_file":{s:syms[s] for s in sorted(syms)},
  "provenance":"LOCAL_MUTABLE_WORKTREE ONLY. No per-response receipts, no hash chain, never committed to qf-data-archive. Yahoo serves no as-of/versioning evidence; bars are silently restatable.",
  "reuse_eligible":False,
  "reuse_note":"Coverage fails (crypto 0/7, equities incomplete), provenance fails (no immutable receipts), window fails (oldest bar 2023-10-31 is 8 sessions after the 2023-10-19 window start; the +-5-session tolerance recorded in Stage C was for that stage's 4H cache, not for this qualification). NOT cohort bytes."})

# 3) Absent / empty locations (verified this run)
inv["absent"]=[
 {"path":"~/workspace/quality-flow-scanner-v5/backtest_cache/ (D1)","state":"DOES NOT EXIST - destroyed with prior VM; 52 SHA256 pins survive, bytes do not"},
 {"path":"~/workspace/quality-flow-scanner-v5/pine_1h/","state":"fetch script + __pycache__ only, zero data files"},
 {"path":"~/workspace/data_archive/yahoo_1h_clean/","state":"EMPTY directory (0 files) - the parked Yahoo clean-capture lane never executed a capture"},
 {"path":"v54_forward_1h/ + v54_forward/ runtime dirs","state":"status/state/jsonl logs only; the harness keeps 1h frames in memory (prefetch) and persists no raw 1h frames"},
]
inv["verdict"]="RAW_1H_NOT_AVAILABLE for the frozen cohort: no existing local/repo artifact set is reuse-eligible as corrected-grid cohort bytes. Existing bytes serve only as route-qualification evidence (TD probe) or unqualified research cache (Stage C)."
out = os.path.expanduser("~/workspace/qf_data_route_stage/pkg/inventory.json")
json.dump(inv, open(out,"w"), indent=1)
print("equity coverage", len(present_eq), "/44 missing:", missing_eq)
print("crypto coverage", len(present_cr), "/7 missing:", missing_cr)
print("inventory written", out)
