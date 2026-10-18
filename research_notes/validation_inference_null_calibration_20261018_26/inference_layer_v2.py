"""Inference layer v2 — null-calibrated formal edge test.

Governed by PREREGISTRATION_AMENDMENT_V2_20261018_26, which supersedes
ONLY the formal one-sided p-value definition of PREREGISTRATION_20261018_25
section 3 (task QF-VALIDATION-INFERENCE-NULL-CALIBRATION-20261018-26 r1;
spec: GitHub Issue #1 comment 6255324442). The -25 preregistration and
the -25 inference_layer.py are unchanged.

Failure memory: BOOTSTRAP_P_NOT_NULL_CALIBRATED. The -25 definition
resampled the unmodified observed series and reported
(1 + #{rep means <= 0}) / (B + 1) as a p-value for H0: mean <= 0. Those
resamples are centered on the OBSERVED sample mean, not on the null
boundary 0, so that quantity is a bootstrap sign probability (the tail
of the percentile-CI distribution), NOT a calibrated null-distribution
p-value. It is retained here ONLY as the clearly labeled uncentered
percentile confidence interval; it is never a formal p-value.

Corrected formal test (frozen by the amendment): a one-sided test of
H0: mean <= 0 at the boundary mean = 0. The null distribution of the
sample mean is formed by a circular block bootstrap (block length 20
sessions, 10,000 deterministic replications, SplitMix64) of the
DEMEANED series x_i - mean(x), which imposes the null boundary while
preserving the series' dependence shape. The formal p-value is the
upper tail at the observed mean, with the plus-one correction:

    p = (1 + #{null rep means >= observed mean}) / (B + 1)

For observed mean <= 0 the null reps are centered at 0, so at least
roughly half of them are >= the observed mean and p > 0.05 always:
the procedure structurally cannot claim positive edge there (asserted
in the test suite).

Everything else from -25 section 3 is carried over unchanged: the
descriptive t statistics (DESCRIPTIVE_ONLY), the six-hypothesis Holm
family F with economic-gate primacy (a p-value can never rescue a
failed economic gate), and the uncentered percentile bootstrap CI.

Pure standard library. Deterministic. Proven on synthetic fixtures
only; never run on real strategy outcomes.
"""

import hashlib
import math
from pathlib import Path

BLOCK_SESSIONS = 20
REPLICATIONS = 10_000

# The registered hypothesis family F (PREREGISTRATION s3, unchanged):
# exactly six formal one-sided edge hypotheses, evaluated only at the
# n=100 readout, Holm-adjusted as a single family.
FAMILY = [
    "H_pooled",
    "H_cohort_UX51",
    "H_cohort_X2",
    "H_grade_A",
    "H_grade_B",
    "H_grade_C",
]

FAILURE_KEY = "BOOTSTRAP_P_NOT_NULL_CALIBRATED"


def seed_from_amendment(amendment_path):
    """Bootstrap seed: first 8 bytes (big-endian) of the governing
    amendment document's SHA-256 (same rule as -25, applied to the
    amendment that freezes this corrected definition)."""
    digest = hashlib.sha256(Path(amendment_path).read_bytes()).digest()
    return int.from_bytes(digest[:8], "big")


class SplitMix64:
    """Deterministic 64-bit RNG (SplitMix64). Version-independent.
    Identical to -25 inference_layer.py."""

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return z ^ (z >> 31)

    def randbelow(self, n):
        return self.next_u64() % n


# --- Student t quantiles (identical implementation to -25) ---

def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    ib = _betai(df / 2.0, 0.5, x)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def t_ppf(p, df):
    lo, hi = -1e6, 1e6
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --- Descriptive statistics on per-trade R (unchanged from -25) ---

def descriptive_r_stats(trades_r):
    n = len(trades_r)
    if n < 2:
        raise ValueError("need at least 2 observations")
    mean = sum(trades_r) / n
    var = sum((x - mean) ** 2 for x in trades_r) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)
    t_stat = mean / se if se > 0 else float("inf")
    crit = t_ppf(0.975, n - 1)
    return {
        "n": n,
        "mean_net_r": mean,
        "sd_net_r": sd,
        "t_stat": t_stat,
        "ci95_low": mean - crit * se,
        "ci95_high": mean + crit * se,
        "status": "DESCRIPTIVE_ONLY",
    }


# --- Shared validation ---

def _validate_series(daily_returns, block):
    x = list(daily_returns)
    n = len(x)
    if n == 0:
        raise ValueError("EMPTY_SERIES")
    if n < block:
        raise ValueError("SERIES_SHORTER_THAN_BLOCK")
    for v in x:
        if not isinstance(v, (int, float)) or isinstance(v, bool) \
                or not math.isfinite(v):
            raise ValueError("NON_FINITE_VALUE")
    return [float(v) for v in x]


