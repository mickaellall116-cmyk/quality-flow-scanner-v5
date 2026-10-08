#!/usr/bin/env python3
"""Build per-ticker-month observation panel for VCP Probe Phase 1A.

Inputs: universe.json, raw/eod/{T}.json, raw/fund/{T}.json, month_ends.json
Output: panels/panel.jsonl — one row per ticker-month with prices, MAs,
        PIT market-cap filter inputs, forward returns, downside excursion,
        and forward-window completeness flags.

Frozen rules: see RUN_PLAN_FROZEN_20261001.md.

CODEFIX 2026-10-07 (QF-VCP-1A-CODEFIX-20261007-03, per adjudication 6051281109):
  Forward windows were silently truncated at the series end via
  end_i = min(pos + w, len(dates) - 1): a 251-day window was reported in the
  r12 field with no marker. Each row now carries fwd_complete_r3/r6/r12
  booleans (True iff pos + w <= len(dates) - 1, i.e. the full w-trading-day
  window is present). Truncated values are RETAINED for provenance but must be
  EXCLUDED from analysis — corrected analyze.py filters on these flags
  (falling back to a data-derived month cutoff on legacy panels without them).
  No strategy-rule changes.
"""
import argparse, json, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

WIN = {"r3": 63, "r6": 126, "r12": 252}
MA_REQ = {150: 140, 200: 185, 250: 230}
MCAP_MAX = 100e9
PX_MIN = 10.0
SHARE_LAG_DAYS = 45


def load_bars(t):
    p = os.path.join(RAW, "eod", f"{t}.json")
    if not os.path.exists(p):
        return None
    rows = json.load(open(p))
    bars = []
    for r in rows:
        d = r["date"][:10]
        ac = r.get("adjClose")
        c = r.get("close")
        if ac is None or ac <= 0 or c is None or c <= 0:
            continue
        bars.append((d, float(ac), float(c)))
    bars.sort()
    # dedupe dates, keep last
    dd = {}
    for d, ac, c in bars:
        dd[d] = (ac, c)
    items = sorted(dd.items())
    return items  # [(iso_date, adjClose, close_unadjusted)]


def load_edgar(t):
    """EDGAR quarterly shares series: [(frame_end, filed, shares)]."""
    if not hasattr(load_edgar, "cache"):
        load_edgar.cache = json.load(open(os.path.join(HERE, "edgar_shares.json")))
    return load_edgar.cache.get(t, [])


def shares_at(shares, month_end):
    """Latest quarterly frame with filed <= month_end - 45d and end <= month_end
    (PIT filing-lag guard; EDGAR source)."""
    cutoff = (date.fromisoformat(month_end) - timedelta(days=SHARE_LAG_DAYS)).isoformat()
    best = None
    for end, filed, v in shares:
        if end <= month_end and filed <= cutoff:
            best = v
    return best


def add_days(d, n):
    return (date.fromisoformat(d) + timedelta(days=n)).isoformat()


DATA_FLOOR = "2009-01-01"      # pull.py startDate; earlier membership months unobservable
SERIES_CURRENT = "2026-09-21"  # series must be this fresh for open-ended intervals


