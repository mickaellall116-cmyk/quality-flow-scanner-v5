"""
ERD v0.1 -- 50-event Intrinio/Zacks timing-integrity audit harness.

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

Reviewer-mandated integrity controls (ChatGPT PASS decision, 2026-09-25):
  C1. Sample hash: SHA-256 over a canonical serialization of each sampled
      row's vendor fields, stored in audit_sample.json BEFORE any human
      examines evidence. `sheet` and `score` recompute and REFUSE on mismatch.
  C2. Raw vendor data immutability: `fetch` stores SHA-256 of the raw record
      payload as `raw_hash`; `sample` verifies before drawing and refuses on
      mismatch; `verify` re-hashes any fetch file (OK / TAMPERED).
  C3. No-replacement rule: sampled events are final. A missing/ambiguous
      event scores as a non-match and against coverage per the frozen rules;
      it is NEVER swapped for a convenient substitute. No code path exists
      that replaces sampled events.
  C4. Precommitted evidence precedence (EVIDENCE_PRECEDENCE): printed into
      the verification sheet header BEFORE human examination.
  C5. Scorer version freeze (SCORER_VERSION): embedded in the sample file,
      the sheet header, and the score report. `sheet` and `score` REFUSE
      artifacts from any other scorer version. Frozen before real data.
  C6. Duplicate/revision handling: duplicate vendor rows (same ticker+date)
      are dropped before stratification and reported (one event = one slot);
      detect_vendor_revisions() diffs two pulls on event key and flags any
      timing-field restatement (backfill) for the gate's systematic-revision
      screen.

Generates ZERO performance data. This is a data-integrity gate, not a study.

Usage:
  export INTRINIO_API_KEY='<key>'   # never commit this
  python3 audit_harness.py fetch --start 2005-01-01 --end 2026-06-30 \\
      --out raw_surprises.json
  python3 audit_harness.py verify --in raw_surprises.json
  python3 audit_harness.py sample --in raw_surprises.json --seed 20260925 \\
      --out audit_sample.json
  python3 audit_harness.py sheet --in audit_sample.json \\
      --out verification_sheet.csv
  # ... human verifies each row against primary sources, fills the sheet ...
  python3 audit_harness.py score --in verification_sheet.csv
"""

import argparse
import csv
import hashlib
import json
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

VALID_BUCKETS = {"BMO", "AMC", "DTM"}

# C5: scorer version. Frozen before real data. Embedded in the sample file,
# the verification sheet header, and the score report; `sheet` and `score`
# REFUSE when the version on the artifact differs from this harness.
# Bump ONLY with a new preregistration amendment.
SCORER_VERSION = "1.0.0"


class SampleIntegrityError(ValueError):
    """Sample/raw integrity verification failed. Never caught silently."""


# ---------------------------------------------------------------- C6: event identity, duplicates, revisions

TIMING_FIELDS = ("actual_reported_date", "actual_reported_time",
                 "actual_reported_code")


def _event_key(rec):
    """Canonical event identity: ticker + reported date. Two vendor rows with
    the same key are the same earnings event (duplicates or revisions)."""
    ticker = ((rec.get("security") or {}).get("ticker")
              or rec.get("ticker") or "").strip().upper()
    return (ticker, (rec.get("actual_reported_date") or "").strip())


def dedupe_records(records):
    """Drop duplicate vendor rows (same ticker+date), keeping the first
    occurrence. Returns (unique_records, n_duplicates_removed). Duplicates are
    reported, never silently collapsed: one event must never occupy two
    sample slots."""
    seen = set()
    unique = []
    for r in records:
        k = _event_key(r)
        if k in seen:
            continue
        seen.add(k)
        unique.append(r)
    return unique, len(records) - len(unique)


