"""Inference layer for forward-test readouts.

Frozen by PREREGISTRATION_20261018_25 section 3 (task
QF-VALIDATION-PREREG-FINALIZATION-20261018-25 r1): descriptive t-statistic
on per-trade R, dependence-robust circular block bootstrap over
chronological daily portfolio returns (20-session blocks, 10,000
deterministic replications, seed derived from the preregistration SHA),
and Holm step-down correction across the registered hypothesis family F.

Pure standard library. All functions are deterministic. This module is
proven on synthetic fixtures only; it has never been run on real strategy
outcomes.
"""

import hashlib
import math
from pathlib import Path

BLOCK_SESSIONS = 20
REPLICATIONS = 10_000

# The registered hypothesis family F (PREREGISTRATION s3): exactly six
# formal one-sided edge hypotheses, evaluated only at the n=100 readout.
FAMILY = [
    "H_pooled",
    "H_cohort_UX51",
    "H_cohort_X2",
    "H_grade_A",
    "H_grade_B",
    "H_grade_C",
]


def seed_from_prereg(prereg_path):
    """Bootstrap seed: first 8 bytes (big-endian) of the preregistration
    document's SHA-256."""
    digest = hashlib.sha256(Path(prereg_path).read_bytes()).digest()
    return int.from_bytes(digest[:8], "big")


class SplitMix64:
    """Deterministic 64-bit RNG (SplitMix64). Version-independent."""

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


# --- Student t quantiles via the regularized incomplete beta function ---

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


# --- Descriptive statistics on per-trade R (descriptive only, PREREG s3) ---

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


# --- Circular block bootstrap over chronological daily returns ---

def circular_block_bootstrap(daily_returns, seed, block=BLOCK_SESSIONS, reps=REPLICATIONS):
    """Returns (ci95_low, ci95_high, p_one_sided) for the mean, per PREREG s3.

    p_one_sided is the one-sided edge test of H0: mean <= 0 with the
    plus-one correction (1 + #{rep means <= 0}) / (reps + 1).
    """
    x = list(daily_returns)
    n = len(x)
    if n == 0:
        raise ValueError("empty series")
    rng = SplitMix64(seed)
    blocks_needed = (n + block - 1) // block
    means = []
    for _ in range(reps):
        sample = []
        for _ in range(blocks_needed):
            start = rng.randbelow(n)
            for j in range(block):
                sample.append(x[(start + j) % n])
        sample = sample[:n]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * reps)]
    hi = means[min(reps - 1, int(0.975 * reps))]
    le_zero = sum(1 for m in means if m <= 0.0)
    p_one = (1 + le_zero) / (reps + 1)
    return lo, hi, p_one


# --- Holm step-down correction ---

def holm_adjust(pvalues):
    """pvalues: {hypothesis: raw p}. Returns {hypothesis: Holm-adjusted p}.

    Step-down: sort ascending; adjusted p_(i) = max over j<=i of
    min(1, (m - j) * p_(j)) with 0-based j.
    """
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    adjusted = {}
    running = 0.0
    for j, (name, p) in enumerate(items):
        val = min(1.0, (m - j) * p)
        running = max(running, val)
        adjusted[name] = running
    return adjusted
