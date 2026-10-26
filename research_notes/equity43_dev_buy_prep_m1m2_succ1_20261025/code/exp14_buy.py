"""EXP-14-BUY-DEV-EXPLORATORY — pinned exploratory BUY study script, v2.

SUCCESSOR to the v1 pin in research_notes/equity43_dev_buy_prep_m1m2_20261025/
(commit 5e02503), built under the independent review in Issue #1 comment
6405786931 (P-1 ACCEPTED for DEV; EXP-14 execution HOLD on three bounded
items). This version changes ONLY what that review prescribes:

  ITEM 1 — single complete-window rule. v1 froze the cohort and the pool
      eligibility on the PRIMARY horizon's window (h=10), so events and
      drawn controls could lack a complete h=20 outcome. v2 pins ONE
      rule for every horizon: an event bar or a control bar is eligible
      only if its full MAX_H=20 forward window lies inside the data
      (idx + 20 <= n - 1). Cohort and all draws are re-derived under
      this rule, outcome-blind. No control is silently omitted: pools
      are computed under the rule before any draw exists.
  ITEM 2 — the executable analysis contract is FINISHED and pinned here
      (forward returns, paired excess, circular block bootstrap over
      calendar time with 20-session blocks, symbol-cluster bootstrap,
      wider-of-two interval rule, output schema), exercised ONLY on
      synthetic fixtures by the test suite. The top-level entry point
      compute_forward_returns() stays behind the GO gate
      (RETURNS_ENABLED is False in this pin; flipping it is a new
      version + new pin + the separate execution GO). The analysis
      fails closed on: non-DEV timestamps, invalid inventory keys,
      missing forward data (including a missing 'open' field — the
      preregistered endpoint is entry = open of bar i+1), and cohort /
      draw hash mismatches.
  ITEM 3 — the step-(c) drop rate is RECOMPUTED on the corrected
      cohort in the package artifacts and reported in the MEMO. The
      >15% question is a governance decision for the user; this script
      takes no position on it.

SEEDS (reconciled and pinned BEFORE any outcome, per review item 2):
  MASTER_SEED (draws) = first 8 bytes (big-endian) of
      SHA-256("EXP-14-BUY-DEV-EXPLORATORY") = 7715012043445510037
      (unchanged from v1 — the frozen draws the review verified were
      derived under it).
  BOOTSTRAP_SEED = first 8 bytes (big-endian) of
      SHA-256(f"{MASTER_SEED}:bootstrap") = 6050949521315240661.
  The cluster bootstrap derives its stream from BOOTSTRAP_SEED via the
  same sub-seed convention (f"{BOOTSTRAP_SEED}:cluster").
  Alternatives considered and NOT adopted for EXP-14 (recorded in the
  package MEMO): seed = SHA-256 of the preregistration (v0.3 section 6
  [C10] / frozen contract fc17041) — the v0.3 preregistration is an
  UNFROZEN draft (freeze HOLD), so its hash is not fixed today; and
  seed = SHA-256 of this script (Claude final-gate p.9) — the script
  hash changes with the very version bump that would enable returns,
  so pin and execution would carry different seeds. The study-ID seed
  family is invariant across versions and amendments.

STUDY DESIGN (unchanged from v1 / preregistration v0.3 section 5):
  EVENTS      generator-domain fires, de-clustered (no signal bar of
              the same symbol in the previous 20 bars).
  B-A POOL    same symbol; same bin; session ordinal within the ladder
              step's window; no signal bar within +/-20 bars; ATR%
              within the step's relative band; complete-window rule.
  B-T POOL    B-A + Close > EMA200, EMA21 > EMA55, signal false
              (non-gating sparse diagnostic).
  LADDER      step 0 base (+/-25%, +/-30 sessions, min pool 8) ->
              (a) ATR% +/-40% -> (b) +/-45 sessions -> (c) min pool 6.
              Frozen at the first step with drop rate <= 15%; if the
              ladder exhausts, the last step is frozen and the >15%
              flag is recorded (the flag's consequence is governance,
              item 3 — never a silent in-script decision).
  DRAWS       min(20, pool size) without replacement per retained
              event — i.e. ALL AVAILABLE controls when the pool holds
              6-19 (P-1 acceptance record, comment 6405786931).
  HORIZONS    5 / 10 / 20 bars; 10 primary. Horizons differ only in
              the exit bar; eligibility never differs by horizon.
  Interpretation P-1 (ACCEPTED, recorded): pool bars are restricted to
              the generator domain — an intentional section-5
              interpretation, not to be switched later based on returns.

ENDPOINT (section 5, execution time only): forward return of bar i at
horizon h = (close[i+h] - open[i+1]) / atr[i]; percent return reported
alongside. Paired excess = event return minus the mean return of its
drawn B-A controls (B-T diagnostic likewise where a B-T draw exists).

FAIL-CLOSED (pool-counts mode, as v1): inventory SHA-256 must match
--inventory-sha; the domain fire census must reconcile to 2,892 before
any cohort work; missing indicator fields exclude a bar from pools and
are counted, never imputed.
"""
import argparse
import hashlib
import json
import sys