def detect_vendor_revisions(old_records, new_records):
    """Diff two vendor pulls on event key. A timing-field change between pulls
    is a vendor revision (restatement/backfill) -- the exact pattern the
    frozen gate's 'no systematic revision' criterion screens for.
    Returns {"changed": [...], "added": [...], "removed": [...]} where each
    changed entry is {"event_key", "ticker", "changes": {field: (old, new)}}.
    Pure function: no network, no mutation."""
    old_by_key = {}
    for r in old_records:
        old_by_key.setdefault(_event_key(r), r)
    new_by_key = {}
    for r in new_records:
        new_by_key.setdefault(_event_key(r), r)
    changed, added, removed = [], [], []
    for k, new_r in new_by_key.items():
        old_r = old_by_key.get(k)
        if old_r is None:
            added.append({"event_key": k,
                          "ticker": new_r.get("ticker") or ""})
            continue
        diffs = {}
        for f in TIMING_FIELDS:
            o, n = (old_r.get(f) or ""), (new_r.get(f) or "")
            if o != n:
                diffs[f] = (o, n)
        if diffs:
            changed.append({"event_key": k,
                            "ticker": new_r.get("ticker") or "",
                            "changes": diffs})
    for k, old_r in old_by_key.items():
        if k not in new_by_key:
            removed.append({"event_key": k,
                            "ticker": old_r.get("ticker") or ""})
    return {"changed": changed, "added": added, "removed": removed}


def check_scorer_version(artifact_version):
    """C5: refuse when an artifact was produced by a different scorer version.
    Raises SampleIntegrityError on mismatch. Never caught silently."""
    if artifact_version != SCORER_VERSION:
        raise SampleIntegrityError(
            f"scorer_version mismatch: artifact={artifact_version!r} "
            f"harness={SCORER_VERSION!r} -- the scorer changed since this "
            f"artifact was produced; re-freeze under a new amendment")
    return True


# ---------------------------------------------------------------- C4: evidence precedence (precommitted)

EVIDENCE_PRECEDENCE = (
    "1. Company IR press-release timestamp (highest authority)",
    "2. Newswire timestamp (Business Wire / PR Newswire)",
    "3. NYSE official calendar: that day's actual regular-session open/close "
    "(early closes honored)",
    "4. Intrinio/Zacks vendor fields (lowest authority -- the data under audit)",
)
EVIDENCE_CONFLICT_RULES = (
    "Conflicts between (1) and (2) resolve to the earliest published timestamp.",
    "Vendor timing code (BTO/DTM/AMC) disagreeing with the timestamp-derived "
    "bucket -> ambiguous -> EXCLUDE per frozen Amendment section 1.",
    "Missing, ambiguous, or vendor-imputed timing -> EXCLUDE. "
    "Timing is never imputed.",
)


# ---------------------------------------------------------------- C1/C2: hashing

def _canonical(obj):
    """Canonical JSON: sorted keys, no whitespace. Deterministic for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def compute_raw_hash(records):
    """C2: SHA-256 over the canonical raw vendor record payload."""
    return hashlib.sha256(_canonical(records).encode("utf-8")).hexdigest()


def check_raw_integrity(payload):
    """C2: verify a fetch payload's raw_hash. Returns (True, '') or (False, reason)."""
    stored = payload.get("raw_hash")
    if not stored:
        return (False, "no raw_hash present -- refetch with the current harness")
    actual = compute_raw_hash(payload.get("records") or [])
    if actual != stored:
        return (False, "raw_hash mismatch -- vendor data modified after fetch")
    return (True, "")


ROW_VENDOR_FIELDS = ("event_id", "ticker", "intrinio_reported_date",
                     "intrinio_reported_time", "intrinio_code", "derived_bucket")


def _row_projection(row):
    return {k: row.get(k, "") for k in ROW_VENDOR_FIELDS}


def compute_sample_hash(rows):
    """C1: SHA-256 over the canonical vendor-field projection of each row."""
    h = hashlib.sha256()
    for row in rows:
        h.update(_canonical(_row_projection(row)).encode("utf-8"))
    return h.hexdigest()


def verify_sample_hash(rows, stored_hash):
    """C1: recompute and compare. Raises SampleIntegrityError on any mismatch."""
    if not stored_hash:
        raise SampleIntegrityError(
            "no sample_hash stored -- sample predates integrity controls")
    actual = compute_sample_hash(rows)
    if actual != stored_hash:
        raise SampleIntegrityError(
            "sample_hash mismatch: stored=%s... actual=%s... -- the sample "
            "was tampered with or substituted after the draw"
            % (stored_hash[:16], actual[:16]))
    return True


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
    """Qualifying = parseable reported date AND a reported time AND a known
    timing code. A record with missing actual_reported_time cannot have its
    time verified against primary sources, so it is not qualifying."""
    d = rec.get("actual_reported_date") or ""
    t = rec.get("actual_reported_time") or ""
    code = (rec.get("actual_reported_code") or "").upper()
    if len(d) < 10 or d[4] != "-" or d[7] != "-":
        return False
    if not t.strip():
        return False
    return code in CODE_TO_BUCKET


