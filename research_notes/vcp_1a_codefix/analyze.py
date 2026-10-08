#!/usr/bin/env python3
"""Phase 1A analysis: Fama-MacBeth paired differences, block bootstrap,
persistence rule, hit rates, downside, breadth, turnover. Frozen per RUN_PLAN.

CODEFIX 2026-10-07 (QF-VCP-1A-CODEFIX-20261007-03, per adjudication 6051281109):
  D1. Annualization: d_m is already a 3M/6M/12M forward-return difference, so
      multiplying every horizon's mean effect by 12 is wrong. The frozen
      RUN_PLAN §7 line "Effect size annualized (x12) also reported" is the
      documented source of the bug; the adjudication overrides it as a
      load-bearing math error. This file now reports the RAW per-window effect
      as primary and a horizon-aware linear equivalent (x4/x2/x1) labeled
      SECONDARY. Same fix applied to vs-SPY "annualized" fields.
  D2. Date boundaries: SUBPERIODS bounds ("2010-01".."2011-12") were compared
      lexically against full dates ("2011-12-31"), silently dropping every
      ending-December (23 months per subperiod instead of the frozen 24) and
      dropping 2025-09 from r12 ("2025-09-30" > "2025-09"). All month
      comparisons now use month periods (YYYY-MM).
  D3. Horizon cutoff: the hardcoded r12 string cutoff is replaced by
      per-row fwd_complete_<h>/fwd_status_<h> fields (see build_panels.py).
      (The 95% data-derived cutoff was an interim step; per adjudication
      6051509411 it is NOT an accepted-run parameter and is removed from
      the accepted path — last_complete_month is retained only as a labeled
      local non-performance probe.)
No strategy-rule changes: d_m estimand, bootstrap, persistence rule logic,
mcap filter, and qualifier definitions are untouched.

CODEFIX-DELTA 2026-10-08 (QF-VCP-1A-CODEFIX-DELTA-20261008-04, per
  adjudication 6051509411):
  D4. Delist/censoring conflation: rows whose series ends by
      delisting/acquisition/bankruptcy (closed membership interval) were
      marked incomplete and excluded — reintroducing survivor/attrition bias
      against the frozen §5 flat-hold rule. build_panels.py now emits
      fwd_status_<h> in {'complete','delisted_flat','censored'}; analysis
      counts 'complete' and 'delisted_flat' as complete, excludes 'censored'.
  D5. Fail closed: analysis raises a hard error unless EVERY analyzed row
      carries explicit boolean fwd_complete_<h> and fwd_status_<h> fields
      with in-enum values. Missing/mixed flags never default True. Legacy
      panels require explicit --legacy-repro + --cutoff-override and are
      stamped NON-ACCEPTANCE.
"""
import argparse, bisect, glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(42)
N_BOOT = 9999
BLOCK = 12
HORIZONS = ["r3", "r6", "r12"]
WIN = {"r3": 63, "r6": 126, "r12": 252}
# Linear horizon-equivalent annualization factors (documented, SECONDARY):
# d_m is a w-trading-day forward-return difference; the linear annual
# equivalent scales by 12 / horizon_months. Primary reporting is the raw
# per-window effect; the annualized figure is secondary by construction.
ANN_FACTOR = {"r3": 4, "r6": 2, "r12": 1}
SUBPERIODS = [(f"{y}-01", f"{y+1}-12") for y in range(2010, 2025, 2)]  # 8 x 2Y
MIN_SIDE = 5
# Fraction of in-month panel tickers required to have a complete forward
# window for the month to be included (data-derived cutoff; see
# last_complete_month). 1.00 is infeasible: delisted/sparse names never have
# complete late windows; 0.95 is a documented judgment call.
#
# CODEFIX-DELTA 2026-10-08 (per adjudication 6051509411): the 95% threshold
# is NOT an accepted-run parameter. last_complete_month is retained ONLY as
# a labeled local non-performance probe; the accepted analysis path never
# calls it. Legacy-panel reproduction requires explicit --legacy-repro.
CUTOFF_MIN_FRAC = 0.95

# Required explicit forward-status fields (CODEFIX-DELTA). Every analyzed row
# must carry all of these; anything less is a hard error (fail closed).
FLAG_KEYS = ["fwd_complete_r3", "fwd_complete_r6", "fwd_complete_r12"]
STATUS_KEYS = ["fwd_status_r3", "fwd_status_r6", "fwd_status_r12"]
STATUS_OK = ("complete", "delisted_flat")  # counted COMPLETE per frozen §5
STATUS_ENUM = ("complete", "delisted_flat", "censored")


