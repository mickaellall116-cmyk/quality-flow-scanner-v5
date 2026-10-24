"""DEV journal-only replay proof for -17: rebuild the governed DEV
recheck run from its journal alone and require byte identity."""
import importlib.util, json, os, sys
STAGE = os.path.abspath(sys.argv[1])
for p in (STAGE, os.path.join(STAGE, "engine_successor"),
          os.path.join(STAGE, "engine_successor", "pine_stack"),
          os.path.join(STAGE, "engine_successor", "pine_ranking"),
          os.path.join(STAGE, "engine_successor", "pine_exposure"),
          os.path.join(STAGE, "engine_successor", "pine_signal_quality")):
    sys.path.insert(0, p)
import pine_backtest as pb  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "fo17", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "fwd_observer17.py"))
fo = importlib.util.module_from_spec(spec); spec.loader.exec_module(fo)
cmp = json.load(open(os.path.join(STAGE, "work", "compare17_fork17.json")))
symbols = cmp["universe"]
table = fo.SessionTable(json.load(open(os.path.join(STAGE,
                                                    "session_table.json"))))
out_j = os.path.join(STAGE, "work", "replay17_journal.jsonl")
out_a = os.path.join(STAGE, "work", "anchors", "replay17.json")
ok, info = fo.replay_journal(
    os.path.join(STAGE, "work", "compare17_fork17_journal.jsonl"),
    os.path.join(STAGE, "work", "anchors", "compare17_fork17.json"),
    table, pb, symbols, out_j, out_a)
print("REPLAY_OK:", ok)
print(json.dumps(info, indent=1))
sys.exit(0 if ok else 2)