def draw_sample(records, seed):
    """
    Deterministic stratified draw honoring the frozen strata:
      50 events, >=10 BMO (BTO), >=10 AMC, >=8 distinct calendar years.

    The retry loop (seed, seed+1, ...) exists ONLY to satisfy the frozen
    strata; the seed actually used is committed in the output. Re-running
    with a different seed after seeing the draw -- e.g. to dodge
    inconvenient events -- is prohibited: the output is final (see C3).

    Returns (sample_records, seed_used).
    """
    qualifying = [r for r in records if _is_qualifying(r)]
    # C6: one event = one slot. Drop duplicate vendor rows (same ticker+date)
    # before stratification; duplicates are reported, never silently kept.
    qualifying, n_dupes = dedupe_records(qualifying)
    if n_dupes:
        print(f"removed {n_dupes} duplicate vendor rows (same ticker+date)",
              file=sys.stderr)
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


def _sheet_header_lines(sample_hash, scorer_version):
    """C4: precedence block committed BEFORE any human examines evidence."""
    lines = [
        "# ERD v0.1 timing-audit verification sheet -- human verification worksheet",
        f"# sample_hash: {sample_hash}",
        f"# scorer_version: {scorer_version}",
        "#",
        "# EVIDENCE PRECEDENCE (precommitted; do not reorder during verification):",
    ]
    lines += [f"# {p}" for p in EVIDENCE_PRECEDENCE]
    lines.append("# Conflict rules:")
    lines += [f"# {r}" for r in EVIDENCE_CONFLICT_RULES]
    lines += [
        "#",
        "# NO-REPLACEMENT RULE (C3): the 50 sampled events are final. A sampled",
        "# event that turns out missing/ambiguous is scored as a non-match and",
        "# counts against coverage per the frozen rules. It is NEVER replaced",
        "# with a convenient substitute. No code path exists that swaps events.",
        "#",
    ]
    return lines


def write_sheet(rows, path, sample_hash, scorer_version=SCORER_VERSION):
    with open(path, "w", newline="", encoding="utf-8") as f:
        for line in _sheet_header_lines(sample_hash, scorer_version):
            f.write(line + "\n")
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")