def reuse_guard(ms, me, s0, s1):
    """Return (ok, reason). Verifies the fetched series is the company that held
    the ticker during [ms, me] (ihsieh31 reuse finding). Evaluable months clamp
    to membership ∩ [s0, s1]; the START side needs no quarantine because pre-s0
    months simply have no bars. The END side detects wrong-company: a reused
    ticker serving the new company's series runs past the old interval's end;
    serving the old company's series stops before an open interval's now."""
    open_end = (me == "2200-01-01")
    if open_end:
        end_ok = s1 >= SERIES_CURRENT
        end_why = f"open: s1={s1}"
    else:
        end_ok = add_days(me, -9) <= s1 <= add_days(me, 9)
        end_why = f"closed: me={me} s1={s1}"
    if not end_ok:
        return False, f"END_MISMATCH {end_why}"
    if ms < DATA_FLOOR <= s0 <= "2009-01-15":
        return True, "depth-clamp (interval starts before data floor)"
    if s0 > add_days(ms, 9) and ms >= DATA_FLOOR:
        return True, f"WARN late series start s0={s0} ms={ms}"
    return True, "ok"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--tickers", default=None, help="file with tickers (default: all)")
    a.add_argument("--months", default=os.path.join(HERE, "month_ends.json"))
    a.add_argument("--out", default=os.path.join(HERE, "panels", "panel.jsonl"))
    args = a.parse_args()
    universe = json.load(open(os.path.join(HERE, "universe.json")))["tickers"]
    months = json.load(open(args.months))  # ["2010-01-29", ...]
    if args.tickers:
        todo = [l.strip().upper() for l in open(args.tickers) if l.strip()]
    else:
        todo = sorted(universe.keys())

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    n_rows = 0
    quar_log = []
    with open(args.out, "w") as fo:
        for t in todo:
            bars = load_bars(t)
            if not bars:
                quar_log.append(f"{t}: no EOD data")
                continue
            dates = [d for d, _ in bars]
            adj = {d: ac for d, (ac, _) in bars}
            unadj = {d: c for d, (_, c) in bars}
            shares = load_edgar(t)
            # per-interval ticker-reuse guard (ihsieh31 finding)
            valid_intervals = []
            for (ms, me) in universe.get(t, []):
                ok, why = reuse_guard(ms, me, dates[0], dates[-1])
                if not ok:
                    quar_log.append(f"{t}: interval {ms}..{me} {why} "
                                    f"(series {dates[0]}..{dates[-1]}) QUARANTINED")
                    continue
                if why.startswith("WARN"):
                    quar_log.append(f"{t}: interval {ms}..{me} {why} (kept, clamped)")
                valid_intervals.append((ms, me))
            if not valid_intervals:
                continue
            # month loop
            for m in months:
                if not any(ms <= m <= me for ms, me in valid_intervals):
                    continue
                # observation bar: latest trading day <= m (must be within ~5 trading days)
                import bisect
                pos = bisect.bisect_right(dates, m) - 1
                if pos < 0:
                    continue
                obs_d = dates[pos]
                gap = (date.fromisoformat(m) - date.fromisoformat(obs_d)).days
                if gap > 9:  # > ~5 trading days -> stale, drop
                    continue
                obs_adj = adj[obs_d]     # split/div-adjusted: MAs, returns
                obs_px = unadj[obs_d]    # actual traded price: $10 filter, mcap
                if obs_px < PX_MIN:
                    continue
                # moving averages (inclusive of obs bar), on adjClose
                mas = {}
                ok_ma = True
                closes = [ac for _, (ac, _) in bars]
                for w, need in MA_REQ.items():
                    if pos + 1 < need:
                        ok_ma = False
                        break
                    seg = closes[max(0, pos - w + 1): pos + 1]
                    seg = [c for c in seg if c and c > 0]
                    if len(seg) < need:
                        ok_ma = False
                        break
                    mas[w] = sum(seg) / len(seg)
                if not ok_ma:
                    continue
                # market-cap filter: unadjusted close x EDGAR shares (same basis)
                sh = shares_at(shares, m)
                mcap = obs_px * sh if sh is not None else None
                # forward returns + downside excursion (adjClose: split-continuous)
                # CODEFIX D3: record window completeness explicitly; a truncated
                # window's value is retained for provenance but flagged so the
                # analysis excludes it instead of silently shortening the window.
                rets, dds, fwc = {}, {}, {}
                for key, w in WIN.items():
                    complete = (pos + w <= len(dates) - 1)
                    fwc[key] = complete
                    end_i = pos + w if complete else len(dates) - 1
                    end_px = closes[end_i]
                    rets[key] = end_px / obs_adj - 1.0
                    segmin = min(closes[pos + 1: end_i + 1]) if end_i > pos else obs_adj
                    dds[key] = segmin / obs_adj - 1.0
                row = {"t": t, "m": m, "obs_d": obs_d, "px": round(obs_adj, 4),
                       "px_unadj": round(obs_px, 4),
                       "ma150": round(mas[150], 4), "ma200": round(mas[200], 4),
                       "ma250": round(mas[250], 4),
                       "shares": sh, "mcap": mcap,
                       "v1": bool(obs_adj > mas[150] and obs_adj > mas[200]),
                       "v2": bool(obs_adj > mas[150] and obs_adj > mas[200] and obs_adj > mas[250]),
                       "fwd_complete_r3": fwc["r3"], "fwd_complete_r6": fwc["r6"],
                       "fwd_complete_r12": fwc["r12"]}
                for key in WIN:
                    row[key] = round(rets[key], 6)
                    row["dd_" + key] = round(dds[key], 6)
                fo.write(json.dumps(row) + "\n")
                n_rows += 1
    real_q = [l for l in quar_log if "no EOD data" not in l]
    with open(os.path.join(HERE, "panels", "quarantine.log"), "w") as f:
        f.write("\n".join(quar_log) + "\n")
    print(f"rows={n_rows} unfetched={len(quar_log)-len(real_q)} "
          f"guard_quarantined={len(real_q)} -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
