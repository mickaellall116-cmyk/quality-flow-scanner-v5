"""Static tests + synthetic fixtures for PREREGISTRATION_20261018_25.

SYNTHETIC_FIXTURE data only: a generated session calendar, per-trade R
values, and daily returns, all from fixed arithmetic formulas. No market
data, no real strategy outcomes, no restored strategy module is imported
or run. Run: python3 test_prereg_finalization.py -> writes TEST_RESULTS.json
and exits 0 only if every check passes. The full fixture computation is
executed twice and the two result digests must be byte-identical.
"""

import ast
import hashlib
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fold_materializer as fm
import inference_layer as il

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append({"test": name, "pass": bool(cond), "detail": detail})
    return cond


def expect_error(name, code, fn):
    try:
        fn()
    except fm.MaterializerError as e:
        return check(name, e.code == code, f"got {e.code}")
    return check(name, False, "no error raised")


# ---------- SYNTHETIC_FIXTURE session calendar ----------
FIXTURE_START = date(2024, 9, 16)
FIXTURE_HOLIDAYS = {date(2024, 11, 28), date(2024, 12, 25), date(2025, 1, 1)}
FIXTURE_SESSIONS = 252 + 63 * 3 + 40  # 3 full folds + a 40-session dropped tail


def fixture_calendar(n_sessions):
    days, d = [], FIXTURE_START
    while len(days) < n_sessions:
        if d.weekday() < 5 and d not in FIXTURE_HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    ts = [f"{day.isoformat()}T{t}" for day in days for t in ("09:30", "13:30")]
    return days, ts