def resolve_horizon_filter(rows, legacy_repro=False, cutoff_override=None):
    """Fail-closed horizon-filter resolution (production function).

    Accepted path: EVERY row carries explicit fwd_complete_<h> booleans and
    fwd_status_<h> fields with values in STATUS_ENUM. Returns
    {"mode": "flags"}. Analysis filters on the flags; 'delisted_flat'
    counts as complete per frozen RUN_PLAN §5.

    Any deviation is a hard RuntimeError:
      - mixed schema (some rows with fields, some without),
      - any row missing any required field,
      - any fwd_status_<h> value outside STATUS_ENUM,
      - legacy panel (no fields at all) without legacy_repro=True.
    Legacy reproduction (--legacy-repro) additionally REQUIRES
    cutoff_override with explicit per-horizon cutoffs and stamps output
    NON-ACCEPTANCE. The 95% data-derived cutoff is not usable here.
    """
    n = len(rows)
    if n == 0:
        raise RuntimeError("empty panel: nothing to analyze")
    need = FLAG_KEYS + STATUS_KEYS
    n_full = sum(1 for r in rows if all(k in r for k in need))
    if n_full == n:
        bad = [r for r in rows
               if any(r[k] not in STATUS_ENUM for k in STATUS_KEYS)]
        if bad:
            raise RuntimeError(
                f"{len(bad)} rows carry fwd_status values outside "
                f"{STATUS_ENUM}; fail closed.")
        for r in rows:
            for k in FLAG_KEYS:
                if not isinstance(r[k], bool):
                    raise RuntimeError(
                        f"non-boolean {k}={r[k]!r}; fail closed.")
        # INTERVAL-FIX 2026-10-08 (QF-VCP-1A-INTERVAL-FIX-20261008-06, per
        # adjudication 6053282451): cross-field invariant as hard
        # accepted-run preflight. The producer emits both fields
        # consistently, but resolve_horizon_filter must assert it rather
        # than trust it.
        horiz = (("r3", "fwd_complete_r3", "fwd_status_r3"),
                 ("r6", "fwd_complete_r6", "fwd_status_r6"),
                 ("r12", "fwd_complete_r12", "fwd_status_r12"))
        viol = []
        for r in rows:
            for h, fk, sk in horiz:
                expect = r[sk] in STATUS_OK
                if r[fk] != expect:
                    viol.append((r.get("t"), r.get("m"), h, r[fk], r[sk]))
                    if len(viol) >= 5:
                        break
            if len(viol) >= 5:
                break
        if viol:
            raise RuntimeError(
                f"cross-field invariant violated: fwd_complete_<h> != "
                f"(fwd_status_<h> in {STATUS_OK}); {len(viol)}+ rows; "
                f"first: {viol[:5]}; fail closed.")
        return {"mode": "flags"}
    if n_full > 0:
        raise RuntimeError(
            f"mixed panel schema: {n_full}/{n} rows carry explicit "
            f"forward-status fields; fail closed. Rebuild the panel with "
            f"the corrected build_panels.py.")
    if not legacy_repro:
        raise RuntimeError(
            "legacy panel without explicit forward-status fields; refusing "
            "to guess completeness. Rebuild with corrected build_panels.py, "
            "or pass --legacy-repro (explicit non-acceptance reproduction "
            "mode).")
    if not cutoff_override:
        raise RuntimeError(
            "--legacy-repro requires --cutoff-override with explicit "
            "per-horizon month cutoffs (the 95% data-derived cutoff is not "
            "an accepted-run parameter).")
    cutoff = dict(kv.split("=") for kv in cutoff_override.split(","))
    return {"mode": "legacy", "cutoff": cutoff,
            "acceptance": "NON-ACCEPTANCE (legacy reproduction)"}


def load_panel(path):
    rows = [json.loads(l) for l in open(path)]
    return rows


def block_bootstrap(d, n=N_BOOT, block=BLOCK):
    d = np.asarray(d, float)
    nobs = len(d)
    if nobs < 2:
        return None
    block = min(block, nobs)
    starts = np.arange(nobs - block + 1)
    nb = int(np.ceil(nobs / block))
    means = np.empty(n)
    for i in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in
                              rng.choice(starts, nb, replace=True)])[:nobs]
        means[i] = d[idx].mean()
    return means


