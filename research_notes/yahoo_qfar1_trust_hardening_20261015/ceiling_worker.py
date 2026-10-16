"""Ceiling-size end-to-end publication worker (-14 req 6).

Runs ONE full publish of a ceiling-size capture in a clean process against
the shared directory-backed fake remote, then prints one JSON line with the
outcome, elapsed seconds and THIS process's peak RSS (ru_maxrss) for the
complete publisher path (seal -> base64 blob -> tree -> commit -> ref update
-> re-fetch/DAG verification). Usage:
  ceiling_worker.py CAP_DIR CID JOURNAL STAGING MANIFEST REMOTE_ROOT PINS_JSON
"""
import json
import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qfar1_publisher_h14 as qp
from qfar1_publisher_h14 import HoldError
from shared_remote import SharedFakeRemote


def main():
    cap_dir, cid, journal, staging, manifest, root, pins_path = sys.argv[1:8]
    with open(pins_path) as f:
        pins = json.load(f)
    remote = SharedFakeRemote(root)
    t0 = time.monotonic()
    try:
        res = qp.publish(cap_dir, cid, remote, journal, staging, manifest,
                         validation_pins=pins)
        out = {"status": res["status"], "container_len": res["container_len"]}
    except HoldError as e:
        out = {"hold": e.code}
    except BaseException as e:  # noqa: BLE001
        out = {"error": repr(e)}
    out["elapsed_s"] = round(time.monotonic() - t0, 3)
    out["peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