def _read_sheet(path):
    """Read a verification sheet: returns (sample_hash, scorer_version, rows)."""
    sample_hash = None
    scorer_version = None
    with open(path, newline="", encoding="utf-8") as f:
        body = [ln for ln in f if not ln.lstrip().startswith("#")]
    # recover the hash and version from the comment lines separately
    with open(path, encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if s.startswith("# sample_hash:"):
                sample_hash = s.split(":", 1)[1].strip()
            elif s.startswith("# scorer_version:"):
                scorer_version = s.split(":", 1)[1].strip()
    rows = list(csv.DictReader(body))
    return sample_hash, scorer_version, rows


# ---------------------------------------------------------------- score

def _valid_bucket(v):
    return (v or "").strip().upper() in VALID_BUCKETS


def score_sheet(path):
    # C1: the vendor columns must still hash to the committed sample_hash.
    # Any edit to a vendor field after the draw -> refusal.
    # C5: the sheet must have been built by this exact scorer version.
    stored_hash, artifact_version, rows = _read_sheet(path)
    check_scorer_version(artifact_version)
    verify_sample_hash(rows, stored_hash)

    n = len(rows)
    filled = [r for r in rows if (r.get("date_bucket_match_YN") or "").strip().upper() in ("Y", "N")]
    # C3: a row counts as a match ONLY with Y AND a valid verified bucket.
    # Rows without a valid verified_bucket (missing/ambiguous timing) are
    # non-matches -- never replaced, never excused.
    matches = sum(1 for r in filled
                  if (r.get("date_bucket_match_YN") or "").strip().upper() == "Y"
                  and _valid_bucket(r.get("verified_bucket")))
    bmo = sum(1 for r in rows if (r.get("verified_bucket") or "").strip().upper() == "BMO")
    amc = sum(1 for r in rows if (r.get("verified_bucket") or "").strip().upper() == "AMC")
    years = { (r.get("verified_date") or "")[:4] for r in filled
              if len(r.get("verified_date") or "") >= 4 }
    years.discard("")
    # Row-level coverage proxy: fraction of sampled events with a valid
    # verified timing classification. (Full-window coverage per the amendment
    # also needs the universe pull; reported separately.)
    valid_timing = sum(1 for r in rows if _valid_bucket(r.get("verified_bucket")))
    coverage = (valid_timing / n) if n else 0.0

    # Revision-pattern screen: count mismatches by direction.
    mismatch_dirs = {}
    for r in filled:
        is_match = ((r.get("date_bucket_match_YN") or "").strip().upper() == "Y"
                    and _valid_bucket(r.get("verified_bucket")))
        if not is_match:
            key = (f"intrinio={r.get('intrinio_reported_date')}/{r.get('intrinio_code')}"
                   f" vs verified={r.get('verified_date')}/{r.get('verified_bucket')}")
            mismatch_dirs[key] = mismatch_dirs.get(key, 0) + 1

    unfilled = n - len(filled)
    verdict = "INCOMPLETE"
    if unfilled == 0:
        verdict = ("PASS" if (matches >= PASS_MATCHES and coverage >= PASS_COVERAGE)
                   else "FAIL")

    report = {
        "scorer_version": SCORER_VERSION,
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


# ---------------------------------------------------------------- verify

def verify_file(path):
    """C2: re-hash a fetch file's raw payload. Returns (status, reason)."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    ok, reason = check_raw_integrity(payload)
    return ("OK", "") if ok else ("TAMPERED", reason)


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description="ERD 50-event timing-integrity audit harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="pull Zacks EPS Surprises from Intrinio")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("verify", help="re-hash a fetch file: OK or TAMPERED")
    p.add_argument("--in", dest="inp", required=True)

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
        payload = {"start": args.start, "end": args.end,
                   "n": len(recs),
                   "raw_hash": compute_raw_hash(recs),  # C2
                   "records": recs}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        print(f"saved {len(recs)} records (raw_hash {payload['raw_hash'][:16]}...) -> {args.out}")

    elif args.cmd == "verify":
        status, reason = verify_file(args.inp)
        print(status + (f": {reason}" if reason else ""))
        sys.exit(0 if status == "OK" else 1)

    elif args.cmd == "sample":
        with open(args.inp, encoding="utf-8") as f:
            payload = json.load(f)
        ok, reason = check_raw_integrity(payload)  # C2: refuse on tampered raw
        if not ok:
            sys.exit(f"REFUSING to sample: {reason}")
        sample, seed_used = draw_sample(payload["records"], args.seed)
        rows = [to_audit_row(r, i) for i, r in enumerate(sample)]
        sample_hash = compute_sample_hash(rows)  # C1: hash BEFORE evidence
        out = {"seed_requested": args.seed, "seed_used": seed_used,
               "scorer_version": SCORER_VERSION,  # C5: frozen scorer identity
               "sample_hash": sample_hash,
               "raw_hash_verified": payload.get("raw_hash"),
               "n": len(rows), "rows": rows,
               "source_window": {k: payload[k] for k in ("start", "end") if k in payload}}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"drew {len(rows)} events (seed {seed_used}, "
              f"sample_hash {sample_hash[:16]}...) -> {args.out}")

    elif args.cmd == "sheet":
        with open(args.inp, encoding="utf-8") as f:
            payload = json.load(f)
        try:
            check_scorer_version(payload.get("scorer_version"))  # C5
            verify_sample_hash(payload["rows"], payload.get("sample_hash"))  # C1
        except SampleIntegrityError as e:
            sys.exit(f"REFUSING to build sheet: {e}")
        write_sheet(payload["rows"], args.out, payload["sample_hash"],
                    payload.get("scorer_version") or SCORER_VERSION)

    elif args.cmd == "score":
        try:
            score_sheet(args.inp)
        except SampleIntegrityError as e:
            sys.exit(f"REFUSING to score: {e}")


if __name__ == "__main__":
    main()
