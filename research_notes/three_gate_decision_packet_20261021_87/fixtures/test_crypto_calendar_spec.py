#!/usr/bin/env python3
"""
test_crypto_calendar_spec.py — Gate 1 fixtures (task -87) for the
PROPOSED crypto continuous calendar (crypto_calendar_spec.py).
Synthetic hourly bars only; no vendor data. Exit 1 on any FAIL.
"""
import json
import sys
from collections import Counter
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from crypto_calendar_spec import assign_bar, hourly_bars, session_span_utc  # noqa: E402

NY = ZoneInfo("America/New_York")
RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def bins_for_session(d):
    start, end = session_span_utc(d)
    counts = Counter()
    labels = {}
    for t in hourly_bars(start, end):
        sd, bi, label = assign_bar(t)
        assert sd == d, f"bar {t} leaked to session {sd}"
        counts[bi] += 1
        labels[bi] = label
    return counts, labels, int((end - start).total_seconds() // 3600)


def main():
    # C1 — normal EDT session: 24 bars, 6 bins x 4, anchor labels.
    counts, labels, hours = bins_for_session(date(2024, 6, 12))
    case("C1_normal_day_shape", hours == 24 and counts == Counter({i: 4 for i in range(6)}),
         f"hours={hours} counts={dict(counts)}")
    case("C1b_anchor_labels", labels[0] == ("2024-06-12", "09:30")
         and labels[1] == ("2024-06-12", "13:30")
         and labels[4] == ("2024-06-13", "01:30"),
         f"bin0={labels[0]} bin1={labels[1]} bin4={labels[4]}")

    # C2 — spring-forward session (2026-03-07 -> 03-08; 02:00 EST is
    # skipped): 23 bars; exactly one overnight bin holds 3 (with the
    # :30-phase bars generated here, bin 4 = [01:30,05:30)); the
    # daytime bins 0/1 always hold 4 (spec S-C3).
    counts, _, hours = bins_for_session(date(2026, 3, 7))
    case("C2_spring_forward", hours == 23 and counts[4] == 3
         and all(counts[i] == 4 for i in (0, 1, 2, 3, 5)),
         f"hours={hours} counts={dict(counts)}")

    # C3 — fall-back session (2026-10-31 -> 11-01; the 01:xx hour
    # occurs twice): 25 bars; exactly one overnight bin holds 5
    # (with :30-phase bars, bin 4 holds both 01:30 opens); daytime
    # bins 0/1 hold 4.
    counts, _, hours = bins_for_session(date(2026, 10, 31))
    case("C3_fall_back", hours == 25 and counts[4] == 5
         and all(counts[i] == 4 for i in (0, 1, 2, 3, 5)),
         f"hours={hours} counts={dict(counts)}")

    # C3b — phase-invariance of the totals: with :00-phase bar stamps
    # the same sessions still total 23/25, bins 0/1 still hold 4, and
    # exactly one overnight bin deviates (the absorbing bin differs:
    # fall-back repeat lands in bin 3 at :00 phase).
    def bins_for_session_phase0(d):
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        start, end = session_span_utc(d)
        t = start
        while t.astimezone(NY).minute != 0:
            t += _td(minutes=30)
        counts = Counter()
        n = 0
        while t < end:
            sd, bi, _ = assign_bar(t)
            assert sd == d
            counts[bi] += 1
            n += 1
            t += _td(hours=1)
        return counts, n

    c_s, n_s = bins_for_session_phase0(date(2026, 3, 7))
    c_f, n_f = bins_for_session_phase0(date(2026, 10, 31))
    case("C3b_phase0_totals_invariant",
         n_s == 23 and n_f == 25 and c_s[0] == c_s[1] == 4 and c_f[0] == c_f[1] == 4
         and sum(1 for v in c_s.values() if v != 4) == 1
         and sum(1 for v in c_f.values() if v != 4) == 1 and c_f[3] == 5,
         f"spring={n_s} {dict(c_s)} fall={n_f} {dict(c_f)}")

    # C4 — anchor alignment in both EST and EDT: bin 0 opens 09:30 ET,
    # bin 1 opens 13:30 ET wall clock, on winter and summer dates.
    ok = True
    for d in (date(2024, 1, 15), date(2024, 7, 15), date(2023, 12, 29), date(2025, 3, 20)):
        start, _ = session_span_utc(d)
        first_local = start.astimezone(NY)
        if not (first_local.date() == d and first_local.time() == time(9, 30)):
            ok = False
        _, labels, _ = bins_for_session(d)
        if labels[0][1] != "09:30" or labels[1][1] != "13:30":
            ok = False
    case("C4_anchor_alignment_both_dst_regimes", ok, "bin starts 09:30/13:30 ET year-round")

    # C5 — every date in the holdout span is a crypto session:
    # 2023-10-19..2024-09-15 inclusive = 333 session dates.
    n = (date(2024, 9, 15) - date(2023, 10, 19)).days + 1
    case("C5_every_date_a_session", n == 333, f"holdout span session dates={n}")

    # C6 — isolation: dates that are NOT XNYS sessions (Saturday,
    # Thanksgiving) ARE crypto sessions; the two calendars are
    # independent objects.
    cand = json.loads((Path(__file__).parent / "inputs" /
                       "XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json").read_text())
    xnys = {s["date"] for s in cand["sessions"]}
    sat = date(2023, 11, 25)
    thx = date(2023, 11, 23)
    case("C6_isolation_from_xnys",
         sat.isoformat() not in xnys and thx.isoformat() not in xnys
         and bins_for_session(sat)[2] == 24 and bins_for_session(thx)[2] == 24,
         "Sat 2023-11-25 and Thanksgiving are 24-bar crypto sessions, absent from XNYS")

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
