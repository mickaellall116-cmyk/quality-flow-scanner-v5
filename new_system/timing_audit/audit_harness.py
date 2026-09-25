"""
ERD v0.1 — 50-event Intrinio/Zacks timing-integrity audit harness.

Frozen gate (erd-v0.1-preregistration-amendment-1.md, section 15 DATA GATE):
  1. Random sample of 50 qualifying events, stratified to include >=10 BMO,
     >=10 AMC, spanning >=8 distinct calendar years.
  2. For each event, verify actual_reported_date, actual_reported_time, and the
     timing bucket against primary sources (company IR press release,
     Business Wire / PR Newswire / newswire timestamp). Record the source
     document per event in the audit log.
  3. Pass criteria: >=48/50 exact date+bucket matches; zero evidence of
     systematic revision patterns (e.g. vendor backfilling announced dates);
     coverage >=90%.
  4. Gate fails -> stop, report, ERD halts. No substitute earnings calendar
     without a new preregistration amendment.
  5. The audit log (50 rows + sources + verdict) is committed to the repo
     BEFORE any performance work begins.

This harness implements steps that can run without human judgment:
  fetch -> draw_sample -> build_verification_sheet -> score_sheet.
The primary-source verification itself is manual (a human checks each
newswire timestamp); the sheet is the tracking artifact for that work.

Generates ZERO performance data. This is a data-integrity gate, not a study.

Usage:
  export INTRINIO_API_KEY='<key>'   # never commit this
  python3 audit_harness.py fetch --start 2005-01-01 --end 2026-06-30 \\
      --out raw_surprises.json
  python3 audit_harness.py sample --in raw_surprises.json --seed 20260925 \\
      --out audit_sample.json
  python3 audit_harness.py sheet --in audit_sample.json \\
      --out verification_sheet.csv
  # ... human verifies each row against primary sources, fills the sheet ...
  python3 audit_harness.py score --in verification_sheet.csv
"""

import argparse
import csv
import json
import math
import os
import random
import sys
import urllib.request
import urllib.parse
from datetime import date

INTRINIO_BASE = "https://api-v2.intrinio.com"
SURPRISES_PATH = "/zacks/eps_surprises"

# Frozen strata (amendment section 15)
SAMPLE_N = 50
MIN_BMO = 10
MIN_AMC = 10
MIN_YEARS = 8
PASS_MATCHES = 48
PASS_COVERAGE = 0.90

# Intrinio actual_reported_code -> frozen timing bucket label
CODE_TO_BUCKET = {
    "BTO": "BMO",   # before the open  -> S = announcement day
    "AMC": "AMC",   # after market close -> S = next session
    "DTM": "DTM",   # during the market -> EXCLUDE per frozen event clock
}


# ---------------------------------------------------------------- fetch

def fetch_surprises(api_key, start_date, end_date, page_size=100):
    """Pull Zacks EPS Surprises pages from Intrinio. Returns list of records."""
    records = []
    next_page = None
    while True:
        params = {
            "api_key": api_key,
            "start_date": start_date,
            "end_date": end_date,
            "page_size": page_size,
        }
        if next_page:
            params["next_page"] = next_page
        url = INTRINIO_BASE + SURPRISES_PATH + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        batch = payload.get("eps_surprises") or payload.get("zacks_eps_surprises") or []
        records.extend(batch)
        next_page = payload.get("next_page")
        print(f"fetched {len(batch)} records (total {len(records)})", file=sys.stderr)
        if not next_page:
            break
    return records


# ---------------------------------------------------------------- sample

def _event_year(rec):
    d = rec.get("actual_reported_date") or ""
    return d[:4]  # YYYY-MM-DD


def _is_qualifying(rec):
    """Qualifying = has a parseable reported date and a known timing code."""
    d = rec.get("actual_reported_date") or ""
    code = (rec.get("actual_reported_code") or "").upper()
    if len(d) < 10 or d[4] != "-" or d[7] != "-":
        return False
    return code in CODE_TO_BUCKET


def draw_sample(records, seed):
    """
    Deterministic stratified draw honoring the frozen strata:
      50 events, >=10 BMO (BTO), >=10 AMC, >=8 distinct calendar years.
    Retries with seed+1, seed+2, ... until strata hold (bounded).
    Returns (sample_records, seed_used).
    """
    qualifying = [r for r in records if _is_qualifying(r)]
    bto = [r for r in qualifying if (r.get("actual_reported_code") or "").upper() == "BTO"]
    amc = [r for r in qualifying if (r.get("actual_reported_code") or "").upper() == "AMC"]
    if len(bto) < MIN_BMO or len(amc) < MIN_AMC:
        raise ValueError(
            f"insufficient stratified pool: BTO={len(bto)} AMC={len(amc)} "
            f"(need >={MIN_BMO} BTO and >={MIN_AMC} AMC)"
        )
    years_all = {_event_year(r) for r in qualifying}
    if len(years_all) < MIN_YEARS:
        raise ValueError(f"pool spans only {len(years_all)} years (need >={MIN_YEARS})")

    for attempt in range(1000):
        s = seed + attempt
        rng = random.Random(s)
        pick_bto = rng.sample(bto, MIN_BMO)
        pick_amc = rng.sample(amc, MIN_AMC)
        rest_pool = [r for r in qualifying
                     if r not in pick_bto and r not in pick_amc]
        rest = rng.sample(rest_pool, SAMPLE_N - MIN_BMO - MIN_AMC)
        sample = pick_bto + pick_amc + rest
        rng.shuffle(sample)
        years = {_event_year(r) for r in sample}
        if len(years) >= MIN_YEARS:
            return sample, s
    raise ValueError("could not satisfy year strata in 1000 attempts")


