#!/usr/bin/env python3
"""B8 run-input lock: hash-lock a run's fetch manifest and raw 1H inputs.

Runbook (rev-6.1 B8): AFTER the run's fetch completes and BEFORE build/compare,
    python3 hash_run_inputs.py --run-dir canonical_stage_c/run2
writes canonical_stage_c/run2/run_input_lock.json:
    {generated_at_utc, run_dir, fetch_manifest_sha256,
     raw_files: [{name, sha256, bytes}], inputs_digest}
This freezes the cache-manifest part of B8 for the downstream Stage-C steps:
build and compare must run against exactly these bytes. Re-run this script
any time before build/compare to detect drift.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="B8 run-input hash lock")
    ap.add_argument("--run-dir", required=True,
                    help="run directory, e.g. canonical_stage_c/run2")
    args = ap.parse_args()
    RUN = Path(args.run_dir)
    manifest_p = RUN / "fetch_4h_manifest.json"
    raw_dir = RUN / "raw_1h"
    if not manifest_p.exists():
        raise SystemExit(f"no fetch manifest at {manifest_p}; fetch first")
    if not raw_dir.exists():
        raise SystemExit(f"no raw input dir at {raw_dir}; fetch first")

    manifest_sha = sha_file(manifest_p)
    raws = []
    for p in sorted(raw_dir.glob("*.csv")):
        raws.append({"name": p.name, "sha256": sha_file(p),
                     "bytes": p.stat().st_size})
    digest_src = manifest_sha + "\n" + "\n".join(
        f"{r['name']}:{r['sha256']}" for r in raws)
    lock = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(RUN),
        "fetch_manifest_sha256": manifest_sha,
        "n_raw_files": len(raws),
        "raw_files": raws,
        "inputs_digest": hashlib.sha256(digest_src.encode()).hexdigest(),
        "note": "B8 cache-manifest freeze: build_4h.py and compare_4h.py for "
                "this run must consume exactly these bytes.",
    }
    out = RUN / "run_input_lock.json"
    out.write_text(json.dumps(lock, indent=2))
    print(f"locked {len(raws)} raw files + manifest -> {out}")
    print(f"inputs_digest: {lock['inputs_digest']}")


if __name__ == "__main__":
    main()