import numpy as np

STUDY_ID = "EXP-14-BUY-DEV-EXPLORATORY"
MASTER_SEED = int.from_bytes(
    hashlib.sha256(STUDY_ID.encode()).digest()[:8], "big")
PINNED_MASTER_SEED = 7715012043445510037
BOOTSTRAP_SEED = int.from_bytes(hashlib.sha256(
    f"{MASTER_SEED}:bootstrap".encode()).digest()[:8], "big")
PINNED_BOOTSTRAP_SEED = 6050949521315240661
HORIZONS = (5, 10, 20)
PRIMARY_H = 10
MAX_H = 20
DECLUSTER_BARS = 20
EXCLUSION_BARS = 20
DRAW_N = 20
EXPECTED_FIRES = 2892
DEV_START = "2024-09-16"
DEV_END = "2026-10-16"
BOOTSTRAP_REPS = 10000
BLOCK_SESSIONS = 20
RETURNS_ENABLED = False
LADDER = (
    {"step": 0, "atr_band": 0.25, "session_window": 30, "min_pool": 8},
    {"step": "a", "atr_band": 0.40, "session_window": 30, "min_pool": 8},
    {"step": "b", "atr_band": 0.40, "session_window": 45, "min_pool": 8},
    {"step": "c", "atr_band": 0.40, "session_window": 45, "min_pool": 6},
)
DROP_FLAG = 0.15


class ExecutionGoRequired(RuntimeError):
    pass


class FailClosedError(RuntimeError):
    pass


if MASTER_SEED != PINNED_MASTER_SEED or BOOTSTRAP_SEED \
        != PINNED_BOOTSTRAP_SEED:
    raise FailClosedError(
        "seed drift: derived seeds do not match the pinned literals "
        f"(master {MASTER_SEED}, bootstrap {BOOTSTRAP_SEED})")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


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
    kept = []
    fire_set = set(fires)
    for i in fires:
        if not any(j in fire_set for j in range(i - DECLUSTER_BARS, i)):
            kept.append(i)
    return kept


def excluded_set(fires_set, n):
    """Bars within +/-EXCLUSION_BARS of any signal bar (inclusive)."""
    out = set()
    for f in fires_set:
        out.update(range(max(0, f - EXCLUSION_BARS),
                         min(n - 1, f + EXCLUSION_BARS) + 1))
    return out


def window_complete(idx, n):
    """THE single complete-window rule (review item 1): the full
    MAX_H-bar forward window lies inside the data."""
    return idx + MAX_H <= n - 1