def summarize(d, ann_factor):
    """Primary: raw per-window mean effect. Secondary (labeled): linear
    horizon-equivalent annualized figure = raw * ann_factor."""
    d = np.asarray(d, float)
    if len(d) < 2:
        return {"n_months": len(d), "mean_window": None,
                "mean_ann_linear_equiv_SECONDARY": None,
                "ci95_window": [None, None], "p_two_sided": None}
    obs = d.mean()
    boots = block_bootstrap(d)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # two-sided p vs H0: mean = 0 — recenter the bootstrap distribution at 0
    # (the raw bootstrap is centered at obs; testing against it is degenerate)
    boots0 = boots - obs
    p = float(np.mean(np.abs(boots0) >= abs(obs)))
    return {"n_months": len(d), "mean_window": round(float(obs), 6),
            "mean_ann_linear_equiv_SECONDARY": round(float(obs * ann_factor), 6),
            "ci95_window": [round(float(lo), 6), round(float(hi), 6)],
            "p_two_sided": round(float(min(p, 1.0)), 6)}


def _mean(xs):
    return round(float(np.mean(xs)), 6) if len(xs) else None


def _load_eod_dates(eod_dir, tickers):
    """{ticker: sorted [date,...]} for tickers with a raw EOD file on disk."""
    out = {}
    for t in tickers:
        p = os.path.join(eod_dir, f"{t}.json")
        if not os.path.exists(p):
            continue
        try:
            bars = json.load(open(p))
        except Exception:
            continue
        ds = sorted(b["date"][:10] for b in bars
                    if isinstance(b, dict) and b.get("adjClose"))
        if ds:
            out[t] = ds
    return out


def last_complete_month(rows, months, w, eod_dir, min_frac=CUTOFF_MIN_FRAC):
    """Data-derived horizon cutoff (replaces the old hardcoded 'YYYY-MM'
    string cutoff). Latest month m (as 'YYYY-MM-DD' month-end) such that at
    least min_frac of the tickers present in the panel that month have >= w
    trading days strictly after their observation bar (latest bar <= m, same
    definition as build_panels.py). The denominator is panel-active tickers:
    delisted names that left the panel years ago must not veto late months.
    Deterministic; reads on-disk raw EOD only — zero vendor calls. Months
    are checked from latest backward; completeness is monotone decreasing
    in m."""
    by_month = {}
    tickers = set()
    for r in rows:
        by_month.setdefault(r["m"], []).append(r["t"])
        tickers.add(r["t"])
    cal = _load_eod_dates(eod_dir, sorted(tickers))
    if not cal:
        raise RuntimeError(
            f"no raw EOD calendars loaded from {eod_dir}; pass --eod-dir or "
            "--cutoff-override (override is for reproducing the frozen-panel "
            "derivation only)")
    for m in sorted(months, reverse=True):
        have = 0
        ok = 0
        for t in by_month.get(m, ()):
            ds = cal.get(t)
            if not ds:
                continue
            pos = bisect.bisect_right(ds, m) - 1
            if pos < 0:
                continue
            have += 1
            if len(ds) - 1 - pos >= w:
                ok += 1
        if have and ok / have >= min_frac:
            return m
    raise RuntimeError(f"no month meets completeness for w={w}")


