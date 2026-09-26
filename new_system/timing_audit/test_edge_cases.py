"""
Synthetic edge-case tests for the ERD 50-event timing-audit harness.

stdlib unittest only. No network, no API keys, no performance data.
Covers the reviewer-mandated controls (ChatGPT PASS decision, 2026-09-25):
  - frozen event-clock vectors (Amendment section 1, incl. the required
    synthetic vectors and the early-close case)
  - DST weekends, exact-close timestamps, code/timestamp conflicts,
    missing timing, ticker identity, raw-data tampering, sample-hash
    tampering, and the no-replacement scoring rule.
  - C5 scorer-version freeze: version embedded in sample/sheet/score;
    cross-version artifacts refused.
  - C6 duplicates and vendor revisions: one event = one sample slot;
    restated timing fields between pulls are flagged for the gate's
    systematic-revision screen.
  - gate scope: no return/price/P&L fields may enter the audit artifacts.

Run:  python3 -m unittest test_edge_cases -v   (from new_system/timing_audit/)
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit_harness as H
from audit_harness import (
    SampleIntegrityError,
    SCORER_VERSION,
    EVIDENCE_PRECEDENCE,
    EVIDENCE_CONFLICT_RULES,
    check_raw_integrity,
    check_scorer_version,
    compute_raw_hash,
    compute_sample_hash,
    dedupe_records,
    detect_vendor_revisions,
    draw_sample,
    to_audit_row,
    verify_file,
    verify_sample_hash,
    write_sheet,
    score_sheet,
    _is_qualifying,
    _read_sheet,
)
from event_clock import classify_release, EXCLUDE

ET = ZoneInfo("America/New_York")
OPEN = time(9, 30)
CLOSE = time(16, 0)
EARLY_CLOSE = time(13, 0)


def rec(ticker, d, t, code):
    return {"ticker": ticker, "actual_reported_date": d,
            "actual_reported_time": t, "actual_reported_code": code}


def fake_pool(n=120):
    """Synthetic qualifying pool: 9 years, all three codes, all with times."""
    codes = ["BTO", "AMC", "DTM"]
    times = {"BTO": "08:00", "AMC": "17:30", "DTM": "12:00"}
    out = []
    for i in range(n):
        code = codes[i % 3]
        year = 2018 + (i % 9)
        out.append(rec(f"T{i:03d}", f"{year}-03-15", times[code], code))
    return out


def fake_fetch_payload(n=120):
    records = fake_pool(n)
    return {"start": "2018-01-01", "end": "2026-06-30", "n": n,
            "raw_hash": compute_raw_hash(records), "records": records}


def sample_rows(payload, seed=20260925):
    sample, seed_used = draw_sample(payload["records"], seed)
    rows = [to_audit_row(r, i) for i, r in enumerate(sample)]
    return rows, seed_used


# ---------------------------------------------------------------- event clock

class TestEventClockFrozenVectors(unittest.TestCase):
    """Exact synthetic vectors required by frozen Amendment section 1."""

    def test_normal_day_vectors(self):
        d = date(2026, 9, 24)  # Thursday
        nxt = date(2026, 9, 25)
        dt = lambda h, m: datetime(2026, 9, 24, h, m)  # naive = ET
        self.assertEqual(classify_release(dt(8, 59), OPEN, CLOSE, nxt), ("S", d))
        self.assertEqual(classify_release(dt(9, 30), OPEN, CLOSE, nxt)[0], EXCLUDE)
        self.assertEqual(classify_release(dt(12, 0), OPEN, CLOSE, nxt)[0], EXCLUDE)
        self.assertEqual(classify_release(dt(15, 59), OPEN, CLOSE, nxt)[0], EXCLUDE)
        self.assertEqual(classify_release(dt(16, 1), OPEN, CLOSE, nxt), ("S", nxt))

    def test_saturday_goes_to_next_session(self):
        sat = datetime(2026, 9, 26, 10, 0)
        mon = date(2026, 9, 28)
        self.assertEqual(
            classify_release(sat, None, None, mon, is_trading_day=False), ("S", mon))

    def test_early_close_vectors(self):
        # Required early-close case: 13:00 ET close.
        d = date(2026, 11, 25)  # Wednesday (day after Thanksgiving pattern)
        nxt = date(2026, 11, 27)
        dt = lambda h, m: datetime(2026, 11, 25, h, m)
        self.assertEqual(
            classify_release(dt(8, 59), OPEN, EARLY_CLOSE, nxt), ("S", d))
        self.assertEqual(
            classify_release(dt(12, 59), OPEN, EARLY_CLOSE, nxt)[0], EXCLUDE)
        self.assertEqual(
            classify_release(dt(13, 0), OPEN, EARLY_CLOSE, nxt)[0], EXCLUDE)  # exact close
        self.assertEqual(
            classify_release(dt(13, 1), OPEN, EARLY_CLOSE, nxt), ("S", nxt))

    def test_exact_close_is_exclude_normal_day(self):
        d = date(2026, 9, 24)
        nxt = date(2026, 9, 25)
        verdict, reason = classify_release(datetime(2026, 9, 24, 16, 0),
                                           OPEN, CLOSE, nxt)
        self.assertEqual(verdict, EXCLUDE)


class TestEventClockDST(unittest.TestCase):
    def test_spring_forward_weekend(self):
        # 2026-03-08 is the spring-forward Sunday.
        sun = datetime(2026, 3, 8, 10, 0, tzinfo=ET)
        mon = date(2026, 3, 9)
        self.assertEqual(
            classify_release(sun, None, None, mon, is_trading_day=False), ("S", mon))

    def test_fall_back_weekend(self):
        # 2026-11-01 is the fall-back Sunday.
        sun = datetime(2026, 11, 1, 10, 0, tzinfo=ET)
        mon = date(2026, 11, 2)
        self.assertEqual(
            classify_release(sun, None, None, mon, is_trading_day=False), ("S", mon))

    def test_tz_aware_trading_day(self):
        # Friday before spring-forward; tz-aware ET wall time must classify.
        d = date(2026, 3, 6)
        nxt = date(2026, 3, 9)
        fri = datetime(2026, 3, 6, 8, 59, tzinfo=ET)
        self.assertEqual(classify_release(fri, OPEN, CLOSE, nxt), ("S", d))
        fri2 = datetime(2026, 3, 6, 16, 1, tzinfo=ET)
        self.assertEqual(classify_release(fri2, OPEN, CLOSE, nxt), ("S", nxt))


class TestEventClockAmbiguity(unittest.TestCase):
    def test_missing_timing_excluded(self):
        self.assertEqual(
            classify_release(None, OPEN, CLOSE, date(2026, 9, 25))[0], EXCLUDE)

    def test_code_timestamp_disagreement_excluded(self):
        d = date(2026, 9, 24)
        nxt = date(2026, 9, 25)
        # Noon is DTM; a BTO code disagrees -> ambiguous -> EXCLUDE.
        v, r = classify_release(datetime(2026, 9, 24, 12, 0), OPEN, CLOSE, nxt,
                                vendor_code="BTO")
        self.assertEqual(v, EXCLUDE)
        self.assertIn("ambiguous", r)
        # 08:59 is BMO; an AMC code disagrees -> EXCLUDE.
        v, _ = classify_release(datetime(2026, 9, 24, 8, 59), OPEN, CLOSE, nxt,
                                vendor_code="AMC")
        self.assertEqual(v, EXCLUDE)

    def test_code_timestamp_agreement_ok(self):
        d = date(2026, 9, 24)
        nxt = date(2026, 9, 25)
        self.assertEqual(
            classify_release(datetime(2026, 9, 24, 8, 59), OPEN, CLOSE, nxt,
                             vendor_code="BTO"), ("S", d))
        self.assertEqual(
            classify_release(datetime(2026, 9, 24, 17, 30), OPEN, CLOSE, nxt,
                             vendor_code="AMC"), ("S", nxt))

    def test_unknown_code_excluded(self):
        v, _ = classify_release(datetime(2026, 9, 24, 8, 59), OPEN, CLOSE,
                                date(2026, 9, 25), vendor_code="XYZ")
        self.assertEqual(v, EXCLUDE)


# ---------------------------------------------------------------- sample hash (C1)

class TestSampleHash(unittest.TestCase):
    def test_hash_deterministic(self):
        payload = fake_fetch_payload()
        rows1, _ = sample_rows(payload)
        rows2, _ = sample_rows(payload)
        self.assertEqual(compute_sample_hash(rows1), compute_sample_hash(rows2))

    def test_hash_tamper_evident(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h1 = compute_sample_hash(rows)
        tampered = [dict(r) for r in rows]
        tampered[0]["intrinio_reported_date"] = "1999-01-01"
        self.assertNotEqual(h1, compute_sample_hash(tampered))
        with self.assertRaises(SampleIntegrityError):
            verify_sample_hash(tampered, h1)

    def test_ticker_change_changes_hash(self):
        # Record identity is bound to the sampled fields: a ticker change
        # (e.g. symbol change) is detectable, not silently absorbed.
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h1 = compute_sample_hash(rows)
        changed = [dict(r) for r in rows]
        changed[5]["ticker"] = changed[5]["ticker"] + "X"
        self.assertNotEqual(h1, compute_sample_hash(changed))

    def test_empty_ticker_no_crash(self):
        # Delisted / missing ticker: still processes deterministically.
        records = fake_pool()
        records[0]["ticker"] = ""
        sample, _ = draw_sample(records, 20260925)
        rows = [to_audit_row(r, i) for i, r in enumerate(sample)]
        h = compute_sample_hash(rows)
        self.assertTrue(verify_sample_hash(rows, h))

    def test_sheet_refuses_tampered_sample(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        tampered = [dict(r) for r in rows]
        # guarantee a real change regardless of the row's original code
        tampered[3]["intrinio_code"] = (
            "AMC" if tampered[3]["intrinio_code"] != "AMC" else "BTO")
        with self.assertRaises(SampleIntegrityError):
            verify_sample_hash(tampered, h)


# ---------------------------------------------------------------- raw immutability (C2)

class TestRawImmutability(unittest.TestCase):
    def test_verify_ok(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump(fake_fetch_payload(), f)
            path = f.name
        try:
            status, reason = verify_file(path)
            self.assertEqual(status, "OK")
            self.assertEqual(reason, "")
        finally:
            os.unlink(path)

    def test_verify_tampered(self):
        payload = fake_fetch_payload()
        payload["records"][10]["actual_reported_date"] = "1999-12-31"
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump(payload, f)
            path = f.name
        try:
            status, reason = verify_file(path)
            self.assertEqual(status, "TAMPERED")
            self.assertIn("mismatch", reason)
        finally:
            os.unlink(path)

    def test_sample_flow_refuses_tampered_raw(self):
        payload = fake_fetch_payload()
        payload["records"][10]["actual_reported_time"] = "00:00"
        ok, reason = check_raw_integrity(payload)
        self.assertFalse(ok)

    def test_missing_raw_hash_refused(self):
        payload = fake_fetch_payload()
        del payload["raw_hash"]
        ok, reason = check_raw_integrity(payload)
        self.assertFalse(ok)
        self.assertIn("no raw_hash", reason)


# ---------------------------------------------------------------- sheet/score hash gates

def _write_tmp_sheet(rows, sample_hash):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    write_sheet(rows, path, sample_hash)
    return path


def _tamper_csv_vendor_cell(path):
    """Change one vendor date cell in the CSV data section (not comments)."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.startswith("#") or ln.startswith("event_id"):
            continue
        parts = ln.rstrip("\n").split(",")
        parts[2] = "1999-01-01"  # intrinio_reported_date column
        lines[i] = ",".join(parts) + "\n"
        break
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


