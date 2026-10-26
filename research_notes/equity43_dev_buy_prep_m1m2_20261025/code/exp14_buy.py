"""EXP-14-BUY-DEV-EXPLORATORY — pinned exploratory BUY study script.

Preregistration v0.3 §5 (H-BUY), preparatory pin under Issue #1 comment
6405097569 (Claude Final-Gate verdict relay). This script implements,
exactly as drafted in v0.3 §5:

  EVENTS      every frozen pine_buy_signal fire in the P7b inventory's
              generator domain, de-clustered: an event is kept only if
              the same symbol had NO signal bar in the previous 20 bars.
  B-A POOL    same symbol; same session bin (09:30 / 13:30); session
              ordinal within +/-30 sessions; no signal bar within
              +/-20 bars; ATR% within a relative band of the event's
              ATR% (base +/-25%); full forward window inside the data.
  B-T POOL    B-A construction, additionally restricted to bars with
              Close > EMA200, EMA21 > EMA55 and the full signal false
              (non-gating diagnostic).
  LADDER      pre-declared feasibility relaxation, in fixed order:
              step 0 base; (a) ATR% band +/-40%; (b) session window
              +/-45; (c) minimum pool 6. Frozen at the first step whose
              event drop rate (pool < minimum) is <= 15%.
  DRAWS       20 pool bars without replacement per retained event
              (whole pool if fewer than 20), deterministic per event:
              sub-seed = first 8 bytes (big-endian) of
              SHA-256(f"{MASTER_SEED}:{arm}:{symbol}:{idx}"), numpy
              PCG64 Generator. MASTER_SEED itself is the first 8 bytes
              (big-endian) of SHA-256("EXP-14-BUY-DEV-EXPLORATORY").
  HORIZONS    5 / 10 / 20 bars; 10 is the single primary endpoint.
              Pool-count feasibility and the frozen draws use the
              primary horizon's forward-window rule (h = 10); counts
              at h = 20 are published alongside as outcome-blind info.
              Interpretation P-1 (recorded in the package MEMO): pool
              bars are restricted to the generator domain, the only
              bars whose signal status the P7 census certifies.

MODES
  pool-counts (default): cohort, pools, ladder, frozen draws. Computes
      NO forward returns and NO group differences. This is the only
      mode exercised by the preparatory package.
  returns: DISABLED. Computing forward returns requires the separate
      execution GO named in the package MEMO; any invocation raises
      ExecutionGoRequired. There is no flag that enables it in this
      pinned version — enabling it is a new version + new pin + GO.

FAIL-CLOSED: the inventory file's SHA-256 must match --inventory-sha;
the inventory's domain fire set must reconcile to 2,892 fires (the P7
census) before any cohort work; missing indicator fields exclude a bar
from pools and are counted, never imputed.
"""
import argparse
import hashlib
import json
import sys

import numpy as np

STUDY_ID = "EXP-14-BUY-DEV-EXPLORATORY"
MASTER_SEED = int.from_bytes(
    hashlib.sha256(STUDY_ID.encode()).digest()[:8], "big")
HORIZONS = (5, 10, 20)
PRIMARY_H = 10
DECLUSTER_BARS = 20
EXCLUSION_BARS = 20
DRAW_N = 20
EXPECTED_FIRES = 2892
LADDER = (
    {"step": 0, "atr_band": 0.25, "session_window": 30, "min_pool": 8},
    {"step": "a", "atr_band": 0.40, "session_window": 30, "min_pool": 8},
    {"step": "b", "atr_band": 0.40, "session_window": 45, "min_pool": 8},
    {"step": "c", "atr_band": 0.40, "session_window": 45, "min_pool": 6},
)
DROP_FLAG = 0.15


