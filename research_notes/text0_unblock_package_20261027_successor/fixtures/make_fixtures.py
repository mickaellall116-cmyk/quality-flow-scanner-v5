"""Deterministic generator for the successor suite's matcher
fixtures. Run directly to (re)generate the three committed fixture
files; the suite re-runs it into a temp dir and asserts byte
equality with the committed copies (fixture determinism check).

Fixtures are FABRICATED: symbols FAA/FBB/FCC, invented prices, no
holdout data. The fixture binding mirrors the real one's shape -
same window, strict key sets - with fixture tier membership, so a
fixture-pinned copy of exp14_buy_corr4.py exercises the real
binding code end to end.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


FIXTURE_TIERS = {"tier2": ["FAA", "FBB"], "tier3": ["FCC"]}
DUMMY_TABLE_SHA = "aa" * 32
DUMMY_CORR2_SHA = "bb" * 32
DUMMY_ENGINE = {"run_study13.py": "cc" * 32,
                "pine_backtest.py": "dd" * 32,
                "scanner_rules.py": "ee" * 32}
DUMMY_BUILDER_SHA = "ff" * 32


def synth_inventory(path):
    """3 symbols x 60 bars (30 sessions x 2 bins), fabricated
    prices, domain fires planted at known indices.
    Planted census: FAA 2 + FBB 1 + FCC 3 = 6; window-complete
    cohort (h=20): FAA 2 + FBB 1 + FCC 2 = 5."""
    import datetime as dt
    days = []
    d = dt.date(2023, 10, 19)
    while len(days) < 30:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    planted = {"FAA": [10, 35], "FBB": [12], "FCC": [10, 35, 50]}
    rows = []
    for sym, fires in planted.items():
        for i in range(60):
            sess = days[i // 2]
            bin_ = "09:30" if i % 2 == 0 else "13:30"
            off = "-04:00" if sess < dt.date(2023, 11, 5) \
                else "-05:00"
            close = 100.0 + (i % 7)
            rows.append({
                "symbol": sym, "idx": i,
                "ts": f"{sess.isoformat()}T{bin_}:00{off}",
                "session_date": sess.isoformat(),
                "session_ordinal": i // 2, "bin": bin_,
                "close": close, "atr": 2.0, "atr_pct": 0.02,
                "ema21": close - 1.0, "ema55": close - 2.0,
                "ema200": close - 3.0,
                "signal": i in fires,
                "in_generator_domain": i >= 5,
            })
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return sum(1 for r in rows
               if r["in_generator_domain"] and r["signal"])


def fixture_content():
    return {
        "binding_id": "FIXTURE-BINDING",
        "stage": 1,
        "window_start": "2023-10-19",
        "window_end": "2024-09-15",
        "tiers": FIXTURE_TIERS,
        "session_table_sha256": DUMMY_TABLE_SHA,
        "corr2_source_sha256": DUMMY_CORR2_SHA,
        "engine": DUMMY_ENGINE,
        "raw_capture": {
            "raw_dir": "session_auth_dir/raw",
            "receipt_file": "receipt_manifest.json",
            "file_template": "{sym}.json",
            "receipt_root_algorithm":
                "canonical_sha256(per_symbol_sha256_map)",
            "symbol_count": 3,
        },
    }


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    inv = os.path.join(outdir, "synth_inventory.jsonl")
    census = synth_inventory(inv)
    content = fixture_content()
    manifest = dict(content)
    manifest["status"] = "STAGE1-PINS-COMMITTED"
    manifest["builder"] = {"file": "fixture-builder",
                           "sha256": DUMMY_BUILDER_SHA}
    manifest["stage2_addendum_file"] = "stage2_addendum.json"
    man_path = os.path.join(outdir, "fixture_stage1_manifest.json")
    with open(man_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    addendum = {
        "binding_id": "FIXTURE-BINDING",
        "stage": 2,
        "binding_content_sha256": canonical_sha(content),
        "inventory_sha256": sha256_file(inv),
        "expected_fires": census,
        "builder_sha256": DUMMY_BUILDER_SHA,
        "session_table_sha256": DUMMY_TABLE_SHA,
        "session": {"id": "FIXTURE-SESSION", "date": "2026-10-29",
                    "operators": ["fixture-op-1", "fixture-op-2"]},
    }
    add_path = os.path.join(outdir, "fixture_stage2_addendum.json")
    with open(add_path, "w") as f:
        json.dump(addendum, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"fixtures written to {outdir} (census {census})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE)