def eligible_pool(rows, excl, event, step, arm):
    """B-A / B-T eligible pool bar indices for one event at a ladder
    step, under the single complete-window rule. Pure function of
    inventory fields — no forward returns."""
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
        if not window_complete(j, n):
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
    """Deterministic per-event draw without replacement: the whole
    pool when it holds fewer than DRAW_N bars (all available)."""
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

    events = {}          # (symbol, idx) -> event row (de-clustered)
    dropped_window = {}  # horizon -> de-clustered events dropped at h
    for sym, rows in by_symbol.items():
        by_idx = {r["idx"]: r for r in rows}
        for i in decluster(fires_of(rows)):
            events[(sym, i)] = by_idx[i]
    for h in HORIZONS:
        dropped_window[h] = sum(
            1 for (sym, i) in events if i + h > len(by_symbol[sym]) - 1)
    # Single rule: the cohort is what survives the MAX_H window.
    cohort = {(sym, i): ev for (sym, i), ev in events.items()
              if window_complete(i, len(by_symbol[sym]))}

    # ---- ladder on B-A under the single rule ---------------------------
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
                by_symbol[sym], excl_sets[sym], ev, step, "B-A")
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
            by_symbol[sym], excl_sets[sym], ev, frozen_step, "B-T")
    bt_below_min = sum(1 for (sym, i) in retained
                       if len(pools_bt[(sym, i)]) < frozen_step["min_pool"])

    # ---- frozen draws (identities only; no returns) --------------------
    draws = {"B-A": {}, "B-T": {}}
    for (sym, i) in sorted(retained):
        draws["B-A"][f"{sym}:{i}"] = event_draws(
            "B-A", sym, i, pools_ba[(sym, i)])
        if len(pools_bt[(sym, i)]) >= frozen_step["min_pool"]:
            draws["B-T"][f"{sym}:{i}"] = event_draws(
                "B-T", sym, i, pools_bt[(sym, i)])
    ba_groups = draws["B-A"]
    ba_full_20 = sum(1 for d in ba_groups.values() if len(d) == DRAW_N)
    ba_all_available = sum(1 for d in ba_groups.values()
                           if len(d) < DRAW_N)

    # ---- event-mix composition of retained events (C14) -----------------
    mix_symbol, mix_bin = {}, {}
    by_idx_all = {sym: {r["idx"]: r for r in rows}
                  for sym, rows in by_symbol.items()}
    for (sym, i) in retained:
        mix_symbol[sym] = mix_symbol.get(sym, 0) + 1
        b = by_idx_all[sym][i]["bin"]
        mix_bin[b] = mix_bin.get(b, 0) + 1

    report = {
        "study": STUDY_ID, "script_version": 2,
        "master_seed": MASTER_SEED, "bootstrap_seed": BOOTSTRAP_SEED,
        "window_rule": "single complete-window rule (review item 1): "
        "an event or control bar is eligible only if idx + 20 <= n - 1 "
        "(full h=20 window inside the data); identical for h=5/10/20",
        "census_fires_reconciled": total_fires,
        "declustered_events_total": len(events),
        "events_dropped_forward_window_by_horizon": {
            str(h): dropped_window[h] for h in HORIZONS},
        "cohort_events_single_rule_h20": len(cohort),
        "ladder": ladder_report,
        "frozen_step": frozen["step"], "drop_flag_over_15pct": flag_over_15,
        "retained_events": len(retained),
        "dropped_events_at_frozen_step": len(cohort) - len(retained),
        "step_c_drop_rate": next(
            r["drop_rate"] for r in ladder_report if r["step"] == "c"),
        "step_c_dropped": next(
            r["dropped"] for r in ladder_report if r["step"] == "c"),
        "ba_draw_groups": len(ba_groups),
        "ba_groups_with_full_20_draws": ba_full_20,
        "ba_groups_all_available_below_20": ba_all_available,
        "bt_viable_groups": len(draws["B-T"]),
        "pool_sizes_ba_at_frozen_step": {
            f"{sym}:{i}": len(pools_ba[(sym, i)])
            for (sym, i) in sorted(cohort)},
        "pool_sizes_bt_at_frozen_step": {
            f"{sym}:{i}": len(pools_bt[(sym, i)])
            for (sym, i) in sorted(cohort)},
        "bt_retained_events_below_min_pool": bt_below_min,
        "event_mix_retained_by_symbol": dict(sorted(mix_symbol.items())),
        "event_mix_retained_by_bin": dict(sorted(mix_bin.items())),
        "outcome_blind": "Pool sizes, counts and draw identities only. "
        "No forward return or group difference computed.",
    }
    cohort_out = {
        "study": STUDY_ID, "script_version": 2,
        "window_rule": report["window_rule"],
        "cohort": [{"symbol": sym, "signal_idx": i,
                    "ts": cohort[(sym, i)]["ts"],
                    "bin": cohort[(sym, i)]["bin"]}
                   for (sym, i) in sorted(cohort)],
        "retained": sorted(f"{sym}:{i}" for (sym, i) in retained),
    }
    draws_out = {"study": STUDY_ID, "script_version": 2,
                 "master_seed": MASTER_SEED,
                 "frozen_step": frozen["step"], "draws": draws}
    return report, cohort_out, draws_out


