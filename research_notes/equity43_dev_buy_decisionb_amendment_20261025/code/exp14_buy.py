"""EXP-14-BUY-DEV-EXPLORATORY — pinned exploratory BUY study script, v3.

SUCCESSOR to the v2 pin in research_notes/
equity43_dev_buy_prep_m1m2_succ1_20261025/ (commit 32dfdb3), built
under DECISION B (Mike, 2026-10-25, chat delivery of record; bridge
commit 243df1a): a prospective amendment for a DEV-only
matched-subpopulation study. The original EXP-14 protocol remains
STOP (step-(c) drop 71/311 = 22.83% > 15%); this version does not
revive it and does not relax any rule. This version changes ONLY the
three implementation items Decision B names:

  ITEM (a) — execution-only price input. Claude prohibited open
      fields in the outcome-blind P7b inventory, and that inventory
      is NOT amended. The section-5 endpoint's entry price (open of
      bar i+1) is now read from a SEPARATE, private, execution-only
      price input derived from the same committed DEV bytes (builder:
      code/build_exec_prices.py; placement: private qf-data-archive
      research_inventory/exp14_exec_prices_20261025/, hash-pinned).
      The analysis reads NO price from the inventory: entry = exec
      input open[i+1]; exit = inventory close[i+h] (a field the
      outcome-blind inventory has always carried); scale = inventory
      ATR[i]. Any missing execution price fails closed.
  ITEM (b) — CLI wiring fixed. The v2 command line called
      compute_forward_returns() with NO arguments, so returns mode
      could never have run. The v3 CLI wires --cohort / --draws /
      --exec-prices (each with its expected SHA-256) and the
      inventory through to the analysis function, and writes
      --out-analysis. Proven by a synthetic CLI end-to-end test
      (fixture inventory + fixture price input -> full pipeline ->
      pinned-schema output) plus a plain-CLI gate test: with
      RETURNS_ENABLED False (this pin), a real CLI returns-mode
      invocation assembles its inputs and is refused by the GO gate
      with NO output written.
  ITEM (c) — reporting completed. The output now carries the
      declared percentage-return views alongside the ATR-unit views
      (per horizon: mean event return and mean paired excess, in
      percent), the declared cost-sensitivity view (preregistration
      v0.3 section 5, H-BUY: costs cancel in the paired difference;
      the descriptive line is primary paired excess in percent minus
      a 25 bps round trip — descriptive only, never a verdict
      input), and a MANDATORY disclosure header (Decision B): the
      eligible / retained / excluded counts and the exclusion rate,
      recomputed from the cohort artifact and fail-closed if the
      supplied disclosure is absent or does not recompute, plus the
      matched-subpopulation-only scope statement. Labels remain DEV
      EXPLORATORY with claim NONE; the script issues no PASS/FAIL.

Study design, pools, ladder, frozen draws, seeds, the complete-window
rule, the endpoint formula, and the inferential basis (ATR-unit
paired excess; wider-of-two bootstrap interval) are UNCHANGED from
v2. The frozen cohort/draws artifacts are carried byte-identical
from the v2 successor package (file SHA-256s pinned in the package
manifest and re-verified by its verifier): cohort 311 events, 240
retained at frozen step (c), 71 excluded (22.83%).

SEEDS (unchanged, pinned before any outcome): MASTER_SEED (draws) =
7715012043445510037; BOOTSTRAP_SEED = 6050949521315240661.

FAIL-CLOSED (analysis): cohort/draws hash mismatch; invalid
inventory keys; non-DEV timestamps; window-incomplete events or
controls; missing forward data; execution-price input hash mismatch,
coverage mismatch (symbols / indices must equal the inventory's
exactly), or a missing/invalid open at any required bar; disclosure
absent or not recomputing from the cohort artifact.
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
COST_RT_BPS = 25  # prereg v0.3 section 5 (H-BUY) descriptive line
RETURNS_ENABLED = False
LADDER = (
    {"step": 0, "atr_band": 0.25, "session_window": 30, "min_pool": 8},
    {"step": "a", "atr_band": 0.40, "session_window": 30, "min_pool": 8},
    {"step": "b", "atr_band": 0.40, "session_window": 45, "min_pool": 8},
    {"step": "c", "atr_band": 0.40, "session_window": 45, "min_pool": 6},
)
DROP_FLAG = 0.15

DECISION_BASIS = (
    "Decision B (Mike, 2026-10-25) — prospective DEV-only "
    "matched-subpopulation amendment; the original EXP-14 protocol "
    "remains STOP; this is a design amendment only and execution "
    "requires Mike's separate authorization")
SCOPE_STATEMENT = (
    "MATCHED SUBPOPULATION ONLY — these results describe only the "
    "events meeting the frozen step-(c) matching criteria (the "
    "retained events). They do NOT describe all Quality Flow BUY "
    "signals, and they establish no validated trading edge.")
STUDY_BASIS = (
    "AMENDED under Decision B (Mike, 2026-10-25): DEV-only "
    "matched-subpopulation descriptive study. The original EXP-14 "
    "protocol remains STOP (step-(c) drop 22.83% > 15%); this "
    "amendment does not revive it, relaxes no rule, and selects "
    "nothing on returns.")


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


def load_exec_prices(path, expected_sha):
    """Load the separate execution-only price input (Decision B item
    (a)): JSONL rows {symbol, idx, ts, open} — nothing else. Returns
    {symbol: {idx: open}}. Hash-pinned; strict row shape; duplicates
    fail closed. Coverage vs the inventory is checked separately by
    validate_exec_prices."""
    got = sha256_file(path)
    if got != expected_sha:
        raise SystemExit(
            f"FAIL-CLOSED: exec-prices sha256 {got} != pinned "
            f"{expected_sha}")
    prices = {}
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            if set(row) != {"symbol", "idx", "ts", "open"}:
                raise FailClosedError(
                    f"exec-prices row shape drift: keys {sorted(row)}")
            sym, idx = row["symbol"], int(row["idx"])
            slot = prices.setdefault(sym, {})
            if idx in slot:
                raise FailClosedError(
                    f"exec-prices duplicate bar {sym}:{idx}")
            slot[idx] = row["open"]
    return prices


def validate_exec_prices(by_symbol, exec_prices):
    """The price input must cover EXACTLY the inventory's bars: same
    symbols, same index sets, every open a positive number."""
    if set(exec_prices) != set(by_symbol):
        raise FailClosedError(
            "exec-prices symbol set != inventory symbol set")
    for sym, rows in by_symbol.items():
        opens = exec_prices[sym]
        if set(opens) != set(range(len(rows))):
            raise FailClosedError(
                f"exec-prices {sym}: index coverage != inventory "
                f"0..{len(rows) - 1}")
        for idx, v in opens.items():
            if v is None or not isinstance(v, (int, float)) or v <= 0:
                raise FailClosedError(
                    f"exec-prices {sym}:{idx}: invalid open {v!r}")
    return True


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
        "study": STUDY_ID, "script_version": 3,
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
        "study": STUDY_ID, "script_version": 3,
        "window_rule": report["window_rule"],
        "cohort": [{"symbol": sym, "signal_idx": i,
                    "ts": cohort[(sym, i)]["ts"],
                    "bin": cohort[(sym, i)]["bin"]}
                   for (sym, i) in sorted(cohort)],
        "retained": sorted(f"{sym}:{i}" for (sym, i) in retained),
    }
    draws_out = {"study": STUDY_ID, "script_version": 3,
                 "master_seed": MASTER_SEED,
                 "frozen_step": frozen["step"], "draws": draws}
    return report, cohort_out, draws_out


# ======================================================================
# Analysis path (Decision B items (a)/(c) applied to the v2 contract).
# Implemented and pinned NOW, exercised ONLY on synthetic fixtures in
# this package. The public entry point compute_forward_returns() is
# gated; _analysis_impl is the locked implementation the gate protects.
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


def build_disclosure(cohort_obj):
    """The Decision B disclosure header, derived from the cohort
    artifact itself: eligible / retained / excluded counts and the
    exclusion rate, plus the pinned scope and basis statements."""
    eligible = len(cohort_obj["cohort"])
    retained = len(cohort_obj["retained"])
    excluded = eligible - retained
    rate = excluded / eligible if eligible else 0.0
    return {
        "decision_basis": DECISION_BASIS,
        "eligible_events": eligible,
        "retained_events_matched": retained,
        "excluded_events_unmatched": excluded,
        "exclusion_rate": rate,
        "exclusion_rate_pct": rate * 100.0,
        "matched_subpopulation_only": True,
        "scope_statement": SCOPE_STATEMENT,
    }


def validate_disclosure(disclosure, cohort_obj):
    """Fail closed unless the disclosure header is present AND its
    counts recompute exactly from the cohort artifact AND its scope /
    basis statements match the pinned Decision B texts. Returns the
    canonical disclosure (as built by build_disclosure)."""
    if not isinstance(disclosure, dict):
        raise FailClosedError(
            "disclosure header absent — Decision B requires the "
            "matched-subpopulation disclosure on every output")
    want = build_disclosure(cohort_obj)
    for k, v in want.items():
        if k not in disclosure:
            raise FailClosedError(f"disclosure header missing '{k}'")
        if isinstance(v, float):
            if abs(disclosure[k] - v) > 1e-12:
                raise FailClosedError(
                    f"disclosure '{k}' does not recompute from the "
                    f"cohort artifact ({disclosure[k]} != {v})")
        elif disclosure[k] != v:
            raise FailClosedError(
                f"disclosure '{k}' drift ({disclosure[k]!r} != {v!r})")
    return want


def forward_return(rows, opens, i, h):
    """Section-5 endpoint: (close[i+h] - open[i+1]) / atr[i], plus the
    percent return. The entry open comes from the separate
    execution-only price input (Decision B item (a)) — never from the
    inventory, which carries no open field. Fail closed on any
    missing forward datum or execution price."""
    n = len(rows)
    if i + h > n - 1 or i + 1 > n - 1:
        raise FailClosedError(
            f"forward window incomplete for idx {i} at h={h} (n={n})")
    sig, exit_bar = rows[i], rows[i + h]
    for bar, field in ((sig, "atr"), (exit_bar, "close")):
        if field not in bar or bar[field] is None:
            raise FailClosedError(
                f"missing forward data: field '{field}' absent/None at "
                f"idx {bar.get('idx')}")
    if i + 1 not in opens:
        raise FailClosedError(
            f"missing execution price: no open for idx {i + 1} in the "
            "execution-only price input")
    entry = opens[i + 1]
    if entry is None or not isinstance(entry, (int, float)) \
            or entry <= 0:
        raise FailClosedError(
            f"invalid execution price at idx {i + 1}: {entry!r}")
    atr = sig["atr"]
    if atr == 0:
        raise FailClosedError(f"zero ATR at idx {i}")
    exit_ = exit_bar["close"]
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


def _analysis_impl(by_symbol, exec_prices, cohort_obj, draws_obj,
                   expected_cohort_sha, expected_draws_sha,
                   disclosure=None, reps=BOOTSTRAP_REPS):
    """The locked EXP-14 analysis (v3: Decision B items (a) and (c)).
    Pure function of its inputs; in this pin it is called ONLY by the
    synthetic test suite. The disclosure header is mandatory and is
    validated against the cohort artifact before any return is
    computed."""
    if canonical_sha(cohort_obj) != expected_cohort_sha:
        raise FailClosedError("cohort artifact hash mismatch")
    if canonical_sha(draws_obj) != expected_draws_sha:
        raise FailClosedError("draws artifact hash mismatch")
    validate_inventory(by_symbol)
    validate_exec_prices(by_symbol, exec_prices)
    disclosure = validate_disclosure(disclosure, cohort_obj)
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
    retained = []
    for k in cohort_obj["retained"]:
        sym, idx = k.rsplit(":", 1)
        retained.append((sym, int(idx)))
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
    primary_pct_mean = None
    bt_items, bt_pcts = [], []
    for h in HORIZONS:
        ev_atr, ev_pct, ex_atr, ex_pct = [], [], [], []
        for (sym, i) in sorted(retained):
            rows, opens = by_symbol[sym], exec_prices[sym]
            er = forward_return(rows, opens, i, h)
            ctrls = [forward_return(rows, opens, int(j), h)
                     for j in draws["B-A"][f"{sym}:{i}"]]
            ev_atr.append(er["atr_units"])
            ev_pct.append(er["pct"])
            ex_atr.append(er["atr_units"]
                          - float(np.mean([c["atr_units"]
                                           for c in ctrls])))
            ex_pct.append(er["pct"]
                          - float(np.mean([c["pct"] for c in ctrls])))
            if h == PRIMARY_H:
                primary_items.append(
                    (cohort[(sym, i)]["session_ordinal"], ex_atr[-1]))
                primary_by_symbol.setdefault(sym, []).append(ex_atr[-1])
        per_h[str(h)] = {
            "n_events": len(retained),
            "mean_event_return_atr": float(np.mean(ev_atr)),
            "mean_event_return_pct": float(np.mean(ev_pct)),
            "mean_paired_excess_atr": float(np.mean(ex_atr)),
            "mean_paired_excess_pct": float(np.mean(ex_pct)),
        }
        if h == PRIMARY_H:
            primary_pct_mean = per_h[str(h)]["mean_paired_excess_pct"]
    for (sym, i) in sorted(retained):
        if f"{sym}:{i}" in draws.get("B-T", {}):
            rows, opens = by_symbol[sym], exec_prices[sym]
            er = forward_return(rows, opens, i, PRIMARY_H)
            ctrls = [forward_return(rows, opens, int(j), PRIMARY_H)
                     for j in draws["B-T"][f"{sym}:{i}"]]
            bt_items.append(er["atr_units"] - float(
                np.mean([c["atr_units"] for c in ctrls])))
            bt_pcts.append(er["pct"] - float(
                np.mean([c["pct"] for c in ctrls])))

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
        "study_basis": STUDY_BASIS,
        "disclosure": disclosure,
        "master_seed": MASTER_SEED, "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": reps, "block_sessions": BLOCK_SESSIONS,
        "horizons": {h: per_h[h] for h in per_h},
        "primary_horizon": PRIMARY_H,
        "primary_paired_excess": {
            "n": len(primary_items),
            "mean_atr": float(np.mean(xs)),
            "mean_pct": primary_pct_mean,
            "block_bootstrap": block,
            "cluster_bootstrap": cluster,
            "interval_used": used_name,
            "interval_lower_95": used["lower_95"],
            "interval_upper_95": used["upper_95"],
            "design_effect": design_effect,
            "n_eff": (len(xs) / design_effect) if design_effect
                     else None,
        },
        "cost_sensitivity": {
            "declared_basis": "preregistration v0.3 section 5 (H-BUY): "
                              "costs cancel in the paired difference; "
                              "this descriptive line is reported so a "
                              "reader can see whether the effect clears "
                              "a cost — it is never a verdict input",
            "round_trip_bps": COST_RT_BPS,
            "primary_paired_excess_pct": primary_pct_mean,
            "primary_paired_excess_pct_minus_round_trip": (
                primary_pct_mean - COST_RT_BPS / 10000.0),
        },
        "bt_diagnostic": {
            "n": len(bt_items),
            "mean_paired_excess_atr": float(np.mean(bt_items))
            if bt_items else None,
            "mean_paired_excess_pct": float(np.mean(bt_pcts))
            if bt_pcts else None,
            "gating": False,
        },
    }


def compute_forward_returns(by_symbol=None, exec_prices=None,
                            cohort_obj=None, draws_obj=None,
                            expected_cohort_sha=None,
                            expected_draws_sha=None, disclosure=None,
                            reps=BOOTSTRAP_REPS):
    """TOP-LEVEL GATE (Decision B): the analysis path above is
    implemented and pinned, but executing it on real data requires
    Mike's SEPARATE execution authorization — Decision B approves the
    design amendment only. RETURNS_ENABLED is False in this pin;
    enabling it is a new version + new pin + that authorization.
    """
    if not RETURNS_ENABLED:
        raise ExecutionGoRequired(
            "EXP-14 returns mode is gated in this pinned version. "
            "Decision B approves the amended design only; computing "
            "forward returns on real data requires Mike's separate "
            "execution authorization, a new pinned version, and this "
            "gate flipped in that version.")
    missing = [k for k, v in (
        ("by_symbol", by_symbol), ("exec_prices", exec_prices),
        ("cohort_obj", cohort_obj), ("draws_obj", draws_obj),
        ("expected_cohort_sha", expected_cohort_sha),
        ("expected_draws_sha", expected_draws_sha),
        ("disclosure", disclosure)) if v is None]
    if missing:
        raise FailClosedError(
            f"returns mode called without required arguments: {missing}")
    return _analysis_impl(by_symbol, exec_prices, cohort_obj, draws_obj,
                          expected_cohort_sha, expected_draws_sha,
                          disclosure=disclosure, reps=reps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--inventory-sha", required=True)
    ap.add_argument("--mode", default="pool-counts",
                    choices=("pool-counts", "returns"))
    ap.add_argument("--out-report")
    ap.add_argument("--out-cohort")
    ap.add_argument("--out-draws")
    # Returns-mode wiring (Decision B item (b)): every input the
    # analysis function requires is an explicit CLI argument with its
    # expected SHA-256.
    ap.add_argument("--cohort")
    ap.add_argument("--cohort-sha")
    ap.add_argument("--draws")
    ap.add_argument("--draws-sha")
    ap.add_argument("--exec-prices")
    ap.add_argument("--exec-prices-sha")
    ap.add_argument("--out-analysis")
    args = ap.parse_args()

    if args.mode == "returns":
        missing = [f for f, v in (
            ("--cohort", args.cohort), ("--cohort-sha", args.cohort_sha),
            ("--draws", args.draws), ("--draws-sha", args.draws_sha),
            ("--exec-prices", args.exec_prices),
            ("--exec-prices-sha", args.exec_prices_sha),
            ("--out-analysis", args.out_analysis)) if not v]
        if missing:
            ap.error(f"--mode returns requires: {', '.join(missing)}")
        if sha256_file(args.cohort) != args.cohort_sha:
            print("FAIL-CLOSED: cohort file sha256 != --cohort-sha",
                  file=sys.stderr)
            return 2
        if sha256_file(args.draws) != args.draws_sha:
            print("FAIL-CLOSED: draws file sha256 != --draws-sha",
                  file=sys.stderr)
            return 2
        by_symbol = load_inventory(args.inventory, args.inventory_sha)
        exec_prices = load_exec_prices(args.exec_prices,
                                       args.exec_prices_sha)
        with open(args.cohort) as f:
            cohort_obj = json.load(f)
        with open(args.draws) as f:
            draws_obj = json.load(f)
        disclosure = build_disclosure(cohort_obj)
        try:
            result = compute_forward_returns(
                by_symbol=by_symbol, exec_prices=exec_prices,
                cohort_obj=cohort_obj, draws_obj=draws_obj,
                expected_cohort_sha=canonical_sha(cohort_obj),
                expected_draws_sha=canonical_sha(draws_obj),
                disclosure=disclosure)
        except ExecutionGoRequired as e:
            print(f"GO GATE: {e}", file=sys.stderr)
            return 3
        except FailClosedError as e:
            print(f"FAIL-CLOSED: {e}", file=sys.stderr)
            return 2
        with open(args.out_analysis, "w") as f:
            json.dump(result, f, indent=1, sort_keys=True)
        print(json.dumps({"analysis_written": args.out_analysis,
                          "label": result["label"],
                          "claim": result["claim"]}))
        return 0

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