def to_audit_row(rec, idx):
    code = (rec.get("actual_reported_code") or "").upper()
    return {
        "event_id": f"EVT-{idx+1:03d}",
        "ticker": ((rec.get("security") or {}).get("ticker")
                   or rec.get("ticker") or ""),
        "intrinio_reported_date": rec.get("actual_reported_date") or "",
        "intrinio_reported_time": rec.get("actual_reported_time") or "",
        "intrinio_code": code,
        "derived_bucket": CODE_TO_BUCKET.get(code, ""),
        # --- human-filled below ---
        "primary_source_type": "",   # IR press release | Business Wire | PR Newswire | newswire
        "primary_source_url": "",
        "verified_date": "",
        "verified_time": "",
        "verified_bucket": "",       # BMO | AMC | DTM
        "date_bucket_match_YN": "",  # Y | N
        "notes": "",
    }


# ---------------------------------------------------------------- sheet

SHEET_FIELDS = ["event_id", "ticker",
                "intrinio_reported_date", "intrinio_reported_time",
                "intrinio_code", "derived_bucket",
                "primary_source_type", "primary_source_url",
                "verified_date", "verified_time", "verified_bucket",
                "date_bucket_match_YN", "notes"]


def write_sheet(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")


# ---------------------------------------------------------------- score

def score_sheet(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n = len(rows)
    filled = [r for r in rows if (r.get("date_bucket_match_YN") or "").strip().upper() in ("Y", "N")]
    matches = sum(1 for r in filled
                  if (r.get("date_bucket_match_YN") or "").strip().upper() == "Y")
    bmo = sum(1 for r in rows if (r.get("verified_bucket") or "").strip().upper() == "BMO")
    amc = sum(1 for r in rows if (r.get("verified_bucket") or "").strip().upper() == "AMC")
    years = { (r.get("verified_date") or "")[:4] for r in filled
              if len(r.get("verified_date") or "") >= 4 }
    years.discard("")
    # Row-level coverage proxy: fraction of sampled events with a valid
    # verified timing classification. (Full-window coverage per the amendment
    # also needs the universe pull; reported separately.)
    valid_timing = sum(1 for r in rows if (r.get("verified_bucket") or "").strip())
    coverage = (valid_timing / n) if n else 0.0

    # Revision-pattern screen: count mismatches by direction.
    mismatch_dirs = {}
    for r in filled:
        if (r.get("date_bucket_match_YN") or "").strip().upper() == "N":
            key = (f"intrinio={r.get('intrinio_reported_date')}/{r.get('intrinio_code')}"
                   f" vs verified={r.get('verified_date')}/{r.get('verified_bucket')}")
            mismatch_dirs[key] = mismatch_dirs.get(key, 0) + 1

    unfilled = n - len(filled)
    verdict = "INCOMPLETE"
    if unfilled == 0:
        verdict = ("PASS" if (matches >= PASS_MATCHES and coverage >= PASS_COVERAGE)
                   else "FAIL")

    report = {
        "n_rows": n,
        "n_scored": len(filled),
        "n_unfilled": unfilled,
        "exact_date_bucket_matches": matches,
        "pass_threshold_matches": PASS_MATCHES,
        "verified_BMO": bmo,
        "verified_AMC": amc,
        "years_covered": sorted(years),
        "n_years": len(years),
        "coverage_proxy": round(coverage, 4),
        "coverage_threshold": PASS_COVERAGE,
        "mismatch_breakdown": mismatch_dirs,
        "verdict": verdict,
    }
    print(json.dumps(report, indent=2))
    return report


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description="ERD 50-event timing-integrity audit harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="pull Zacks EPS Surprises from Intrinio")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("sample", help="draw the stratified 50-event sample")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("sheet", help="build the human verification sheet")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("score", help="score a filled verification sheet")
    p.add_argument("--in", dest="inp", required=True)

    args = ap.parse_args()

    if args.cmd == "fetch":
        key = os.environ.get("INTRINIO_API_KEY", "")
        if not key:
            sys.exit("INTRINIO_API_KEY is not set")
        recs = fetch_surprises(key, args.start, args.end)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"start": args.start, "end": args.end,
                       "n": len(recs), "records": recs}, f)
        print(f"saved {len(recs)} records -> {args.out}")

    elif args.cmd == "sample":
        with open(args.inp, encoding="utf-8") as f:
            payload = json.load(f)
        sample, seed_used = draw_sample(payload["records"], args.seed)
        rows = [to_audit_row(r, i) for i, r in enumerate(sample)]
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"seed_requested": args.seed, "seed_used": seed_used,
                       "n": len(rows), "rows": rows,
                       "source_window": {k: payload[k] for k in ("start", "end") if k in payload}},
                      f, indent=2)
        print(f"drew {len(rows)} events (seed {seed_used}) -> {args.out}")

    elif args.cmd == "sheet":
        with open(args.inp, encoding="utf-8") as f:
            payload = json.load(f)
        write_sheet(payload["rows"], args.out)

    elif args.cmd == "score":
        score_sheet(args.inp)


if __name__ == "__main__":
    main()
