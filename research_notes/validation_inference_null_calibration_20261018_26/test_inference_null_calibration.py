"""Synthetic-fixture proof for PREREGISTRATION_AMENDMENT_V2_20261018_26.

Task QF-VALIDATION-INFERENCE-NULL-CALIBRATION-20261018-26 r1.
All series are SYNTHETIC_FIXTURE values from fixed arithmetic formulas.
No market data, no real strategy outcomes. Prints a JSON payload and
exits 0 only if every check passes. The full computation is run twice
and must be byte-identical.
"""

import hashlib
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG25 = HERE.parent / "validation_prereg_finalization_20261018_25"
sys.path.insert(0, str(HERE))

import inference_layer_v2 as v2  # noqa: E402


def _load_25():
    spec = importlib.util.spec_from_file_location(
        "inference_layer_25", PKG25 / "inference_layer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


il25 = _load_25()

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"test": name, "pass": bool(ok), "detail": str(detail)})


def expect_value_error(name, fn, needle):
    try:
        fn()
    except ValueError as e:
        check(name, needle in str(e), str(e))
        return
    check(name, False, "no ValueError raised")


# --- Independent reference recomputation of the null-centered tail ---
# Written separately from inference_layer_v2 (list-building sampler in
# the -25 style, own RNG copy) so agreement is a real cross-check.

class _RefSplitMix64:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return z ^ (z >> 31)


def reference_null_centered_p(series, seed, block=20, reps=10000):
    n = len(series)
    xbar = sum(series) / n
    dem = [v - xbar for v in series]
    rng = _RefSplitMix64(seed)
    need = (n + block - 1) // block
    ge = 0
    for _ in range(reps):
        sample = []
        for _ in range(need):
            s = rng.next_u64() % n
            for j in range(block):
                sample.append(dem[(s + j) % n])
        sample = sample[:n]
        if sum(sample) / n >= xbar:
            ge += 1
    return (1 + ge) / (reps + 1), xbar


SEED_25 = 14767771057543718562  # from -25 preregistration SHA (-25 suite)
SHARED_FIX = [((i * 2654435761) % 997) / 997.0 - 0.47 for i in range(300)]
BASE = [((i * 2654435761) % 997) / 997.0 for i in range(300)]
C0 = sum(BASE) / len(BASE)
NULL_FIX = [b - C0 for b in BASE]              # sample mean ~ 0
NEG_FIX = [b - C0 - 0.05 for b in BASE]        # sample mean = -0.05
POS_FIX = [b - C0 + 0.10 for b in BASE]        # sample mean = +0.10

EXPECTED_25_SHA = {
    "fold_materializer.py":
        "b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e",
    "inference_layer.py":
        "64e8ec1bec536e4b9bf040cbc467541b2102058b42e6b67f04d620a28ff91e17",
    "PREREGISTRATION.md":
        "ccf1a988a93026a2032f5cb94f6c6d9e78705e5121ca049d60ec2a1272473c24",
}


