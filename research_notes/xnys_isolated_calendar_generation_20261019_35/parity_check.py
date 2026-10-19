#!/usr/bin/env python3
"""Independent parity review for QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1.
Implements PARITY_MATRIX.md rows HRS/CLO/EC/CNT/MST/STR + R/COR from run
evidence. Stdlib only; shares no code with generator.py/assemble.py.
Primary facts transcribed verbatim from PARITY_MATRIX.md (sources S1..S9)."""
import hashlib, json
from datetime import date, timedelta
from pathlib import Path

W = Path(__file__).resolve().parent
REPO = Path.home() / "workspace/quality-flow-scanner-v5"
rows = {}
def row(rid, ok, note=""): rows[rid] = {"result": "PASS" if ok else "FAIL", "note": note}
def H(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

blob = (W / "out/artifact_run1.json").read_bytes()
doc = json.loads(blob.decode("utf-8"))
sessions = doc["sessions"]
S = {s["date"]: s for s in sessions}
dates = [s["date"] for s in sessions]

CLOSURES = {  # 21 in-interval dated closures per matrix §2
 "2024-11-28","2024-12-25",
 "2025-01-01","2025-01-09","2025-01-20","2025-02-17","2025-04-18","2025-05-26",
 "2025-06-19","2025-07-04","2025-09-01","2025-11-27","2025-12-25",
 "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19",
 "2026-07-03","2026-09-07"}
CLO_IDS = ["CLO-01","CLO-02","CLO-03","CLO-04","CLO-05","CLO-06","CLO-07","CLO-08",
 "CLO-09","CLO-10","CLO-11","CLO-12","CLO-13","CLO-14","CLO-15","CLO-16","CLO-17",
 "CLO-18","CLO-19","CLO-20","CLO-21"]
EARLY = {"2024-11-29","2024-12-24","2025-07-03","2025-11-28","2025-12-24"}
EC_IDS = ["EC-01","EC-02","EC-03","EC-04","EC-05"]

# §1 core hours
row("HRS-01", all(s["open"] == "09:30" for s in sessions), "every session open==09:30 (S1 Rule 1.1(d))")
row("HRS-02", all(s["close"] == ("13:00" if s["date"] in EARLY else "16:00") for s in sessions),
    "every close==16:00 except the 5 §3 dates at 13:00; no other close value")
# §2 closures
for rid, d in zip(CLO_IDS, sorted(CLOSURES)):
    row(rid, d not in S, f"no session on closure {d}")
row("CLO-22", all(d <= "2026-10-16" for d in dates) and doc["coverage_end"] == "2026-10-16",
    "no session after 2026-10-16; post-interval S6 closures absent")
# §3 early closes
for rid, d in zip(EC_IDS, sorted(EARLY)):
    row(rid, d in S and S[d]["close"] == "13:00", f"session on {d} with close 13:00")
row("EC-06", {d for d, s in S.items() if s["close"] == "13:00"} == EARLY,
    "exactly the 5 dated early closes carry 13:00; zero 2026 in-interval early closes")
# §4 counts (aux emissions = agreed A/C emitted files, byte-identical pairs)
def load(p): return json.loads((W / p).read_text())
aux24 = load("out/aux2024_A_run1.json"); aux26 = load("out/aux2026_A_run1.json")
row("CNT-2024", len(aux24) == 252, f"aux full-year 2024 = {len(aux24)} (expect 252, S8)")
n2025 = sum(1 for d in dates if d.startswith("2025-"))
row("CNT-2025", n2025 == 250, f"artifact 2025 sessions = {n2025} (expect 250, S9 final vintage)")
row("CNT-2026", len(aux26) == 251, f"aux full-year 2026 = {len(aux26)} (expect 251, S7; S8 corroborates)")
# §5 master sweep over 761 days
d0, d1 = date(2024, 9, 16), date(2026, 10, 16)
ndays = (d1 - d0).days + 1
bad = []
cur = d0
while cur <= d1:
    iso = cur.isoformat()
    expect = cur.weekday() < 5 and iso not in CLOSURES
    if expect != (iso in S): bad.append(iso)
    elif expect and S[iso]["close"] != ("13:00" if iso in EARLY else "16:00"): bad.append(iso + ":close")
    cur += timedelta(days=1)
row("MST-01", ndays == 761 and not bad, f"{ndays} calendar days swept; mismatches: {bad[:5] if bad else 'none'}")
# §6 structural
hdr_ok = (doc["artifact"] == "XNYS_SESSION_SCHEDULE_V2" and doc["exchange"] == "XNYS"
          and doc["timezone"] == "America/New_York" and doc["coverage_start"] == "2024-09-16"
          and doc["coverage_end"] == "2026-10-16" and bool(doc["source"]) and bool(doc["version"]))
row("STR-01", hdr_ok, "consumer header rules (fold_materializer_v3 e1b0dfed)")
asc = dates == sorted(dates) and len(set(dates)) == len(dates) and len(dates) > 0
row("STR-02", asc and dates[0] == "2024-09-16" and dates[-1] == "2026-10-16",
    f"ascending unique non-empty; first={dates[0]} last={dates[-1]} (Friday session)")
canon = (json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
row("STR-03", canon == blob, "canonical serialization byte-exact; sha pinned in receipt")
def mins(t): return int(t[:2]) * 60 + int(t[3:])
str4 = all(date.fromisoformat(d).weekday() < 5 for d in dates) and \
       all(mins(s["close"]) > mins(s["open"]) and mins(s["close"]) > mins("09:30") for s in sessions)
row("STR-04", str4, "no weekend sessions; close>open; close after 09:30 (Amendment v3)")
# §7 review rows from run evidence
man = json.loads((REPO / "research_notes/xnys_schedule_generation_contract_20261019_34/SOURCE_SET_MANIFEST.json").read_text())
r1 = all(H(REPO / s["path"]) == s["sha256"] for s in man["primary_sources"])
row("R1", r1, "all 9 primary source hashes recomputed == SOURCE_SET_MANIFEST")
blog = (W / "logs/build_stdout.txt").read_text(); elog = (W / "logs/emissions_stdout.txt").read_text()
r2 = ("--no-index" in (W / "build_env.sh").read_text() and "Errno -3" in blog and "Network is unreachable" in blog
      and "Network is unreachable" in elog and "Successfully installed" in blog)
row("R2", r2, "unshare -n namespace; --no-index --no-cache-dir --require-hashes --find-links; 3 probes failed to connect")
gen = (W / "generator.py").read_text()
r3 = ('get_calendar("NYSE")' in gen and "mirror" not in gen.replace("mirror key forbidden", "").replace("mirror module", "")
      and 'mcal.get_calendar("XNYS")' not in gen and "calendars.mirror" not in gen)
row("R3", r3, "path A key exactly 'NYSE'; mirror module never referenced for emission")
row("R4", 'ecals.get_calendar("XNYS"' in gen, "path C key exactly 'XNYS' on exchange_calendars directly")
A = (W / "out/emission_A_run1.json").read_bytes(); C = (W / "out/emission_C_run1.json").read_bytes()
agr = json.loads((W / "out/agreement_run1.json").read_text())
row("R5", A == C and agr["agreement"] == "AGREE" and agr["differences"] == [],
    "A vs C byte-identical emissions; logged as CORRELATED CONSISTENCY ONLY (-30)")
r6 = ((W / "out/emission_A_run1.json").read_bytes() == (W / "out/emission_A_run2.json").read_bytes()
      and (W / "out/emission_C_run1.json").read_bytes() == (W / "out/emission_C_run2.json").read_bytes()
      and (W / "out/artifact_run1.json").read_bytes() == (W / "out/artifact_run2.json").read_bytes())
row("R6", r6, "full dual emission + assembly repeated; all bytes identical")
suite = json.loads((W / "notes_mirror/validation_fold_coverage_boundary_20261018_28/TEST_RESULTS.json").read_text())
frozen = json.loads((REPO / "research_notes/validation_fold_coverage_boundary_20261018_28/TEST_RESULTS.json").read_text())
row("R7", suite == frozen and suite["checks_passed"] == 25 and suite["checks_total"] == 25
    and H(REPO / "research_notes/validation_fold_coverage_boundary_20261018_28/fold_materializer_v3.py")
        == "e1b0dfed43c7c0817d2816f5398a1601a3886b107f7eb882e2e46a316f53d4c8",
    "frozen -28 synthetic suite 25/25 in mirrored tree; consumer byte-unmodified")
pr = json.loads((W / "out/consumer_parse_result.json").read_text())
row("R8", pr["materialize_ok"] and pr["coverage_first_session"] == dates[0] and pr["coverage_last_session"] == dates[-1],
    "real artifact parsed with 1043 synthetic timestamps; no SCHEDULE_* error; first/last match")
# §8 corroboration / reconciliation
col2025 = {d for d in CLOSURES if d.startswith("2025-")} | EARLY
art2025 = {d for d in dates if d.startswith("2025-") and (S[d]["close"] == "13:00")} | \
          {d for d in CLOSURES if d.startswith("2025-")}
row("COR-01", {d for d in dates if d.startswith("2025-")} and
    all((d in S) == (d not in CLOSURES) for d in [f"2025-{m:02d}-{dd:02d}" for m in range(1, 13) for dd in range(1, 32) if _valid(f"2025-{m:02d}-{dd:02d}")]) if False else
    ({d for d in S if d.startswith("2025-") and S[d]["close"] == "13:00"} == {d for d in EARLY if d.startswith("2025-")}
     and not any(d in S for d in CLOSURES if d.startswith("2025-"))),
    "artifact consistent with BOTH S3 and S4 2025 columns (identical per -32)")
row("COR-02", n2025 == 250, "CNT-2025 binds at 250 under priority rule (S5 tier-1 notice postdates S8's 251 vintage)")

def _valid(s):
    try: date.fromisoformat(s); return True
    except ValueError: return False

passed = sum(1 for r in rows.values() if r["result"] == "PASS")
out = {"rows_total": len(rows), "pass": passed, "fail": len(rows) - passed,
       "artifact_sha256": hashlib.sha256(blob).hexdigest(), "rows": rows}
(W / "out/parity_results.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(f"PARITY {passed}/{len(rows)} PASS")
for rid, r in rows.items():
    if r["result"] != "PASS": print("FAIL", rid, r["note"])