def _block_resample_means(x, seed, block, reps):
    """Circular block bootstrap rep means of series x (internal)."""
    n = len(x)
    rng = SplitMix64(seed)
    blocks_needed = (n + block - 1) // block
    means = []
    for _ in range(reps):
        # Identical sampling AND summation to -25: concatenated
        # circular blocks truncated to exactly n elements, mean via
        # built-in sum() over the built sample (CPython float sum is
        # compensated; a hand accumulation loop differs in last ulps
        # and flipped boundary reps during -26 fixture proof).
        sample = []
        for _ in range(blocks_needed):
            start = rng.randbelow(n)
            for j in range(block):
                sample.append(x[(start + j) % n])
        sample = sample[:n]
        means.append(sum(sample) / n)
    return means


# --- Uncentered percentile CI (retained from -25; NOT a p-value) ---

def bootstrap_percentile_ci(daily_returns, seed, block=BLOCK_SESSIONS,
                            reps=REPLICATIONS):
    """Two-sided 95% percentile CI for the mean from circular block
    bootstrap resamples of the OBSERVED series. This is a confidence
    interval only. The tail mass of this distribution at 0 is the -25
    defective 'p-value' (failure key BOOTSTRAP_P_NOT_NULL_CALIBRATED)
    and must never be reported as one."""
    x = _validate_series(daily_returns, block)
    means = _block_resample_means(x, seed, block, reps)
    means.sort()
    lo = means[int(0.025 * reps)]
    hi = means[min(reps - 1, int(0.975 * reps))]
    return lo, hi


def legacy_defective_sign_probability(daily_returns, seed,
                                      block=BLOCK_SESSIONS,
                                      reps=REPLICATIONS):
    """The -25 quantity (1 + #{uncentered rep means <= 0}) / (B + 1),
    reproduced ONLY so tests can prove it is not the formal p-value.
    Never use as a p-value."""
    x = _validate_series(daily_returns, block)
    means = _block_resample_means(x, seed, block, reps)
    le_zero = sum(1 for m in means if m <= 0.0)
    return (1 + le_zero) / (reps + 1)


# --- Corrected formal edge test (null-centered) ---

def null_centered_edge_test(daily_returns, seed, block=BLOCK_SESSIONS,
                            reps=REPLICATIONS):
    """One-sided test of H0: mean <= 0 at boundary 0, per AMENDMENT v2.

    Null distribution: circular block bootstrap of the demeaned series
    x_i - mean(x). Formal p = (1 + #{null rep means >= observed
    mean}) / (reps + 1) (upper tail, plus-one correction).
    """
    x = _validate_series(daily_returns, block)
    n = len(x)
    observed_mean = sum(x) / n
    demeaned = [v - observed_mean for v in x]
    null_means = _block_resample_means(demeaned, seed, block, reps)
    ge = sum(1 for m in null_means if m >= observed_mean)
    p_formal = (1 + ge) / (reps + 1)
    return {
        "observed_mean": observed_mean,
        "p_formal": p_formal,
        "method": "NULL_CENTERED_CIRCULAR_BLOCK_BOOTSTRAP",
        "failure_key_repaired": FAILURE_KEY,
        "block_sessions": block,
        "replications": reps,
        "seed": seed,
        "edge_claim_possible": observed_mean > 0.0,
    }


# --- Holm step-down correction (math identical to -25) + family guard ---

def holm_adjust(pvalues):
    """Step-down Holm adjustment; identical mathematics to -25."""
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    adjusted = {}
    running = 0.0
    for j, (name, p) in enumerate(items):
        val = min(1.0, (m - j) * p)
        running = max(running, val)
        adjusted[name] = running
    return adjusted


def validate_and_adjust_family(pvalues):
    """Formal family gate: refuse anything but exactly the registered
    family F with finite p-values in [0, 1]; then Holm-adjust."""
    keys = set(pvalues.keys())
    if keys != set(FAMILY):
        missing = sorted(set(FAMILY) - keys)
        extra = sorted(keys - set(FAMILY))
        raise ValueError(
            "FAMILY_MISMATCH missing=%s extra=%s" % (missing, extra))
    for name, p in pvalues.items():
        if not isinstance(p, (int, float)) or isinstance(p, bool) \
                or not math.isfinite(p) or p < 0.0 or p > 1.0:
            raise ValueError("INVALID_P_VALUE %s=%r" % (name, p))
    return holm_adjust(pvalues)