# ======================================================================
# Analysis path (review item 2). Implemented and pinned NOW, exercised
# ONLY on synthetic fixtures in this package. The public entry point
# compute_forward_returns() is gated; _analysis_impl is the locked
# implementation the gate protects.
# ======================================================================

REQUIRED_ROW_KEYS = ("symbol", "idx", "ts", "session_date",
                     "session_ordinal", "bin", "close", "atr",
                     "atr_pct", "ema21", "ema55", "ema200", "signal",
                     "in_generator_domain")


def _check_dev_ts(row, what):
    d = str(row.get("session_date", ""))[:10]
    if not (DEV_START <= d <= DEV_END):
        raise FailClosedError(
            f"non-DEV timestamp on {what}: {row.get('symbol')}:"
            f"{row.get('idx')} session_date {d} outside "
            f"[{DEV_START}, {DEV_END}]")


def validate_inventory(by_symbol):
    """Fail closed on invalid inventory structure/keys."""
    for sym, rows in by_symbol.items():
        if [r["idx"] for r in rows] != list(range(len(rows))):
            raise FailClosedError(
                f"inventory {sym}: idx sequence not contiguous 0..n-1")
        for r in rows:
            missing = [k for k in REQUIRED_ROW_KEYS if k not in r]
            if missing:
                raise FailClosedError(
                    f"inventory {sym}:{r.get('idx')}: missing keys "
                    f"{missing}")
            if r["symbol"] != sym:
                raise FailClosedError(
                    f"inventory key mismatch: row symbol {r['symbol']} "
                    f"under {sym}")
    return True


def forward_return(rows, i, h):
    """Section-5 endpoint: (close[i+h] - open[i+1]) / atr[i], plus the
    percent return. Fail closed on any missing forward datum — the
    pinned P7b inventory carries no 'open' field, so on that inventory
    this raises by design rather than substituting another price."""
    n = len(rows)
    if i + h > n - 1 or i + 1 > n - 1:
        raise FailClosedError(
            f"forward window incomplete for idx {i} at h={h} (n={n})")
    sig, entry_bar, exit_bar = rows[i], rows[i + 1], rows[i + h]
    for bar, field in ((sig, "atr"), (entry_bar, "open"),
                       (exit_bar, "close")):
        if field not in bar or bar[field] is None:
            raise FailClosedError(
                f"missing forward data: field '{field}' absent/None at "
                f"idx {bar.get('idx')}")
    atr = sig["atr"]
    if atr == 0:
        raise FailClosedError(f"zero ATR at idx {i}")
    entry, exit_ = entry_bar["open"], exit_bar["close"]
    return {"atr_units": (exit_ - entry) / atr,
            "pct": (exit_ - entry) / entry}


def _sub_seed(tag):
    return int.from_bytes(hashlib.sha256(
        f"{BOOTSTRAP_SEED}:{tag}".encode()).digest()[:8], "big")


def circular_block_bootstrap(items, reps=BOOTSTRAP_REPS,
                             block_sessions=BLOCK_SESSIONS, seed=None):
    """Circular block bootstrap over calendar time. items: list of
    (session_ordinal, value). Blocks are block_sessions consecutive
    session ordinals on the circular ordinal axis [min, max]; a block
    contributes every value whose ordinal it covers. Returns the
    percentile interval and resample-mean distribution summary."""
    if not items:
        raise FailClosedError("bootstrap: no items")
    if seed is None:
        seed = BOOTSTRAP_SEED
    ords = sorted({o for o, _ in items})
    lo, hi = ords[0], ords[-1]
    span = hi - lo + 1
    by_ord = {}
    for o, v in items:
        by_ord.setdefault(o, []).append(v)
    n = len(items)
    rng = np.random.default_rng(np.random.PCG64(seed))
    means = np.empty(reps)
    blocks_used = np.empty(reps)
    for r in range(reps):
        vals, nb = [], 0
        while len(vals) < n:
            start = ords[int(rng.integers(0, len(ords)))]
            nb += 1
            for k in range(block_sessions):
                o = lo + ((start - lo + k) % span)
                vals.extend(by_ord.get(o, ()))
        blocks_used[r] = nb
        means[r] = float(np.mean(vals[:n]))
    return {"lower_95": float(np.percentile(means, 5)),
            "upper_95": float(np.percentile(means, 95)),
            "resample_mean": float(np.mean(means)),
            "resample_var": float(np.var(means, ddof=1)),
            "mean_blocks_per_rep": float(np.mean(blocks_used)),
            "reps": reps}


