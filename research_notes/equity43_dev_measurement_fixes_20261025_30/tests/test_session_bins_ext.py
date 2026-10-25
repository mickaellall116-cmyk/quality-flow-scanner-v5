"""30 fixtures for the session-table EXTENSION + union loader (P8
calendar-horizon repair).

Run: python3 tests/test_session_bins_ext.py  (exit 0 = all hold)

The adopted 751-session base table is byte-untouched (its sha is
re-verified here, not trusted); the extension is a separate
hash-pinned artifact (303 sessions, 2026-10-19..2027-12-31) built
from the NYSE published calendar by code/build_session_extension.py.
The union (1054 sessions) accepts the Oct 26-30 2026 pilot week and
the declared horizon, and still fails closed on holidays, on the
extension's own early closes' phantom bins, and on every date past
2027-12-31 — no extrapolation.
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import session_bins as sb  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def expect_refusal(name, fn, needle=""):
    try:
        fn()
    except sb.SessionTableError as e:
        check(name, needle in str(e), f"({e})")
        return
    check(name, False, "no SessionTableError raised")


def main():
    # The base table is byte-untouched by this lane.
    raw = open(sb.default_table_path(), "rb").read()
    check("base table bytes unchanged (sha 00c5555c…)",
          hashlib.sha256(raw).hexdigest() == sb.PINNED_TABLE_SHA256)
    base = sb.load_pinned_table()
    check("base loader still yields exactly the 751 adopted sessions",
          len(base) == 751)

    ext = sb.load_extension_table()
    check("extension loads (sha verified), 303 sessions",
          len(ext) == 303, f"n={len(ext)}")
    doc = json.load(open(sb.default_extension_path()))
    check("extension provenance: artifact id + parent pin recorded",
          doc["artifact"] == "XNYS_SESSION_TABLE_EXTENSION_2027"
          and doc["extends"]["sha256"] == sb.PINNED_TABLE_SHA256)
    check("extension provenance: horizon + cross-checks recorded",
          doc["horizon"]["declared"] == "2026-10-19..2027-12-31"
          and doc["cross_checks"]["X2_exchange_calendars"]
          ["date_mismatches"] == []
          and doc["cross_checks"]["X3_published_counts"]
          ["sessions_2027"] == 251)
    ext_dates = {r["date"] for r in doc["sessions"]}
    base_dates = {r["date"] for r in json.loads(raw)["sessions"]}
    check("base and extension are disjoint",
          not (ext_dates & base_dates))
    check("extension spans exactly the declared horizon",
          min(ext_dates) == "2026-10-19"
          and max(ext_dates) == "2027-12-31")

    u = sb.load_union_table()
    check("union loads: 751 + 303 = 1054 sessions", len(u) == 1054,
          f"n={len(u)}")

    # The pilot week (Oct 26-30 2026, EDT): regular bins resolve.
    for d in ("2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29",
              "2026-10-30"):
        e1 = u.bin_end(f"{d}T09:30:00-04:00")
        e2 = u.bin_end(f"{d}T13:30:00-04:00")
        check(f"pilot week {d}: bins end 13:30 / 16:00 -04:00",
              e1.isoformat() == f"{d}T13:30:00-04:00"
              and e2.isoformat() == f"{d}T16:00:00-04:00")
    # Seam continuity: the base table's last bin flows into the
    # extension's first session.
    check("next bin start crosses the base->extension seam",
          u.next_bin_start("2026-10-16T13:30:00-04:00").isoformat()
          == "2026-10-19T09:30:00-04:00")
    # Fall-back inside the extension (Sun 2026-11-01).
    check("post-fallback Mon 2026-11-02 bin2 end -05:00",
          u.bin_end("2026-11-02T13:30:00-05:00").isoformat()
          == "2026-11-02T16:00:00-05:00")

    # Extension holidays fail closed.
    for d, name in (("2026-11-26", "Thanksgiving 2026"),
                    ("2026-12-25", "Christmas 2026"),
                    ("2027-03-26", "Good Friday 2027"),
                    ("2027-06-18", "Juneteenth observed 2027"),
                    ("2027-07-05", "Independence Day observed 2027"),
                    ("2027-12-24", "Christmas observed 2027")):
        expect_refusal(f"holiday refused ({name})",
                       lambda d=d: u.bin_end(f"{d}T09:30:00-05:00"),
                       "absent")
    # Extension early closes: single bin ending 13:00; no 13:30 bin.
    for d in ("2026-11-27", "2026-12-24", "2027-11-26"):
        bins = u.bins_for_date(d)
        check(f"early close {d}: single bin ending 13:00",
              len(bins) == 1
              and bins[0][1].strftime("%H:%M") == "13:00")
        expect_refusal(f"early close {d}: 13:30 bin refused",
                       lambda d=d: u.bin_end(f"{d}T13:30:00-05:00"),
                       "not a bin start")
    # Dec 31 2027 IS a session (NYSE does not observe NYD-2028 on
    # the preceding Friday).
    check("2027-12-31 is a regular session in the extension",
          u.bin_end("2027-12-31T13:30:00-05:00").isoformat()
          == "2027-12-31T16:00:00-05:00")
    # Beyond the declared horizon still fails closed.
    expect_refusal("beyond-horizon date refused (2028-01-03)",
                   lambda: u.bin_end("2028-01-03T09:30:00-05:00"),
                   "absent")

    # Pin enforcement on the extension artifact itself.
    eraw = open(sb.default_extension_path(), "rb").read()
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ext_tampered.json")
        with open(p, "wb") as f:
            f.write(eraw[:-2] + b"9}")
        expect_refusal("tampered extension refused (hash pin)",
                       lambda: sb.load_extension_table(p),
                       "hash mismatch")
        expect_refusal("missing extension refused",
                       lambda: sb.load_extension_table(
                           os.path.join(td, "nope.json")), "missing")
        # An extension naming a different parent is refused even
        # before its (necessarily different) hash is considered:
        # exercise the parentage check via a forged doc whose hash
        # cannot match the pin — refusal either way is fail-closed.
        forged = json.loads(eraw)
        forged["extends"]["sha256"] = "0" * 64
        pf = os.path.join(td, "ext_forged.json")
        with open(pf, "w") as f:
            json.dump(forged, f)
        expect_refusal("forged-parentage extension refused",
                       lambda: sb.load_extension_table(pf), "")

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
