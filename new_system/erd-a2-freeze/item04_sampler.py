"""ERD v0.1 Amendment 2 — frozen sampler (manifest item 4).

Implements the §1.2 draw mechanics of
`new_system/erd-v0.1-preregistration-amendment-2-DRAFT-rev4.md` verbatim,
plus the §1.6(c) transition-sample draw.

Frozen constants live in item04_sampler_config.json and are loaded from it;
no constant is defined anywhere else.

Determinism: Fisher-Yates is implemented explicitly on top of
random.Random(seed) (Mersenne Twister). The PRNG stream is the ONLY source
of randomness. Re-running on the same frame bytes reproduces the sample
byte-for-byte (see item04_determinism_check.log).

Frame row fields (canonical JSON, sorted keys, UTF-8):
  perm_id: str            permanent security ID
  fiscal_year: int
  fiscal_quarter: int     1-4
  quarter_end_date: str   ISO date YYYY-MM-DD
  delisted: bool          delisted as of freeze
  ticker_change: bool     >=1 ticker change in history per the master
  acquisition: bool       acquisition/entity-transition flag per the master
"""

import hashlib
import json
import random
import sys

CONFIG_PATH = "item04_sampler_config.json"


def load_config(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fisher_yates(items, rng):
    """Explicit Fisher-Yates shuffle using only the provided PRNG."""
    a = list(items)
    for i in range(len(a) - 1, 0, -1):
        j = rng.randint(0, i)
        a[i], a[j] = a[j], a[i]
    return a


def canonical_key(row):
    return (row["perm_id"], row["fiscal_year"], row["fiscal_quarter"])


def draw_sample(frame_rows, config):
    """§1.2 draw mechanics. Returns (sample_rows, audit)."""
    seed = config["seed"]
    quotas = config["quotas"]

    # 1. canonical sort
    ordered = sorted(frame_rows, key=canonical_key)

    # 2. seeded Fisher-Yates shuffle
    rng = random.Random(seed)
    shuffled = fisher_yates(ordered, rng)

    admitted = []
    admitted_keys = set()
    shortfalls = []

    def admit(row):
        k = canonical_key(row)
        if k not in admitted_keys:
            admitted_keys.add(k)
            admitted.append(row)

    # 3a. years quota: first member of each new quarter-end year, in order
    years_seen = set()
    for row in shuffled:
        y = int(row["quarter_end_date"][:4])
        if y not in years_seen:
            years_seen.add(y)
            admit(row)
        if len(years_seen) >= quotas["distinct_years"]:
            break
    if len(years_seen) < quotas["distinct_years"]:
        shortfalls.append(
            f"years: only {len(years_seen)} distinct years available, "
            f"quota {quotas['distinct_years']}")

    # 3b/3c/3d. flag quotas, in fixed priority order
    for flag, name in (("delisted", "delisted"),
                       ("ticker_change", "ticker_change"),
                       ("acquisition", "acquisition")):
        want = quotas[name]
        got = 0
        for row in shuffled:
            if row.get(flag):
                before = len(admitted)
                admit(row)
                if len(admitted) > before:
                    got += 1
                if got >= want:
                    break
        if got < want:
            shortfalls.append(
                f"{name}: only {got} available, quota {want}")

    # 4. fill pass to exactly 50
    target = config["sample_size"]
    for row in shuffled:
        if len(admitted) >= target:
            break
        admit(row)

    # smaller-population fallback
    if len(ordered) < target:
        raise SystemExit(
            f"GATE NOT RUNNABLE: eligible frame holds {len(ordered)} members, "
            f"fewer than {target}. ERD halts. No redraw outside the frame.")

    audit = {
        "frame_rows": len(ordered),
        "sample_size": len(admitted),
        "seed": seed,
        "distinct_years": sorted(years_seen),
        "shortfalls": shortfalls,
    }
    return admitted[:target], audit


def draw_transition_sample(sample_rows, config):
    """§1.6(c): N=20, Fisher-Yates seeded shuffle of the frozen 50 with the
    frozen transition seed; first 20 taken. No weighting."""
    rng = random.Random(config["transition_seed"])
    shuffled = fisher_yates(sorted(sample_rows, key=canonical_key), rng)
    return shuffled[:config["transition_n"]]


def canonical_json(rows):
    """Canonical serialization for the frozen 50-event list (item 3):
    sorted keys, UTF-8, LF, no timing fields."""
    slim = [{"perm_id": r["perm_id"],
             "fiscal_year": r["fiscal_year"],
             "fiscal_quarter": r["fiscal_quarter"],
             "quarter_end_date": r["quarter_end_date"]} for r in rows]
    return json.dumps(slim, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 3:
        print("usage: item04_sampler.py <frame.json> <out_sample.json>")
        sys.exit(2)
    config = load_config()
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        frame = json.load(f)
    sample, audit = draw_sample(frame, config)
    blob = canonical_json(sample)
    with open(sys.argv[2], "wb") as f:
        f.write(blob)
    print(json.dumps({"audit": audit,
                      "sha256": sha256_hex(blob)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