def run_all():
    RESULTS.clear()
    amendment = HERE / "PREREGISTRATION_AMENDMENT_V2.md"
    seed_v2 = v2.seed_from_amendment(amendment)
    expect_seed = int.from_bytes(
        hashlib.sha256(amendment.read_bytes()).digest()[:8], "big")
    check("seed_from_amendment_sha", seed_v2 == expect_seed, str(seed_v2))
    check("frozen_constants", v2.BLOCK_SESSIONS == 20
          and v2.REPLICATIONS == 10000 and len(v2.FAMILY) == 6)

    # 1. -25 files preserved byte-identically (static check vs fc17041).
    for fname, want in EXPECTED_25_SHA.items():
        got = hashlib.sha256((PKG25 / fname).read_bytes()).hexdigest()
        check(f"static_25_preserved_{fname}", got == want, got)

    # 2. Shared -25 fixture: reproduce the -25 defective result exactly.
    lo25, hi25, p25 = il25.circular_block_bootstrap(SHARED_FIX, SEED_25)
    check("fixture25_reproduced_ci",
          abs(lo25 - (-0.030297559344700745)) < 1e-15
          and abs(hi25 - 0.08825810765630226) < 1e-15, f"{lo25},{hi25}")
    check("fixture25_reproduced_defective_p",
          abs(p25 - 0.16998300169983002) < 1e-15, str(p25))

    # 3. v2 CI is the identical uncentered percentile CI (retained).
    lo2, hi2 = v2.bootstrap_percentile_ci(SHARED_FIX, SEED_25)
    check("v2_ci_identical_to_25", lo2 == lo25 and hi2 == hi25,
          f"{lo2},{hi2}")

    # 4. v2 reproduction of the defective quantity matches -25 exactly,
    #    proving the comparison below isolates the definition change.
    p_legacy = v2.legacy_defective_sign_probability(SHARED_FIX, SEED_25)
    check("v2_legacy_quantity_reproduces_25", p_legacy == p25, str(p_legacy))

    # 5. Corrected null-centered p on the SAME fixture, SAME seed.
    corr = v2.null_centered_edge_test(SHARED_FIX, SEED_25)
    p_corr = corr["p_formal"]
    check("corrected_p_differs_from_defective",
          abs(p_corr - p25) > 1e-9, f"corrected={p_corr} defective={p25}")
    check("corrected_p_in_range", 0.0 < p_corr <= 1.0, str(p_corr))

    # 6. Independent reference recomputation of the null-centered tail.
    p_ref, xbar_ref = reference_null_centered_p(SHARED_FIX, SEED_25)
    check("reference_recompute_shared_fixture",
          p_ref == p_corr and abs(xbar_ref - corr["observed_mean"]) < 1e-15,
          f"ref={p_ref} module={p_corr}")

    # 7. Known-null scenario: no edge claim, plausible null p.
    null_res = v2.null_centered_edge_test(NULL_FIX, seed_v2)
    check("null_scenario_mean_is_zero",
          abs(null_res["observed_mean"]) < 1e-9, str(null_res["observed_mean"]))
    check("null_scenario_no_edge_claim",
          0.05 < null_res["p_formal"] < 0.95, str(null_res["p_formal"]))
    p_ref_null, _ = reference_null_centered_p(NULL_FIX, seed_v2)
    check("reference_recompute_null_scenario",
          p_ref_null == null_res["p_formal"], str(p_ref_null))

    # 8. Negative-mean scenario: structurally cannot claim edge.
    neg_res = v2.null_centered_edge_test(NEG_FIX, seed_v2)
    check("negative_scenario_mean", abs(neg_res["observed_mean"] + 0.05) < 1e-9,
          str(neg_res["observed_mean"]))
    check("negative_scenario_p_above_half",
          neg_res["p_formal"] > 0.5, str(neg_res["p_formal"]))
    check("negative_scenario_edge_claim_impossible",
          neg_res["edge_claim_possible"] is False)

    # 9. Strong-positive scenario: power sanity.
    pos_res = v2.null_centered_edge_test(POS_FIX, seed_v2)
    check("positive_scenario_detected",
          pos_res["p_formal"] < 0.01 and pos_res["edge_claim_possible"] is True,
          str(pos_res["p_formal"]))

    # 10. Descriptive stats unchanged vs -25 implementation + stdlib.
    r_fix = [((i * 37) % 11 - 4) * 0.13 + 0.05 for i in range(100)]
    desc = {}
    for n in (50, 100):
        s2 = v2.descriptive_r_stats(r_fix[:n])
        s25 = il25.descriptive_r_stats(r_fix[:n])
        check(f"descriptive_n{n}_identical_to_25", s2 == s25)
        check(f"descriptive_n{n}_mean_stdlib",
              abs(s2["mean_net_r"] - statistics.mean(r_fix[:n])) < 1e-12)
        desc[f"n{n}"] = s2
    check("t_ppf_known_value", abs(v2.t_ppf(0.975, 49) - 2.0096) < 1e-3)

    # 11. Holm: identical math to -25 + family refusals.
    adj = v2.holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03})
    check("holm_hand_example",
          abs(adj["a"] - 0.03) < 1e-12 and abs(adj["b"] - 0.06) < 1e-12
          and abs(adj["c"] - 0.06) < 1e-12, json.dumps(adj))
    raw = {h: p for h, p in zip(v2.FAMILY,
                                [0.001, 0.02, 0.04, 0.008, 0.20, 0.049])}
    adj_f = v2.validate_and_adjust_family(raw)
    check("holm_family_matches_25", adj_f == il25.holm_adjust(raw),
          json.dumps(adj_f))
    missing = dict(raw); del missing["H_grade_C"]
    expect_value_error("holm_refuses_missing_hypothesis",
                       lambda: v2.validate_and_adjust_family(missing),
                       "FAMILY_MISMATCH")
    extra = dict(raw); extra["H_extra"] = 0.01
    expect_value_error("holm_refuses_extra_hypothesis",
                       lambda: v2.validate_and_adjust_family(extra),
                       "FAMILY_MISMATCH")
    nanp = dict(raw); nanp["H_pooled"] = float("nan")
    expect_value_error("holm_refuses_nan_p",
                       lambda: v2.validate_and_adjust_family(nanp),
                       "INVALID_P_VALUE")
    oorp = dict(raw); oorp["H_pooled"] = 1.5
    expect_value_error("holm_refuses_out_of_range_p",
                       lambda: v2.validate_and_adjust_family(oorp),
                       "INVALID_P_VALUE")

    # 12. Series refusals on the formal path.
    expect_value_error("edge_test_refuses_empty",
                       lambda: v2.null_centered_edge_test([], seed_v2),
                       "EMPTY_SERIES")
    expect_value_error("edge_test_refuses_short_series",
                       lambda: v2.null_centered_edge_test(
                           [0.01] * 10, seed_v2),
                       "SERIES_SHORTER_THAN_BLOCK")
    expect_value_error("edge_test_refuses_non_finite",
                       lambda: v2.null_centered_edge_test(
                           [0.01] * 30 + [float("inf")], seed_v2),
                       "NON_FINITE_VALUE")

    payload = {
        "fixture_label": "SYNTHETIC_FIXTURE",
        "failure_key": v2.FAILURE_KEY,
        "amendment_seed": seed_v2,
        "shared_fixture_25_seed": SEED_25,
        "shared_fixture": {
            "observed_mean": corr["observed_mean"],
            "ci95_uncentered_percentile": [lo2, hi2],
            "p_defective_25": p25,
            "p_corrected_26": p_corr,
            "p_reference_recompute": p_ref,
        },
        "scenarios": {
            "null": {"observed_mean": null_res["observed_mean"],
                     "p_formal": null_res["p_formal"],
                     "p_reference": p_ref_null},
            "negative": {"observed_mean": neg_res["observed_mean"],
                         "p_formal": neg_res["p_formal"],
                         "edge_claim_possible":
                             neg_res["edge_claim_possible"]},
            "strong_positive": {"observed_mean": pos_res["observed_mean"],
                                "p_formal": pos_res["p_formal"]},
        },
        "descriptive": desc,
        "holm_family_adjusted": adj_f,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload, digest


def main():
    payload1, digest1 = run_all()
    first = list(RESULTS)
    payload2, digest2 = run_all()
    second = list(RESULTS)
    all_pass = all(r["pass"] for r in first) and first == second \
        and digest1 == digest2 and payload1 == payload2
    out = {
        "task": "QF-VALIDATION-INFERENCE-NULL-CALIBRATION-20261018-26 r1",
        "fixture_label": "SYNTHETIC_FIXTURE",
        "all_pass": all_pass,
        "twice_byte_identical": digest1 == digest2,
        "result_digest": digest1,
        "checks": len(first),
        "results": first,
        "fixture_payload": payload1,
    }
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