def load_spy_ref(months_path, eod_path):
    """SPY total returns over identical forward windows. Returns {m: {r3,r6,r12}} or {}."""
    try:
        bars = json.load(open(eod_path))
        months = json.load(open(months_path))
    except FileNotFoundError:
        return {}
    dates = sorted(b["date"][:10] for b in bars)
    px = {b["date"][:10]: b["adjClose"] for b in bars}
    closes = [px[d] for d in dates]
    ref = {}
    for m in months:
        pos = bisect.bisect_right(dates, m) - 1
        if pos < 0:
            continue
        obs = closes[pos]
        r = {}
        for key, w in WIN.items():
            end_i = min(pos + w, len(dates) - 1)
            r[key] = round(closes[end_i] / obs - 1.0, 6)
        ref[m] = r
    return ref


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--panel", default=os.path.join(HERE, "panels", "panel.jsonl"))
    a.add_argument("--out", default=os.path.join(HERE, "results_phase1a.json"))
    a.add_argument("--spy", default=None,
                 help="path to raw/eod/SPY.json for secondary reference")
    a.add_argument("--eod-dir", default=os.path.join(HERE, "raw", "eod"),
                 help="raw EOD dir for the data-derived horizon cutoff")
    a.add_argument("--cutoff-override", default=None,
                 help="YYYY-MM-DD month-end cutoff per horizon as "
                      "'r3=..,r6=..,r12=..'; REQUIRES --legacy-repro; for "
                      "reproducing the frozen-panel derivation only — the "
                      "November run must use explicit flags")
    a.add_argument("--legacy-repro", action="store_true",
                 help="explicit non-acceptance mode: analyze a legacy panel "
                      "without forward-status fields using --cutoff-override "
                      "cutoffs. Output is stamped NON-ACCEPTANCE.")
    args = a.parse_args()
    rows = load_panel(args.panel)
    spy_ref = load_spy_ref(os.path.join(HERE, "month_ends.json"), args.spy) if args.spy else {}
    # mcap filter (frozen): $2B <= mcap <= $100B, PIT estimate; null -> exclude
    filt = [r for r in rows if r.get("mcap") is not None
            and 2e9 <= r["mcap"] <= 100e9]
    print(f"panel rows={len(rows)} after mcap filter={len(filt)}")
    months = sorted(set(r["m"] for r in filt))
    if not months:
        print("no rows after mcap filter; nothing to analyze")
        return 0

    # --- horizon completeness: fail-closed explicit flags (accepted path),
    # or explicit legacy-reproduction mode. Never a hardcoded date string,
    # never a silent 95% fallback. (CODEFIX-DELTA, adjudication 6051509411)
    flag_key = {"r3": "fwd_complete_r3", "r6": "fwd_complete_r6",
                "r12": "fwd_complete_r12"}
    filt_mode = resolve_horizon_filter(rows, args.legacy_repro,
                                       args.cutoff_override)
    has_flags = (filt_mode["mode"] == "flags")
    if has_flags:
        print("using per-row fwd_complete_<h>/fwd_status_<h> fields "
              "(fail-closed; delisted_flat counts complete per frozen §5)")
        cutoff = {}
    else:
        cutoff = filt_mode["cutoff"]
        print(f"LEGACY REPRODUCTION MODE — {filt_mode['acceptance']}: "
              f"cutoffs {cutoff}")

    out = {"n_panel_rows": len(rows), "n_filtered_rows": len(filt),
           "months": [months[0], months[-1]], "variants": {},
           "codefix": "QF-VCP-1A-CODEFIX-20261007-03+DELTA-20261008-04",
           "horizon_filter": filt_mode,
           "horizon_cutoffs": cutoff if not has_flags else "per-row-flags",
           "annualization": "raw per-window primary; "
                            "mean_ann_linear_equiv_SECONDARY = raw * "
                            + str(ANN_FACTOR)}
    for v in ["v1", "v2"]:
        vres = {"horizons": {}, "breadth": {}, "turnover": None,
                "hit_rate": {}, "downside": {}}
        qsets = {}
        for h in HORIZONS:
            if has_flags:
                used = months
                # Fail closed: resolve_horizon_filter already guaranteed every
                # row carries an explicit boolean; no .get() default.
                row_ok = lambda r: bool(r[flag_key[h]])
            else:
                used = [mm for mm in months if mm <= cutoff[h]]
                row_ok = lambda r: True
            d_all, qrets, crets, qmeans = [], [], [], []
            for m in used:
                rm = [r for r in filt if r["m"] == m and row_ok(r)]
                q = [r[h] for r in rm if r[v]]
                c = [r[h] for r in rm if not r[v]]
                if len(q) < MIN_SIDE or len(c) < MIN_SIDE:
                    d_all.append(np.nan)
                    qmeans.append(np.nan)
                else:
                    d_all.append(float(np.mean(q) - np.mean(c)))
                    qmeans.append(float(np.mean(q)))
                    qrets.extend(q)
                    crets.extend(c)
            d = [x for x in d_all if not np.isnan(x)]
            s = summarize(d, ANN_FACTOR[h])
            s["n_months_used"] = len(d)
            s["n_qual_obs"] = len(qrets)
            s["n_ctrl_obs"] = len(crets)
            s["mean_qual_ret"] = _mean(qrets)
            s["mean_ctrl_ret"] = _mean(crets)
            vres["horizons"][h] = s
            sub = []
            for (y0, y1) in SUBPERIODS:
                # month-period comparison (CODEFIX D2): mth is YYYY-MM-DD;
                # comparing against YYYY-MM bounds lexically drops December.
                vals = [x for mth, x in zip(used, d_all)
                        if y0 <= mth[:7] <= y1 and not np.isnan(x)]
                sub.append({"period": f"{y0[:4]}-{y1[:4]}",
                            "n_months": len(vals),
                            "mean_excess_window": round(float(np.mean(vals)), 6)
                            if vals else None})
            vres["horizons"][h]["subperiods"] = sub
            vres["horizons"][h]["n_positive_subperiods"] = sum(
                1 for s_ in sub if s_["mean_excess_window"] is not None and s_["mean_excess_window"] > 0)
            # hit rate / downside on qualifier observations
            vres["hit_rate"][h] = {
                "qual": round(float(np.mean(np.array(qrets) > 0)), 4) if qrets else None,
                "ctrl": round(float(np.mean(np.array(crets) > 0)), 4) if crets else None}
            if has_flags:
                dds = [r["dd_" + h] for r in filt if r[v] and bool(r[flag_key[h]])]
            else:
                dds = [r["dd_" + h] for r in filt if r[v] and r["m"] <= cutoff[h]]
            vres["downside"][h] = {"n": len(dds),
                                   "mean_max_adv_exc": _mean(dds),
                                   "median_max_adv_exc": round(float(np.median(dds)), 4)
                                   if dds else None}
            if spy_ref:
                exc = [qm - spy_ref[m][h] for m, qm in zip(used, qmeans)
                       if m in spy_ref and not np.isnan(qm)]
                if exc:
                    se = float(np.mean(exc))
                    vres["horizons"][h]["vs_spy"] = {
                        "n_months": len(exc),
                        "mean_excess_window": round(se, 6),
                        "mean_excess_ann_linear_equiv_SECONDARY":
                            round(se * ANN_FACTOR[h], 6)}
        # breadth + turnover
        counts = []
        for m in months:
            q = [r["t"] for r in filt if r["m"] == m and r[v]]
            qsets[m] = set(q)
            counts.append(len(q))
        vres["breadth"] = {"mean": round(float(np.mean(counts)), 1),
                           "min": int(np.min(counts)), "max": int(np.max(counts))}
        to = []
        for i in range(len(months) - 1):
            a_, b_ = qsets[months[i]], qsets[months[i + 1]]
            if a_:
                to.append(1 - len(a_ & b_) / len(a_))
        vres["turnover"] = round(float(np.mean(to)), 4) if to else None
        out["variants"][v] = vres
    # persistence rule (frozen §7): per horizon h, pass_h =
    #   full-sample mean(d_h) > 0  AND  >=5/8 subperiods with mean>0
    #   AND  bootstrap p_h < 0.05.
    # Overall verdict: all three horizons pass (no cherry-picking).
    # CODEFIX: the rule logic is unchanged; it now reads the raw per-window
    # mean (mean_window) instead of the mislabeled mean_m.
    persist = {}
    for v in ["v1", "v2"]:
        h_pass = {}
        for h in HORIZONS:
            s = out["variants"][v]["horizons"][h]
            h_pass[h] = bool(
                s["mean_window"] is not None and s["mean_window"] > 0
                and s["n_positive_subperiods"] is not None
                and s["n_positive_subperiods"] >= 5
                and s["p_two_sided"] is not None
                and s["p_two_sided"] < 0.05)
        persist[v] = {"per_horizon": h_pass,
                      "pass_all_three": all(h_pass.values())}
    out["persistence_rule"] = persist
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"-> {args.out}")
    print("persistence:", json.dumps(persist))
    # console tables
    def _f(x):
        return f"{x:+.4f}" if x is not None else "n/a"
    for v in ["v1", "v2"]:
        print(f"\n=== {v.upper()} ===")
        for h in HORIZONS:
            s = out["variants"][v]["horizons"][h]
            print(f" {h}: window={_f(s['mean_window'])} "
                  f"ann_equiv(2nd)={_f(s['mean_ann_linear_equiv_SECONDARY'])} "
                  f"CI95=[{_f(s['ci95_window'][0])},{_f(s['ci95_window'][1])}] p={s['p_two_sided']} "
                  f"nmo={s['n_months']} subpos={s['n_positive_subperiods']}/8 "
                  f"qret={_f(s['mean_qual_ret'])} cret={_f(s['mean_ctrl_ret'])}")
        print(f" breadth={out['variants'][v]['breadth']} turnover={out['variants'][v]['turnover']}")
        print(f" hit_rate={out['variants'][v]['hit_rate']}")
        print(f" downside={out['variants'][v]['downside']}")


if __name__ == "__main__":
    sys.exit(main())
