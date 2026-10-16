"""Real-process partial-frame crash/restart worker (-15 req 4 fixture).

Modes:
  tear JOURNAL CID
      Append an intent-shaped record through the real qp._journal_append,
      but with os.write capped so only half the frame bytes land, then die
      via os._exit(3): a genuine torn final frame on disk, produced by the
      real write path in a real process. Exit code 3 = crashed as designed.
  publish CAP_DIR CID JOURNAL STAGING MANIFEST REMOTE_ROOT PINS_JSON
      Full publish against the shared directory-backed remote; prints one
      JSON line {"status": ...} / {"hold": code} / {"error": repr}.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qfar1_publisher_h15 as qp
from qfar1_publisher_h15 import HoldError
from shared_remote import SharedFakeRemote


def do_tear(journal, cid):
    rec = {"type": "intent", "capture_id": cid, "torn_marker": True}
    frame = qp._frame_bytes(dict(rec, seq=0))
    budget = {"left": len(frame) // 2}
    real_write = os.write

    def capped(fd, data):
        if budget["left"] <= 0:
            os._exit(3)
        n = real_write(fd, data[:budget["left"]])
        budget["left"] -= n
        if budget["left"] <= 0:
            os._exit(3)
        return n

    os.write = capped
    qp._journal_append(journal, rec)
    os._exit(4)  # unreachable if the cap fired


def do_publish(cap_dir, cid, journal, staging, manifest, root, pins_path):
    with open(pins_path) as f:
        pins = json.load(f)
    remote = SharedFakeRemote(root)
    try:
        res = qp.publish(cap_dir, cid, remote, journal, staging, manifest,
                         validation_pins=pins)
        print(json.dumps({"status": res["status"]}))
    except HoldError as e:
        print(json.dumps({"hold": e.code}))
    except BaseException as e:  # noqa: BLE001 - fixture reports verbatim
        print(json.dumps({"error": repr(e)}))


if __name__ == "__main__":
    if sys.argv[1] == "tear":
        do_tear(sys.argv[2], sys.argv[3])
    else:
        do_publish(*sys.argv[2:9])