class TestSheetScoreGates(unittest.TestCase):
    def test_score_refuses_tampered_vendor_field(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        path = _write_tmp_sheet(rows, h)
        try:
            _tamper_csv_vendor_cell(path)
            with self.assertRaises(SampleIntegrityError):
                score_sheet(path)
        finally:
            os.unlink(path)

    def test_score_refuses_missing_hash_header(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=H.SHEET_FIELDS)
                w.writeheader()
                w.writerows(rows)
            with self.assertRaises(SampleIntegrityError):
                score_sheet(path)
        finally:
            os.unlink(path)

    def test_round_trip_no_substitution(self):
        # sample -> sheet -> read back: vendor columns must equal the drawn rows.
        payload = fake_fetch_payload()
        self.assertTrue(check_raw_integrity(payload)[0])
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        path = _write_tmp_sheet(rows, h)
        try:
            stored, version, back = _read_sheet(path)
            self.assertEqual(stored, h)
            self.assertEqual(version, SCORER_VERSION)
            self.assertTrue(verify_sample_hash(back, stored))
            for orig, rt in zip(rows, back):
                for k in ("event_id", "ticker", "intrinio_reported_date",
                          "intrinio_reported_time", "intrinio_code",
                          "derived_bucket"):
                    self.assertEqual(orig[k], rt[k], f"field {k} changed in pipeline")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------- C3: no replacement

class TestNoReplacementRule(unittest.TestCase):
    def _filled_sheet(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        rows = rows[:3]
        h = compute_sample_hash(rows)
        # row0: clean match; row1: clean non-match; row2: Y but NO valid bucket
        # (missing/ambiguous timing) -> must count as non-match, never replaced.
        rows[0].update(verified_bucket="BMO", verified_date="2020-03-15",
                       verified_time="08:00", date_bucket_match_YN="Y")
        rows[1].update(verified_bucket="AMC", verified_date="2021-03-15",
                       verified_time="17:30", date_bucket_match_YN="N")
        rows[2].update(verified_bucket="", verified_date="", verified_time="",
                       date_bucket_match_YN="Y",
                       notes="primary source not found -- ambiguous")
        path = _write_tmp_sheet(rows, h)
        return path

    def test_missing_bucket_is_nonmatch(self):
        path = self._filled_sheet()
        try:
            report = score_sheet(path)
            self.assertEqual(report["exact_date_bucket_matches"], 1)
            self.assertEqual(report["n_scored"], 3)
            # coverage counts only rows with a valid verified bucket: 2/3
            self.assertAlmostEqual(report["coverage_proxy"], 2 / 3, places=4)
        finally:
            os.unlink(path)

    def test_no_swap_code_path(self):
        # The harness exposes no function that mutates or replaces drawn rows.
        for name in dir(H):
            self.assertNotIn("replace", name.lower())
            self.assertNotIn("resample", name.lower())
            self.assertNotIn("swap", name.lower())


# ---------------------------------------------------------------- qualification

class TestQualification(unittest.TestCase):
    def test_missing_time_not_qualifying(self):
        self.assertFalse(_is_qualifying(rec("A", "2020-03-15", "", "BTO")))
        self.assertFalse(_is_qualifying(rec("A", "2020-03-15", "   ", "AMC")))
        r = rec("A", "2020-03-15", None, "BTO")
        self.assertFalse(_is_qualifying(r))

    def test_bad_date_not_qualifying(self):
        self.assertFalse(_is_qualifying(rec("A", "not-a-date", "08:00", "BTO")))
        self.assertFalse(_is_qualifying(rec("A", "", "08:00", "BTO")))

    def test_unknown_code_not_qualifying(self):
        self.assertFalse(_is_qualifying(rec("A", "2020-03-15", "08:00", "XYZ")))

    def test_good_record_qualifying(self):
        self.assertTrue(_is_qualifying(rec("A", "2020-03-15", "08:00", "BTO")))
        self.assertTrue(_is_qualifying(rec("A", "2020-03-15", "17:30", "AMC")))
        self.assertTrue(_is_qualifying(rec("A", "2020-03-15", "12:00", "DTM")))

    def test_missing_time_excluded_from_pool(self):
        records = fake_pool()
        for r in records[:20]:
            r["actual_reported_time"] = ""
        sample, _ = draw_sample(records, 20260925)
        for r in sample:
            self.assertTrue((r.get("actual_reported_time") or "").strip())


# ---------------------------------------------------------------- C4: precedence

class TestEvidencePrecedence(unittest.TestCase):
    def test_four_levels_vendor_last(self):
        self.assertEqual(len(EVIDENCE_PRECEDENCE), 4)
        self.assertIn("IR press-release", EVIDENCE_PRECEDENCE[0])
        self.assertIn("Newswire", EVIDENCE_PRECEDENCE[1])
        self.assertIn("NYSE", EVIDENCE_PRECEDENCE[2])
        self.assertIn("Intrinio/Zacks", EVIDENCE_PRECEDENCE[3])
        self.assertTrue(EVIDENCE_CONFLICT_RULES)

    def test_sheet_embeds_precedence(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        path = _write_tmp_sheet(rows[:2], h)
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(2000)
            self.assertIn("EVIDENCE PRECEDENCE", head)
            self.assertIn("sample_hash", head)
            self.assertIn("NO-REPLACEMENT RULE", head)
            for level in EVIDENCE_PRECEDENCE:
                self.assertIn(level.split(". ", 1)[1][:20], head)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------- C5: scorer version freeze

class TestScorerVersionFreeze(unittest.TestCase):
    def test_version_constant_present(self):
        self.assertEqual(H.SCORER_VERSION, "1.0.0")

    def test_sheet_carries_version(self):
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        path = _write_tmp_sheet(rows[:2], h)
        try:
            _, version, _ = _read_sheet(path)
            self.assertEqual(version, SCORER_VERSION)
        finally:
            os.unlink(path)

    def test_check_scorer_version_ok_and_refusal(self):
        self.assertTrue(check_scorer_version(SCORER_VERSION))
        with self.assertRaises(SampleIntegrityError):
            check_scorer_version("2.0.0")
        with self.assertRaises(SampleIntegrityError):
            check_scorer_version(None)

    def test_score_refuses_version_mismatch(self):
        # A sheet built by a different scorer version must not score.
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            write_sheet(rows, path, h, scorer_version="0.9.0")
            with self.assertRaises(SampleIntegrityError):
                score_sheet(path)
        finally:
            os.unlink(path)

    def test_score_refuses_missing_version(self):
        # Sheets predating version control (no header line) are refused.
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        path = _write_tmp_sheet(rows[:2], h)
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            content = "\n".join(
                ln for ln in content.splitlines()
                if not ln.startswith("# scorer_version:"))
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            with self.assertRaises(SampleIntegrityError):
                score_sheet(path)
        finally:
            os.unlink(path)

    def test_version_in_score_report(self):
        # End-to-end: a fully filled sheet scores and reports the version.
        payload = fake_fetch_payload()
        rows, _ = sample_rows(payload)
        h = compute_sample_hash(rows)
        for r in rows:
            r["verified_date"] = r["intrinio_reported_date"]
            r["verified_time"] = r["intrinio_reported_time"]
            r["verified_bucket"] = r["derived_bucket"]
            r["date_bucket_match_YN"] = "Y"
        path = _write_tmp_sheet(rows, h)
        try:
            report = score_sheet(path)
            self.assertEqual(report["scorer_version"], SCORER_VERSION)
            self.assertEqual(report["verdict"], "PASS")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------- C6: duplicates and vendor revisions

class TestDuplicatesAndRevisions(unittest.TestCase):
    def test_exact_duplicates_collapse_and_count(self):
        a = rec("AAA", "2020-03-15", "08:00", "BTO")
        b = rec("AAA", "2020-03-15", "08:00", "BTO")  # exact duplicate
        d = rec("BBB", "2020-03-15", "08:00", "BTO")
        unique, n_exact, conflicts = dedupe_records([a, b, d])
        self.assertEqual(n_exact, 1)
        self.assertEqual(conflicts, [])
        self.assertEqual(len(unique), 2)
        self.assertEqual(unique[0]["actual_reported_time"], "08:00")

    def test_conflicting_duplicates_flagged_not_collapsed(self):
        a = rec("AAA", "2020-03-15", "08:00", "BTO")
        c = rec("AAA", "2020-03-15", "17:30", "AMC")  # same event, disagrees
        unique, n_exact, conflicts = dedupe_records([a, c])
        self.assertEqual(n_exact, 0)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["ticker"], "AAA")
        self.assertEqual(len(conflicts[0]["rows"]), 2)
        self.assertEqual(unique, [])  # conflicted event takes no slot

    def test_draw_sample_refuses_conflicting_duplicates(self):
        pool = fake_pool(120)
        bad = rec(pool[0]["ticker"], pool[0]["actual_reported_date"],
                  "23:59", "AMC")  # same event, conflicting timing
        with self.assertRaises(SampleIntegrityError):
            draw_sample(pool + [bad], 20260925)

    def test_draw_sample_tolerates_exact_duplicates(self):
        pool = fake_pool(120)
        pool = pool + [dict(r) for r in pool[:10]]  # inject exact duplicates
        sample, _ = draw_sample(pool, 20260925)
        keys = [((r.get("ticker") or "").upper(),
                 r.get("actual_reported_date")) for r in sample]
        self.assertEqual(len(sample), 50)
        self.assertEqual(len(keys), len(set(keys)))

    def test_vendor_revision_detected(self):
        old = [rec("AAA", "2020-03-15", "08:00", "BTO"),
               rec("BBB", "2020-03-15", "17:30", "AMC")]
        new = [rec("AAA", "2020-03-15", "08:05", "BTO"),   # restated time
               rec("BBB", "2020-03-15", "17:30", "AMC"),
               rec("CCC", "2020-03-15", "08:00", "BTO")]   # added
        diff = detect_vendor_revisions(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        ch = diff["changed"][0]
        self.assertEqual(ch["ticker"], "AAA")
        self.assertEqual(ch["changes"]["actual_reported_time"],
                         ("08:00", "08:05"))
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["added"][0]["ticker"], "CCC")
        self.assertEqual(diff["removed"], [])

    def test_vendor_revision_removed_reported(self):
        old = [rec("AAA", "2020-03-15", "08:00", "BTO")]
        diff = detect_vendor_revisions(old, [])
        self.assertEqual(len(diff["removed"]), 1)
        self.assertEqual(diff["removed"][0]["ticker"], "AAA")
        self.assertEqual(diff["changed"], [])

    def test_vendor_revision_none_when_identical(self):
        pool = fake_pool(40)
        diff = detect_vendor_revisions(pool, [dict(r) for r in pool])
        self.assertEqual(diff, {"changed": [], "added": [], "removed": []})

    def test_revision_code_change_flagged(self):
        old = [rec("AAA", "2020-03-15", "08:00", "BTO")]
        new = [rec("AAA", "2020-03-15", "08:00", "AMC")]
        diff = detect_vendor_revisions(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        self.assertIn("actual_reported_code", diff["changed"][0]["changes"])

    def test_revision_match_uses_stable_security_id_across_ticker_change(self):
        # Same company, ticker changed between pulls: must read as a revision,
        # not as a removed+added event.
        old = [{"security": {"id": "SEC123", "ticker": "AAA"},
                "ticker": "AAA",
                "actual_reported_date": "2020-03-15",
                "actual_reported_time": "08:00",
                "actual_reported_code": "BTO"}]
        new = [{"security": {"id": "SEC123", "ticker": "AAANEW"},
                "ticker": "AAANEW",
                "actual_reported_date": "2020-03-15",
                "actual_reported_time": "08:05",
                "actual_reported_code": "BTO"}]
        diff = detect_vendor_revisions(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        self.assertEqual(diff["changed"][0]["key_type"], "security_id")
        self.assertEqual(diff["changed"][0]["changes"]["actual_reported_time"],
                         ("08:00", "08:05"))
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])

    def test_revision_falls_back_to_ticker_date_without_stable_id(self):
        # No security id on either side: documented ticker+date fallback.
        old = [rec("AAA", "2020-03-15", "08:00", "BTO")]
        new = [rec("AAA", "2020-03-15", "08:05", "BTO")]
        diff = detect_vendor_revisions(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        self.assertEqual(diff["changed"][0]["key_type"], "ticker_fallback")


# ---------------------------------------------------------------- gate scope: no returns enter this audit

class TestNoReturnsInAudit(unittest.TestCase):
    RETURN_LIKE = ("return", "price", "pnl", "p&l", "profit")

    def _assert_no_return_like(self, names):
        lowered = [n.lower() for n in names]
        bad = [n for n in lowered
               if any(tok in n for tok in self.RETURN_LIKE)]
        self.assertEqual(bad, [], f"return-like fields leaked into the audit: {bad}")

    def test_sheet_fields_have_no_return_like_columns(self):
        self._assert_no_return_like(H.SHEET_FIELDS)

    def test_audit_row_has_no_return_like_fields(self):
        row = to_audit_row(rec("AAA", "2020-03-15", "08:00", "BTO"), 0)
        self._assert_no_return_like(row.keys())


if __name__ == "__main__":
    unittest.main(verbosity=2)
