"""Two-process fencing worker (-14 req 3 fixture).

Usage: fence_worker.py CAP_DIR CID JOURNAL STAGING MANIFEST REMOTE_ROOT PINS_JSON
Publishes once against the shared directory-backed remote and prints exactly
one JSON line: {"status": ...} or {"hold": code} or {"error": repr}.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qfar1_publisher_h15 as qp
from qfar1_publisher_h15 import HoldError
from shared_remote import SharedFakeRemote


def main():
    cap_dir, cid, journal, staging, manifest, root, pins_path = sys.argv[1:8]
    with open(pins_path) as f:
        pins = json.load(f)
    remote = SharedFakeRemote(root)
    try:
        res = qp.publish(cap_dir, cid, remote, journal, staging, manifest,
                         validation_pins=pins)
        print(json.dumps({"status": res["status"]}))
    except HoldError as e:
        print(json.dumps({"hold": e.code}))
    except BaseException as e:  # noqa: BLE001 - fixture reports any failure verbatim
        print(json.dumps({"error": repr(e)}))


if __name__ == "__main__":
    main()