def run_all():
    days, ts = fixture_calendar(FIXTURE_SESSIONS)
    holiday_strs = {d.isoformat() for d in FIXTURE_HOLIDAYS}

    # 1. Timestamp-only access: materializer signature + import surface.
    import inspect
    params = list(inspect.signature(fm.materialize).parameters)
    check("timestamp_only_signature", params == ["timestamps", "declared_holidays"], str(params))
    tree = ast.parse((HERE / "fold_materializer.py").read_text())
    imports = sorted(
        (n.module if isinstance(n, ast.ImportFrom) else a.name)
        for node in ast.walk(tree)
        for n in ([node] if isinstance(node, (ast.Import, ast.ImportFrom)) else [])
        for a in (n.names if isinstance(n, ast.Import) else [n])
    )
    check("materializer_stdlib_imports_only",
          set(imports) <= {"hashlib", "json", "datetime"}, str(imports))
    expect_error("rejects_non_string_timestamp", "MALFORMED_TIMESTAMP",
                 lambda: fm.materialize([{"day": "2024-09-16", "o": 1.0}]))

    # 2. Happy path + fold shape.
    out = fm.materialize(ts, holiday_strs)
    check("fold_count_3", len(out["folds"]) == 3, str(len(out["folds"])))
    check("dropped_tail_40", out["dropped_tail_sessions"] == 40, str(out["dropped_tail_sessions"]))
    f1, f3 = out["folds"][0], out["folds"][2]
    check("fold1_boundaries",
          f1["train_start"] == days[0].isoformat() and f1["train_end"] == days[251].isoformat()
          and f1["oos_start"] == days[252].isoformat() and f1["oos_end"] == days[314].isoformat(),
          json.dumps(f1))
    check("fold3_expanding_train",
          f3["train_sessions"] == 252 + 126 and f3["oos_start"] == days[378].isoformat()
          and f3["oos_end"] == days[440].isoformat(), json.dumps(f3))
    check("holdout_never_in_output",
          all(not (fm.HOLDOUT_START.isoformat() <= f["oos_start"] <= fm.HOLDOUT_END.isoformat())
              for f in out["folds"]))

    # 3. Digests recomputed independently.
    check("input_digest",
          out["input_timestamp_digest"] == hashlib.sha256("\n".join(ts).encode()).hexdigest())
    check("calendar_digest",
          out["calendar_digest"] == hashlib.sha256(
              "\n".join(d.isoformat() for d in days).encode()).hexdigest())

    # 4. Determinism of the materializer.
    out2 = fm.materialize(list(ts), set(holiday_strs))
    check("materializer_deterministic", fm.canonical_json(out) == fm.canonical_json(out2))

    # 5. Fail-closed cases.
    bad = list(ts); del bad[1]  # drop one 13:30 bar
    expect_error("bad_grid_missing_bar", "BAD_GRID", lambda: fm.materialize(bad, holiday_strs))
    bad = list(ts); bad.insert(5, bad[4])
    expect_error("duplicate_timestamp", "DUPLICATE_TIMESTAMP", lambda: fm.materialize(bad, holiday_strs))
    bad = list(ts); bad[10], bad[11] = bad[11], bad[10]
    expect_error("non_monotonic", "NON_MONOTONIC", lambda: fm.materialize(bad, holiday_strs))
    # remove a full non-holiday Wednesday (index: find one) -> unresolved gap
    wed_idx = next(i for i, d in enumerate(days) if d.weekday() == 2 and i > 10)
    bad = [t for t in ts if not t.startswith(days[wed_idx].isoformat())]
    expect_error("unresolved_gap", "UNRESOLVED_GAP", lambda: fm.materialize(bad, holiday_strs))
    bad = ["2024-01-10T09:30", "2024-01-10T13:30"] + list(ts)  # inside sealed holdout
    bad.sort()
    expect_error("holdout_touch", "HOLDOUT_TOUCH", lambda: fm.materialize(bad, holiday_strs))
    expect_error("insufficient_sessions", "INSUFFICIENT_SESSIONS",
                 lambda: fm.materialize(ts[: 2 * 300], holiday_strs))

    # 6. Descriptive statistics on SYNTHETIC_FIXTURE per-trade R.
    r_fix = [((i * 37) % 11 - 4) * 0.13 + 0.05 for i in range(100)]
    stats_out = {}
    for n in (50, 100):
        s = il.descriptive_r_stats(r_fix[:n])
        check(f"descriptive_n{n}_mean", abs(s["mean_net_r"] - statistics.mean(r_fix[:n])) < 1e-12)
        check(f"descriptive_n{n}_sd", abs(s["sd_net_r"] - statistics.stdev(r_fix[:n])) < 1e-12)
        check(f"descriptive_n{n}_ci_contains_mean", s["ci95_low"] < s["mean_net_r"] < s["ci95_high"])
        stats_out[f"n{n}"] = s
    check("t_ppf_known_value", abs(il.t_ppf(0.975, 49) - 2.0096) < 1e-3,
          f"{il.t_ppf(0.975, 49):.6f}")

    # 7. Bootstrap: seed derived from preregistration SHA + determinism.
    prereg = HERE / "PREREGISTRATION.md"
    seed = il.seed_from_prereg(prereg)
    expect_seed = int.from_bytes(hashlib.sha256(prereg.read_bytes()).digest()[:8], "big")
    check("bootstrap_seed_from_prereg_sha", seed == expect_seed, str(seed))
    daily_fix = [((i * 2654435761) % 997) / 997.0 - 0.47 for i in range(300)]  # SYNTHETIC_FIXTURE
    boot = il.circular_block_bootstrap(daily_fix, seed)
    boot2 = il.circular_block_bootstrap(daily_fix, seed)
    check("bootstrap_deterministic", boot == boot2, str(boot))
    check("bootstrap_ci_ordered", boot[0] < boot[1] and 0.0 < boot[2] <= 1.0, str(boot))
    check("bootstrap_block_reps_frozen", il.BLOCK_SESSIONS == 20 and il.REPLICATIONS == 10000)

    # 8. Holm ordering on a hand-computed example + the registered family.
    adj = il.holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03})
    check("holm_hand_example",
          abs(adj["a"] - 0.03) < 1e-12 and abs(adj["b"] - 0.06) < 1e-12 and abs(adj["c"] - 0.06) < 1e-12,
          json.dumps(adj))
    raw = {h: p for h, p in zip(il.FAMILY, [0.001, 0.02, 0.04, 0.008, 0.20, 0.049])}
    adj_f = il.holm_adjust(raw)
    sorted_raw = sorted(raw.values())
    sorted_adj = [adj_f[h] for h, _ in sorted(raw.items(), key=lambda kv: kv[1])]
    check("holm_family_size_6", len(il.FAMILY) == 6 and set(adj_f) == set(il.FAMILY))
    check("holm_monotone_in_raw_order",
          all(a <= b + 1e-15 for a, b in zip(sorted_adj, sorted_adj[1:]))
          and all(adj_f[h] >= raw[h] - 1e-15 for h in raw),
          json.dumps(adj_f))
    _ = sorted_raw

    payload = {
        "fixture_label": "SYNTHETIC_FIXTURE",
        "materializer_output": out,
        "descriptive": stats_out,
        "bootstrap": {"seed": seed, "ci95": [boot[0], boot[1]], "p_one_sided": boot[2]},
        "holm_family_adjusted": adj_f,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload, digest


def main():
    payload1, digest1 = run_all()
    first_pass = list(RESULTS)
    RESULTS.clear()
    payload2, digest2 = run_all()
    byte_identical = digest1 == digest2 and fm.canonical_json(payload1) == fm.canonical_json(payload2)
    all_pass = all(r["pass"] for r in first_pass) and all(r["pass"] for r in RESULTS)
    doc = {
        "task": "QF-VALIDATION-PREREG-FINALIZATION-20261018-25 r1",
        "fixture_label": "SYNTHETIC_FIXTURE",
        "tests_run": len(first_pass),
        "tests_passed": sum(1 for r in first_pass if r["pass"]),
        "all_pass": bool(all_pass),
        "twice_run_byte_identical": bool(byte_identical),
        "run_digest_1": digest1,
        "run_digest_2": digest2,
        "results": first_pass,
        "fixture_payload": payload1,
    }
    (HERE / "TEST_RESULTS.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"tests {doc['tests_passed']}/{doc['tests_run']} pass; "
          f"byte_identical={byte_identical}; digest={digest1}")
    sys.exit(0 if (all_pass and byte_identical) else 1)


if __name__ == "__main__":
    main()
