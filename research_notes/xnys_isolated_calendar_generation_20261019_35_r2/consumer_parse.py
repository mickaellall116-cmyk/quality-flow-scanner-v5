#!/usr/bin/env python3
"""R8 consumer check: parse the generated artifact with fold_materializer_v3
(byte-unmodified, sha e1b0dfed...) using SYNTHETIC timestamps only —
timestamps are constructed mechanically from the artifact's own session
list (09:30 anchor for every session, 13:30 anchor added iff the session
close is 16:00, per the Amendment v3 anchor rule). No market data."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "notes_mirror" / "validation_fold_coverage_boundary_20261018_28"))
import fold_materializer_v3 as fm

blob = (HERE / "out" / "artifact_run1.json").read_bytes()
sha = hashlib.sha256(blob).hexdigest()
doc = json.loads(blob.decode("utf-8"))
ts = []
for s in doc["sessions"]:
    ts.append(f'{s["date"]}T09:30')
    if s["close"] == "16:00":
        ts.append(f'{s["date"]}T13:30')
result = fm.materialize(ts, blob, sha)
out = {
    "materialize_ok": True,
    "coverage_first_session": result["coverage_first_session"],
    "coverage_last_session": result["coverage_last_session"],
    "calendar_digest": result.get("calendar_digest"),
    "synthetic_timestamps": len(ts),
    "folds": len(result.get("folds", [])),
}
print(json.dumps(out, indent=1))
(HERE / "out" / "consumer_parse_result.json").write_text(json.dumps(out, indent=1) + "\n")