class ExecutionGoRequired(RuntimeError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inventory(path, expected_sha):
    got = sha256_file(path)
    if got != expected_sha:
        raise SystemExit(
            f"FAIL-CLOSED: inventory sha256 {got} != pinned {expected_sha}")
    by_symbol = {}
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            by_symbol.setdefault(row["symbol"], []).append(row)
    for rows in by_symbol.values():
        rows.sort(key=lambda r: r["idx"])
    return by_symbol


def fires_of(rows):
    return sorted(r["idx"] for r in rows
                  if r["in_generator_domain"] and r["signal"])


def decluster(fires):
    """Keep a fire only if no signal bar in the previous 20 bars."""
    kept, last_fire = [], None
    fire_set = set(fires)
    for i in fires:
        if not any(j in fire_set for j in range(i - DECLUSTER_BARS, i)):
            kept.append(i)
        last_fire = i
    return kept


def excluded_set(fires_set, n):
    """Bars within +/-EXCLUSION_BARS of any signal bar (inclusive)."""
    out = set()
    for f in fires_set:
        out.update(range(max(0, f - EXCLUSION_BARS),
                         min(n - 1, f + EXCLUSION_BARS) + 1))
    return out


def eligible_pool(rows, excl, event, step, horizon, arm):
    """B-A / B-T eligible pool bar indices for one event at a ladder step.

    rows: the symbol's inventory rows (idx-ordered); excl: precomputed
    exclusion set from excluded_set(); event: inventory row of the
    signal bar. Pure function of inventory fields — no prices beyond
    the published inventory fields, no forward returns."""
    n = len(rows)
    pool = []
    for r in rows:
        j = r["idx"]
        if not r["in_generator_domain"]:
            continue
        if r["bin"] != event["bin"]:
            continue
        if abs(r["session_ordinal"] - event["session_ordinal"]) \
                > step["session_window"]:
            continue
        if j in excl:
            continue
        if r["atr_pct"] is None or event["atr_pct"] is None:
            continue
        if abs(r["atr_pct"] - event["atr_pct"]) \
                > step["atr_band"] * event["atr_pct"]:
            continue
        if j + horizon > n - 1:
            continue
        if arm == "B-T":
            if r["ema200"] is None or r["ema55"] is None \
                    or r["ema21"] is None:
                continue
            if not (r["close"] > r["ema200"] and r["ema21"] > r["ema55"]):
                continue
            if r["signal"]:
                continue
        pool.append(j)
    return pool


def event_draws(arm, symbol, event_idx, pool):
    """Deterministic per-event draw without replacement."""
    sub = int.from_bytes(hashlib.sha256(
        f"{MASTER_SEED}:{arm}:{symbol}:{event_idx}".encode()
    ).digest()[:8], "big")
    rng = np.random.default_rng(np.random.PCG64(sub))
    pool_sorted = sorted(pool)
    k = min(DRAW_N, len(pool_sorted))
    chosen = rng.choice(pool_sorted, size=k, replace=False)
    return sorted(int(x) for x in chosen)


def run_pool_counts(by_symbol):
    # ---- census reconciliation (fail-closed) --------------------------
    total_fires = sum(len(fires_of(rows)) for rows in by_symbol.values())
    if total_fires != EXPECTED_FIRES:
        raise SystemExit(
            f"FAIL-CLOSED: inventory domain fires {total_fires} "
            f"!= P7 census {EXPECTED_FIRES}")

    events = {}          # (symbol, idx) -> event row
    dropped_window = {}  # horizon -> count of de-clustered events dropped
    for sym, rows in by_symbol.items():
        by_idx = {r["idx"]: r for r in rows}
        n = len(rows)
        for i in decluster(fires_of(rows)):
            events[(sym, i)] = by_idx[i]
    for h in HORIZONS:
        dropped_window[h] = sum(
            1 for (sym, i) in events if i + h > len(by_symbol[sym]) - 1)
    cohort = {(sym, i): ev for (sym, i), ev in events.items()
              if i + PRIMARY_H <= len(by_symbol[sym]) - 1}

    # ---- ladder on B-A at the primary horizon --------------------------
    fires_sets = {sym: set(fires_of(rows))
                  for sym, rows in by_symbol.items()}
    excl_sets = {sym: excluded_set(fires_sets[sym], len(rows))
                 for sym, rows in by_symbol.items()}
    ladder_report = []
    pools_by_step = {}
    for step in LADDER:
        pools = {}
        for (sym, i), ev in cohort.items():
            pools[(sym, i)] = eligible_pool(
                by_symbol[sym], excl_sets[sym], ev, step, PRIMARY_H, "B-A")
        pools_by_step[step["step"]] = pools
        dropped = sum(1 for p in pools.values() if len(p) < step["min_pool"])
        ladder_report.append({
            "step": step["step"], "atr_band": step["atr_band"],
            "session_window": step["session_window"],
            "min_pool": step["min_pool"], "events": len(cohort),
            "dropped": dropped,
            "drop_rate": dropped / len(cohort) if cohort else 1.0,
        })
    frozen = next((r for r in ladder_report
                   if r["drop_rate"] <= DROP_FLAG), ladder_report[-1])
    frozen_step = next(s for s in LADDER if s["step"] == frozen["step"])
    flag_over_15 = frozen["drop_rate"] > DROP_FLAG

    pools_ba = pools_by_step[frozen["step"]]
    retained = {(sym, i) for (sym, i), p in pools_ba.items()
                if len(p) >= frozen_step["min_pool"]}

    # ---- B-T at the frozen step (diagnostic; no ladder of its own) -----
    pools_bt = {}
    for (sym, i), ev in cohort.items():
        pools_bt[(sym, i)] = eligible_pool(
            by_symbol[sym], excl_sets[sym], ev, frozen_step, PRIMARY_H,
            "B-T")
    bt_below_min = sum(1 for (sym, i) in retained
                       if len(pools_bt[(sym, i)]) < frozen_step["min_pool"])

    # ---- supplementary h=20 pool counts at the frozen step -------------
    pools_h20 = {}
    for (sym, i), ev in cohort.items():
        pools_h20[(sym, i)] = eligible_pool(
            by_symbol[sym], excl_sets[sym], ev, frozen_step, 20, "B-A")

    # ---- frozen draws (identities only; no returns) --------------------
    draws = {"B-A": {}, "B-T": {}}
    for (sym, i) in sorted(retained):
        draws["B-A"][f"{sym}:{i}"] = event_draws(
            "B-A", sym, i, pools_ba[(sym, i)])
        if len(pools_bt[(sym, i)]) >= frozen_step["min_pool"]:
            draws["B-T"][f"{sym}:{i}"] = event_draws(
                "B-T", sym, i, pools_bt[(sym, i)])

    # ---- event-mix composition of retained events (C14) -----------------
    mix_symbol, mix_bin = {}, {}
    by_idx_all = {sym: {r["idx"]: r for r in rows}
                  for sym, rows in by_symbol.items()}
    for (sym, i) in retained:
        mix_symbol[sym] = mix_symbol.get(sym, 0) + 1
        b = by_idx_all[sym][i]["bin"]
        mix_bin[b] = mix_bin.get(b, 0) + 1

    report = {
        "study": STUDY_ID, "master_seed": MASTER_SEED,
        "census_fires_reconciled": total_fires,
        "declustered_events_total": len(events),
        "events_dropped_forward_window_by_horizon": {
            str(h): dropped_window[h] for h in HORIZONS},
        "cohort_events_primary_h10": len(cohort),
        "ladder": ladder_report,
        "frozen_step": frozen["step"], "drop_flag_over_15pct": flag_over_15,
        "retained_events": len(retained),
        "dropped_events_at_frozen_step": len(cohort) - len(retained),
        "pool_sizes_ba_at_frozen_step": {
            f"{sym}:{i}": len(pools_ba[(sym, i)])
            for (sym, i) in sorted(cohort)},
        "pool_sizes_bt_at_frozen_step": {
            f"{sym}:{i}": len(pools_bt[(sym, i)])
            for (sym, i) in sorted(cohort)},
        "bt_retained_events_below_min_pool": bt_below_min,
        "pool_sizes_ba_h20_at_frozen_step": {
            f"{sym}:{i}": len(pools_h20[(sym, i)])
            for (sym, i) in sorted(cohort)},
        "event_mix_retained_by_symbol": dict(sorted(mix_symbol.items())),
        "event_mix_retained_by_bin": dict(sorted(mix_bin.items())),
        "outcome_blind": "Pool sizes, counts and draw identities only. "
        "No forward return or group difference computed.",
    }
    cohort_out = {
        "study": STUDY_ID,
        "cohort": [{"symbol": sym, "signal_idx": i,
                    "ts": cohort[(sym, i)]["ts"],
                    "bin": cohort[(sym, i)]["bin"]}
                   for (sym, i) in sorted(cohort)],
        "retained": sorted(f"{sym}:{i}" for (sym, i) in retained),
    }
    draws_out = {"study": STUDY_ID, "master_seed": MASTER_SEED,
                 "frozen_step": frozen["step"], "draws": draws}
    return report, cohort_out, draws_out


def compute_forward_returns(*args, **kwargs):
    raise ExecutionGoRequired(
        "EXP-14 returns mode is DISABLED in this pinned version. "
        "Computing forward returns requires the separate execution GO "
        "named in the package MEMO; enabling it is a new version, a "
        "new pin, and that GO.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--inventory-sha", required=True)
    ap.add_argument("--mode", default="pool-counts",
                    choices=("pool-counts", "returns"))
    ap.add_argument("--out-report")
    ap.add_argument("--out-cohort")
    ap.add_argument("--out-draws")
    args = ap.parse_args()
    if args.mode == "returns":
        compute_forward_returns()
    by_symbol = load_inventory(args.inventory, args.inventory_sha)
    report, cohort, draws = run_pool_counts(by_symbol)
    for path, obj in ((args.out_report, report), (args.out_cohort, cohort),
                      (args.out_draws, draws)):
        if path:
            with open(path, "w") as f:
                json.dump(obj, f, indent=1, sort_keys=True)
    print(json.dumps({k: report[k] for k in (
        "census_fires_reconciled", "declustered_events_total",
        "cohort_events_primary_h10", "frozen_step", "retained_events",
        "dropped_events_at_frozen_step", "drop_flag_over_15pct")},
        indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
