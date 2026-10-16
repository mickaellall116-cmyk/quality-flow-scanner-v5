"""Real-process torn-append worker (-16 req 4): writes a byte-prefix of a
genuine next frame directly to the journal, fsyncs, then dies via
os._exit(3) -- a crash mid-append through the real frame builder.
Usage: crash_worker_h16.py <candidate_path> <journal_path> <record_json> <nbytes>
"""
import importlib.util
import json
import os
import sys


def main():
    cand_path, journal_path, record_json, nbytes = (
        sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
    spec = importlib.util.spec_from_file_location("cand", cand_path)
    cand = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cand)
    recs = cand._journal_read(journal_path)
    rec = dict(json.loads(record_json))
    rec["seq"] = len(recs)
    frame = cand._frame_bytes(rec)
    fd = os.open(journal_path, os.O_WRONLY)
    try:
        os.lseek(fd, 0, os.SEEK_END)
        os.write(fd, frame[:nbytes])
        os.fsync(fd)
    finally:
        os.close(fd)
    os._exit(3)


if __name__ == "__main__":
    main()