def cluster_bootstrap(items_by_symbol, reps=BOOTSTRAP_REPS, seed=None):
    """Symbol-cluster bootstrap: resample symbols with replacement,
    take all of each drawn symbol's values (with multiplicity)."""
    syms = sorted(items_by_symbol)
    if not syms:
        raise FailClosedError("cluster bootstrap: no symbols")
    if seed is None:
        seed = _sub_seed("cluster")
    rng = np.random.default_rng(np.random.PCG64(seed))
    means = np.empty(reps)
    for r in range(reps):
        vals = []
        for _ in syms:
            vals.extend(items_by_symbol[syms[int(
                rng.integers(0, len(syms)))]])
        means[r] = float(np.mean(vals))
    return {"lower_95": float(np.percentile(means, 5)),
            "upper_95": float(np.percentile(means, 95)),
            "resample_mean": float(np.mean(means)),
            "resample_var": float(np.var(means, ddof=1)),
            "clusters": len(syms), "reps": reps}


def _wider(a, b):
    wa = a["upper_95"] - a["lower_95"]
    wb = b["upper_95"] - b["lower_95"]
    return ("block", a) if wa >= wb else ("cluster", b)


def _analysis_impl(by_symbol, cohort_obj, draws_obj,
                   expected_cohort_sha, expected_draws_sha,
                   reps=BOOTSTRAP_REPS):
    """The locked EXP-14 analysis. Pure function of its inputs; in
    this pin it is called ONLY by the synthetic test suite."""
    if canonical_sha(cohort_obj) != expected_cohort_sha:
        raise FailClosedError("cohort artifact hash mismatch")
    if canonical_sha(draws_obj) != expected_draws_sha:
        raise FailClosedError("draws artifact hash mismatch")
    validate_inventory(by_symbol)
    by_idx = {sym: {r["idx"]: r for r in rows}
              for sym, rows in by_symbol.items()}

    cohort = {}
    for c in cohort_obj["cohort"]:
        sym, i = c["symbol"], int(c["signal_idx"])
        row = by_idx.get(sym, {}).get(i)
        if row is None:
            raise FailClosedError(f"cohort event {sym}:{i} not in "
                                  "inventory")
        _check_dev_ts(row, "cohort event")
        if not row["signal"] or not row["in_generator_domain"]:
            raise FailClosedError(f"cohort event {sym}:{i} is not a "
                                  "generator-domain fire")
        if not window_complete(i, len(by_symbol[sym])):
            raise FailClosedError(f"cohort event {sym}:{i} lacks a "
                                  "complete h=20 window")
        cohort[(sym, i)] = row
    retained = [tuple(k.rsplit(":", 1)[0:1] + [int(k.rsplit(":", 1)[1])])
                for k in cohort_obj["retained"]]
    retained = [(k[0], k[1]) for k in retained]
    for key in retained:
        if key not in cohort:
            raise FailClosedError(f"retained event {key} not in cohort")

    draws = draws_obj["draws"]
    for arm in ("B-A", "B-T"):
        for key, idxs in draws.get(arm, {}).items():
            sym, i = key.rsplit(":", 1)[0], int(key.rsplit(":", 1)[1])
            if (sym, i) not in cohort:
                raise FailClosedError(f"{arm} draw group {key} has no "
                                      "cohort event")
            for j in idxs:
                row = by_idx.get(sym, {}).get(int(j))
                if row is None:
                    raise FailClosedError(f"{arm} draw {sym}:{j} not "
                                          "in inventory")
                _check_dev_ts(row, f"{arm} control")
                if not window_complete(int(j), len(by_symbol[sym])):
                    raise FailClosedError(
                        f"{arm} control {sym}:{j} lacks a complete "
                        "h=20 window")

    per_h = {}
    primary_items, primary_by_symbol = [], {}
    bt_items = []
    for h in HORIZONS:
        ev_rets, excesses = [], []
        for (sym, i) in sorted(retained):
            rows = by_symbol[sym]
            er = forward_return(rows, i, h)["atr_units"]
            ctrls = [forward_return(rows, int(j), h)["atr_units"]
                     for j in draws["B-A"][f"{sym}:{i}"]]
            ex = er - float(np.mean(ctrls))
            ev_rets.append(er)
            excesses.append(ex)
            if h == PRIMARY_H:
                primary_items.append(
                    (cohort[(sym, i)]["session_ordinal"], ex))
                primary_by_symbol.setdefault(sym, []).append(ex)
        per_h[str(h)] = {
            "n_events": len(retained),
            "mean_event_return_atr": float(np.mean(ev_rets)),
            "mean_paired_excess_atr": float(np.mean(excesses)),
        }
    for (sym, i) in sorted(retained):
        if f"{sym}:{i}" in draws.get("B-T", {}):
            rows = by_symbol[sym]
            er = forward_return(rows, i, PRIMARY_H)["atr_units"]
            ctrls = [forward_return(rows, int(j), PRIMARY_H)["atr_units"]
                     for j in draws["B-T"][f"{sym}:{i}"]]
            bt_items.append(er - float(np.mean(ctrls)))

    block = circular_block_bootstrap(primary_items, reps=reps)
    cluster = cluster_bootstrap(primary_by_symbol, reps=reps)
    used_name, used = _wider(block, cluster)
    xs = np.array([v for _, v in primary_items], dtype=float)
    var_iid_mean = float(np.var(xs, ddof=1) / len(xs)) if len(xs) > 1 \
        else 0.0
    design_effect = (cluster["resample_var"] / var_iid_mean) \
        if var_iid_mean > 0 else None
    return {
        "study": STUDY_ID,
        "label": "DEV EXPLORATORY",
        "claim": "NONE",
        "verdict": "NONE — estimates and intervals only; this script "
                   "issues no PASS/FAIL and no edge claim",
        "master_seed": MASTER_SEED, "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": reps, "block_sessions": BLOCK_SESSIONS,
        "horizons": {h: per_h[h] for h in per_h},
        "primary_horizon": PRIMARY_H,
        "primary_paired_excess": {
            "n": len(primary_items),
            "mean_atr": float(np.mean(xs)),
            "block_bootstrap": block,
            "cluster_bootstrap": cluster,
            "interval_used": used_name,
            "interval_lower_95": used["lower_95"],
            "interval_upper_95": used["upper_95"],
            "design_effect": design_effect,
            "n_eff": (len(xs) / design_effect) if design_effect
                     else None,
        },
        "bt_diagnostic": {
            "n": len(bt_items),
            "mean_paired_excess_atr": float(np.mean(bt_items))
            if bt_items else None,
            "gating": False,
        },
    }


def compute_forward_returns(*args, **kwargs):
    """TOP-LEVEL GATE (review item 2): the analysis path above is
    implemented and pinned, but executing it on real data requires the
    separate execution GO named in the package MEMO. RETURNS_ENABLED
    is False in this pin; enabling it is a new version + new pin + GO.
    """
    if not RETURNS_ENABLED:
        raise ExecutionGoRequired(
            "EXP-14 returns mode is gated in this pinned version. "
            "Computing forward returns on real data requires the "
            "separate execution GO named in the package MEMO; "
            "enabling it is a new version, a new pin, and that GO.")
    return _analysis_impl(*args, **kwargs)


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
        "cohort_events_single_rule_h20", "frozen_step", "retained_events",
        "dropped_events_at_frozen_step", "step_c_drop_rate",
        "drop_flag_over_15pct")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
