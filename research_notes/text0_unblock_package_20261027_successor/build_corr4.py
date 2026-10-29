"""Build script for the Text 0 unblock SUCCESSOR package (corr4).

Derives every generated artifact of the package from its pinned
inputs, in an order that keeps the binding non-circular:

  1. hashes of the vendored artifacts (corr2 source, frozen engine
     modules, adopted session table) - all verified against the
     values recorded in the freeze record (P11 pins) before use;
  2. the Stage-1 binding CONTENT (binding id, stage, window, tier
     membership, session-table pin, corr2 pin, engine pins) and its
     canonical-content hash (corr2's canonical_sha semantics);
  3. exp14_buy_corr4.py - derived from the pinned corr2 source by
     the exact, asserted replacements below; the content hash from
     step 2 is compiled into it (the manifest does NOT pin corr4,
     so nothing is circular);
  4. build_holdout_inventory_corr4.py - its compiled-in content
     pin is set to the same hash; only then is the builder's own
     sha256 final;
  5. stage1_manifest.json - binding content + the builder pin +
     status fields (status/builder are outside the pinned content);
  6. corr2_to_corr4.diff and SHA256_MANIFEST.txt.

Tier membership derivation (verified 2026-10-29 against repo data
files; see tier_derivation.json): Tier 2 = the 44 UX51 equities of
research_notes/data_route_readiness_20261023_01/capture_manifest.json
minus the 25 names whose holdout legs the section-9 audit
quarantined (research_notes/s9_contamination_audit_20261026/
evidence/quarantine_census.json: 23 listed legs + PLTR via
plus_first_capture + SMCI via plus_pilot_step1) = 19 names.
Tier 3 = the frozen 12-name list minus GOOG (issuer-level
exclusion) = 11 names.
"""
import difflib
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CORR2 = os.path.join(HERE, "corr2_src", "exp14_buy_corr2.py")
CORR4 = os.path.join(HERE, "exp14_buy_corr4.py")
BUILDER = os.path.join(HERE, "build_holdout_inventory_corr4.py")
MANIFEST = os.path.join(HERE, "stage1_manifest.json")
TABLE = os.path.join(HERE, "session_table_751.json")
ENGINE = {n: os.path.join(HERE, "engine", n)
          for n in ("run_study13.py", "pine_backtest.py",
                    "scanner_rules.py")}

PIN_CORR2 = "77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8"
PIN_TABLE = "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"
PIN_ENGINE = {
    "run_study13.py":
        "4962e30d8b42124ebc317aab647351521d107b600c01a42905fce4c41ce4b22b",
    "pine_backtest.py":
        "874d2a9b1d99171a4d3db709ece9ce4719b4d108a70f7e95b4a082692cc0c99d",
    "scanner_rules.py":
        "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
}

TIER2 = ["AAPL", "AMD", "AMZN", "ARKK", "ARM", "AVGO", "COIN",
         "IWM", "LUNR", "META", "MSFT", "NFLX", "NIO", "NVDA",
         "SHOP", "SMH", "SPY", "TSLA", "XLF"]
TIER3 = ["AAOI", "ACN", "BABA", "BE", "BLK", "COF", "CRDO",
         "IREN", "MPWR", "SPOT", "TWLO"]
WINDOW_START, WINDOW_END = "2023-10-19", "2024-09-15"
BINDING_ID = "TEXT0-UNBLOCK-CORR4-STAGE1-20261029"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def replace_once(src, old, new, label):
    assert src.count(old) == 1, f"{label}: expected exactly 1 " \
        f"occurrence, found {src.count(old)}"
    return src.replace(old, new)


CORR4_DOCSTRING = '''"""EXP-14 / Text 0 - sealed-window pool-count matcher, CORR4.

SUCCESSOR of the CORR3 unblock draft (package commit e3f5e8e),
which ChatGPT's independent review put on HOLD with four blockers
(reproducibility, caller-override surface, circular manifest
completion, missing Tier 3 bytes). CORR4 is rebuilt from the
pinned CORR2 source (P11 pin 77bd53e8..., reproduced in corr2_src/)
and changes ONLY the binding, exactly as itemized in
corr2_to_corr4.diff and PACKAGE.md:

  - the domain is the SEALED holdout window
    [2023-10-19, 2024-09-15] and the frozen tier membership
    (19 Tier 2 + 11 Tier 3 names), compiled in below AND pinned by
    canonical-content hash in stage1_manifest.json, committed
    beside this file BEFORE any access (Stage 1);
  - the Stage-2 addendum (stage2_addendum.json) does not exist in
    this package and is created ONLY by the future reviewed
    Stage-2 session, after the inventory is built; it carries the
    inventory hash + census and must reference the Stage-1 content
    pin and the Stage-1 builder / session-table pins. The counting
    step creates no pins (non-circular staging);
  - there is no --manifest / --window / --symbols argument and no
    environment-variable latch: manifest, window, and membership
    exist only in the pinned package files;
  - a missing Tier 3 symbol fails closed with the NAMED error
    TIER3_INVENTORY_MISSING; the tier is never silently shrunk
    (Tier 3 holdout-window bytes do not exist yet - see
    DECISION_CARD_TIER3_BYTES.md).

Everything else - ladder, seeds, declustering, pool construction,
draw discipline, the returns machinery and its gates - is
BYTE-IDENTICAL to CORR2 (machine-verified by the package suite's
AST audit; the sole non-binding change is `import os`, which the
fixed-path binding needs and CORR2 did not import).
script_version is bumped to 5 inside run_pool_counts
so artifacts of this binding are distinguishable from CORR2 (3)
and the unadopted CORR3 draft (4).

This script computes pool SIZES only on the Text 0 path
(outcome-free by construction: no price is read for any return).
The returns path remains unauthorized and gated exactly as in
CORR2 (RETURNS_ENABLED is False; ExecutionGoRequired stands).
"""
'''

BINDING_CONSTANTS = '''# CORR4 BINDING (Text 0 successor package, 2026-10-29): corr2's
# DEV-domain constants (its frozen census and DEV window bounds)
# are replaced by the sealed-window binding below. The window and the
# tier membership are compiled in AND pinned by canonical-content
# hash in the Stage-1 manifest committed beside this file
# (stage1_manifest.json); load_stage1_manifest verifies the
# manifest's binding content against PINNED_BINDING_CONTENT_SHA256
# before any inventory byte is read, and the Stage-2 addendum -
# created only by the future reviewed session - must reference
# the same content hash. No CLI argument names a manifest, a
# window, a tier, or a symbol set.
WINDOW_START = "2023-10-19"
WINDOW_END = "2024-09-15"
TIER2 = ["AAPL", "AMD", "AMZN", "ARKK", "ARM", "AVGO", "COIN",
         "IWM", "LUNR", "META", "MSFT", "NFLX", "NIO", "NVDA",
         "SHOP", "SMH", "SPY", "TSLA", "XLF"]
TIER3 = ["AAOI", "ACN", "BABA", "BE", "BLK", "COF", "CRDO",
         "IREN", "MPWR", "SPOT", "TWLO"]
PINNED_BINDING_CONTENT_SHA256 = "@CONTENT_SHA@"
SESSION_TABLE_SHA256 = \\
    "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"
CORR2_SOURCE_SHA256 = \\
    "77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8"
STAGE1_MANIFEST_NAME = "stage1_manifest.json"
STAGE2_ADDENDUM_NAME = "stage2_addendum.json"
MANIFEST_FILE_KEYS = {"binding_id", "stage", "status",
                      "window_start", "window_end", "tiers",
                      "session_table_sha256", "corr2_source_sha256",
                      "engine", "builder", "stage2_addendum_file"}
MANIFEST_CONTENT_KEYS = ("binding_id", "stage", "window_start",
                         "window_end", "tiers",
                         "session_table_sha256",
                         "corr2_source_sha256", "engine")
ADDENDUM_KEYS = {"binding_id", "stage", "binding_content_sha256",
                 "inventory_sha256", "expected_fires",
                 "builder_sha256", "session_table_sha256",
                 "session"}'''

BINDING_FUNCTIONS = '''

def _package_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        name)


def load_stage1_manifest():
    """CORR4 Stage-1 binding: load stage1_manifest.json from beside
    this file (no caller-chosen path exists) and verify it BEFORE
    any inventory byte is read. The manifest's binding content -
    binding id, stage, window, tier membership, session-table pin,
    corr2 pin, engine pins - must hash (canonical_sha) to the
    compiled-in PINNED_BINDING_CONTENT_SHA256; window, tiers, and
    pins are then cross-checked against the compiled-in values.
    Any drift is FailClosedError."""
    path = _package_path(STAGE1_MANIFEST_NAME)
    if not os.path.exists(path):
        raise FailClosedError(
            "STAGE1_MANIFEST_MISSING: " + STAGE1_MANIFEST_NAME +
            " not found beside the matcher - the Stage-1 pins are "
            "a precondition of any counting session")
    try:
        with open(path) as f:
            m = json.load(f)
    except Exception as e:
        raise FailClosedError(f"stage1 manifest unparseable: {e}")
    if set(m) != MANIFEST_FILE_KEYS:
        raise FailClosedError(
            f"stage1 manifest key set drift: {sorted(m)}")
    content = {k: m[k] for k in MANIFEST_CONTENT_KEYS}
    if canonical_sha(content) != PINNED_BINDING_CONTENT_SHA256:
        raise FailClosedError(
            "stage1 manifest binding content != compiled-in pin "
            f"{PINNED_BINDING_CONTENT_SHA256} - refusing "
            "(manifest bytes are never trusted beyond the pinned "
            "content)")
    if m["stage"] != 1 or m["status"] != "STAGE1-PINS-COMMITTED":
        raise FailClosedError("stage1 manifest stage/status drift")
    if m["window_start"] != WINDOW_START \\
            or m["window_end"] != WINDOW_END:
        raise FailClosedError(
            "stage1 manifest window != compiled-in window "
            f"[{WINDOW_START}, {WINDOW_END}]")
    if m["tiers"] != {"tier2": TIER2, "tier3": TIER3}:
        raise FailClosedError(
            "stage1 manifest tiers != compiled-in tier membership")
    if m["session_table_sha256"] != SESSION_TABLE_SHA256:
        raise FailClosedError(
            "stage1 manifest session-table pin != compiled-in pin")
    if m["corr2_source_sha256"] != CORR2_SOURCE_SHA256:
        raise FailClosedError(
            "stage1 manifest corr2 pin != compiled-in pin")
    return m


def load_stage2_addendum(stage1):
    """CORR4 Stage-2 binding: the addendum is created ONLY by the
    future reviewed Stage-2 session, after the holdout inventory
    exists; its hash is entered in the freeze record before any
    counting run (PACKAGE.md states the staging - it is
    non-circular: the counting step completes and repins nothing).
    The addendum must reference the Stage-1 binding-content hash
    and the Stage-1 builder / session-table pins, and it carries
    the inventory hash + census the counting step verifies
    against. Its absence is the shipped state of this package and
    fails closed with a named error."""
    path = _package_path(STAGE2_ADDENDUM_NAME)
    if not os.path.exists(path):
        raise FailClosedError(
            "STAGE2_ADDENDUM_MISSING: " + STAGE2_ADDENDUM_NAME +
            " does not exist - Stage 2 has not run; no counting "
            "session is possible under this package until the "
            "reviewed Stage-2 session creates it")
    try:
        with open(path) as f:
            a = json.load(f)
    except Exception as e:
        raise FailClosedError(f"stage2 addendum unparseable: {e}")
    if set(a) != ADDENDUM_KEYS:
        raise FailClosedError(
            f"stage2 addendum key set drift: {sorted(a)}")
    if a["binding_id"] != stage1["binding_id"] or a["stage"] != 2:
        raise FailClosedError("stage2 addendum binding/stage drift")
    if a["binding_content_sha256"] != PINNED_BINDING_CONTENT_SHA256:
        raise FailClosedError(
            "stage2 addendum does not reference the pinned "
            "Stage-1 binding content")
    if a["builder_sha256"] != stage1["builder"]["sha256"]:
        raise FailClosedError(
            "stage2 addendum builder pin != Stage-1 builder pin")
    if a["session_table_sha256"] != stage1["session_table_sha256"]:
        raise FailClosedError(
            "stage2 addendum session-table pin != Stage-1 pin")
    if not isinstance(a["expected_fires"], int) \\
            or isinstance(a["expected_fires"], bool) \\
            or a["expected_fires"] <= 0:
        raise FailClosedError(
            "stage2 addendum census not a positive integer")
    return a


def verify_holdout_binding(by_symbol):
    """The loaded inventory's symbol set must equal the compiled-in
    Tier 2 + Tier 3 membership exactly, and every row's
    session_date must lie inside the sealed window. A missing
    Tier 3 symbol fails with the NAMED error
    TIER3_INVENTORY_MISSING - the tier is never silently shrunk
    (Tier 3 holdout-window bytes do not exist yet; see
    DECISION_CARD_TIER3_BYTES.md)."""
    have = set(by_symbol)
    missing3 = sorted(set(TIER3) - have)
    if missing3:
        raise FailClosedError(
            "TIER3_INVENTORY_MISSING: inventory carries no rows "
            f"for Tier 3 symbol(s) {missing3} - failing closed; "
            "the tier is never silently shrunk")
    missing2 = sorted(set(TIER2) - have)
    if missing2:
        raise FailClosedError(
            "TIER2_INVENTORY_MISSING: inventory carries no rows "
            f"for Tier 2 symbol(s) {missing2}")
    extra = sorted(have - set(TIER2) - set(TIER3))
    if extra:
        raise FailClosedError(
            "inventory symbol set != pinned tier membership: "
            f"unexpected symbol(s) {extra}")
    for sym, rows in by_symbol.items():
        for r in rows:
            d = str(r.get("session_date", ""))[:10]
            if not (WINDOW_START <= d <= WINDOW_END):
                raise FailClosedError(
                    "inventory row outside the sealed window: "
                    f"{sym}:{r.get('idx')} session_date {d}")
    return True
'''

OLD_POOL_HEAD = '''def run_pool_counts(by_symbol):
    # ---- census reconciliation (fail-closed) --------------------------
    total_fires = sum(len(fires_of(rows)) for rows in by_symbol.values())
    if total_fires != EXPECTED_FIRES:
        raise SystemExit(
            f"FAIL-CLOSED: inventory domain fires {total_fires} "
            f"!= P7 census {EXPECTED_FIRES}")
'''
NEW_POOL_HEAD = '''def run_pool_counts(by_symbol, expected_fires):
    # ---- census reconciliation (fail-closed) --------------------------
    # CORR4: the expectation is the sealed-window inventory's own
    # census, carried by the Stage-2 addendum under the Stage-1
    # content pin - not corr2's DEV P7 census (2892), which belongs
    # to a different domain (the recorded Text 0 STOP blocker).
    total_fires = sum(len(fires_of(rows)) for rows in by_symbol.values())
    if total_fires != expected_fires:
        raise SystemExit(
            f"FAIL-CLOSED: inventory domain fires {total_fires} "
            f"!= pinned holdout census {expected_fires}")
'''

OLD_CHECK = '''def _check_dev_ts(row, what):
    d = str(row.get("session_date", ""))[:10]
    if not (DEV_START <= d <= DEV_END):
        raise FailClosedError(
            f"non-DEV timestamp on {what}: {row.get('symbol')}:"
            f"{row.get('idx')} session_date {d} outside "
            f"[{DEV_START}, {DEV_END}]")
'''
NEW_CHECK = '''def _check_window_ts(row, what):
    # CORR4: corr2's DEV timestamp check, bound to the sealed
    # holdout window constants instead of the DEV window. The analysis path
    # that calls this remains gated (RETURNS_ENABLED is False).
    d = str(row.get("session_date", ""))[:10]
    if not (WINDOW_START <= d <= WINDOW_END):
        raise FailClosedError(
            f"out-of-window timestamp on {what}: {row.get('symbol')}:"
            f"{row.get('idx')} session_date {d} outside "
            f"[{WINDOW_START}, {WINDOW_END}]")
'''

OLD_MAIN_TAIL = '''    by_symbol = load_inventory(args.inventory, args.inventory_sha)
    report, cohort, draws = run_pool_counts(by_symbol)
'''
NEW_MAIN_TAIL = '''    # CORR4 staged binding (pool-counts): the Stage-1 manifest is
    # verified against the compiled-in binding-content pin BEFORE
    # anything is loaded; the Stage-2 addendum must reference the
    # same content pin and the Stage-1 builder / session-table
    # pins; the inventory is loaded against the ADDENDUM's recorded
    # hash (a supplied --inventory-sha that disagrees is a wiring
    # error, exactly as in the returns branch above); tier
    # membership and window are verified before any pool is
    # counted. No argument names a manifest, window, tier, or
    # symbol set - those exist only in the pinned package files.
    try:
        stage1 = load_stage1_manifest()
        addendum = load_stage2_addendum(stage1)
    except FailClosedError as e:
        print(f"FAIL-CLOSED: {e}", file=sys.stderr)
        return 2
    if args.inventory_sha != addendum["inventory_sha256"]:
        print("FAIL-CLOSED: supplied --inventory-sha "
              f"{args.inventory_sha} != stage2 addendum inventory "
              f"{addendum['inventory_sha256']} (caller-supplied "
              "hashes are not trusted)", file=sys.stderr)
        return 2
    by_symbol = load_inventory(args.inventory,
                               addendum["inventory_sha256"])
    try:
        verify_holdout_binding(by_symbol)
    except FailClosedError as e:
        print(f"FAIL-CLOSED: {e}", file=sys.stderr)
        return 2
    report, cohort, draws = run_pool_counts(
        by_symbol, addendum["expected_fires"])
'''


def build_corr4(content_sha):
    src = open(CORR2).read()
    # R1: docstring - everything through the first closing quotes.
    end = src.index('"""', 3) + 3
    src = CORR4_DOCSTRING + src[end:]
    # R1b: the binding resolves fixed package paths (corr2 never
    # imported os; nothing else about the import block changes).
    src = replace_once(src, "import math\nimport sys\n",
                       "import math\nimport os\nimport sys\n",
                       "os import")
    # R2: domain constants -> CORR4 binding constants.
    src = replace_once(
        src,
        'EXPECTED_FIRES = 2892\nDEV_START = "2024-09-16"\n'
        'DEV_END = "2026-10-16"\n',
        BINDING_CONSTANTS.replace("@CONTENT_SHA@", content_sha) + "\n",
        "constants")
    # R3: binding functions before load_inventory.
    src = replace_once(src, "\n\ndef load_inventory(",
                       BINDING_FUNCTIONS + "\n\ndef load_inventory(",
                       "binding functions")
    # R4: run_pool_counts head + script_version 3 -> 5 (3 sites,
    # all inside run_pool_counts).
    src = replace_once(src, OLD_POOL_HEAD, NEW_POOL_HEAD, "pool head")
    assert src.count('"script_version": 3') == 3
    src = src.replace('"script_version": 3', '"script_version": 5')
    # R5: window check rename.
    src = replace_once(src, OLD_CHECK, NEW_CHECK, "window check")
    # R6: the two call sites in _analysis_impl.
    src = replace_once(src, '_check_dev_ts(row, "cohort event")',
                       '_check_window_ts(row, "cohort event")',
                       "call site 1")
    src = replace_once(src, '_check_dev_ts(row, f"{arm} control")',
                       '_check_window_ts(row, f"{arm} control")',
                       "call site 2")
    # R7: main() pool-counts tail.
    src = replace_once(src, OLD_MAIN_TAIL, NEW_MAIN_TAIL, "main tail")
    assert "EXPECTED_FIRES" not in src and "DEV_START" not in src \
        and "_check_dev_ts" not in src
    with open(CORR4, "w") as f:
        f.write(src)
    return src


def main():
    # Step 1: verify vendored pins.
    assert sha256_file(CORR2) == PIN_CORR2, "corr2 pin drift"
    assert sha256_file(TABLE) == PIN_TABLE, "session table pin drift"
    for name, path in ENGINE.items():
        assert sha256_file(path) == PIN_ENGINE[name], \
            f"engine pin drift: {name}"
    # Step 2: binding content + its canonical hash.
    content = {
        "binding_id": BINDING_ID,
        "stage": 1,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "tiers": {"tier2": TIER2, "tier3": TIER3},
        "session_table_sha256": PIN_TABLE,
        "corr2_source_sha256": PIN_CORR2,
        "engine": dict(PIN_ENGINE),
    }
    content_sha = canonical_sha(content)
    # Step 3: derive corr4.
    corr4_src = build_corr4(content_sha)
    # Step 4: set the builder's compiled-in content pin, then hash.
    bsrc = open(BUILDER).read()
    bsrc, n = re.subn(
        r'PINNED_BINDING_CONTENT_SHA256 = "[0-9a-f]{64}"',
        f'PINNED_BINDING_CONTENT_SHA256 = "{content_sha}"', bsrc)
    assert n == 1, "builder content-pin literal not found"
    with open(BUILDER, "w") as f:
        f.write(bsrc)
    builder_sha = sha256_file(BUILDER)
    # Step 5: Stage-1 manifest (content + non-content fields).
    manifest = dict(content)
    manifest["status"] = "STAGE1-PINS-COMMITTED"
    manifest["builder"] = {
        "file": "build_holdout_inventory_corr4.py",
        "sha256": builder_sha}
    manifest["stage2_addendum_file"] = "stage2_addendum.json"
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    # Step 6: diff + package hash manifest.
    diff = difflib.unified_diff(
        open(CORR2).read().splitlines(keepends=True),
        corr4_src.splitlines(keepends=True),
        fromfile="exp14_buy_corr2.py (P11 pin 77bd53e8)",
        tofile="exp14_buy_corr4.py")
    with open(os.path.join(HERE, "corr2_to_corr4.diff"), "w") as f:
        f.writelines(diff)
    files = [
        "PACKAGE.md", "DECISION_CARD_TIER3_BYTES.md",
        "build_corr4.py", "stage1_manifest.json",
        "tier_derivation.json", "exp14_buy_corr4.py",
        "build_holdout_inventory_corr4.py", "corr2_to_corr4.diff",
        "session_table_751.json", "corr2_src/exp14_buy_corr2.py",
        "engine/run_study13.py", "engine/pine_backtest.py",
        "engine/scanner_rules.py", "fixtures/make_fixtures.py",
        "fixtures/synth_inventory.jsonl",
        "fixtures/fixture_stage1_manifest.json",
        "fixtures/fixture_stage2_addendum.json",
        "test_text0_unblock_successor.py",
    ]
    lines = []
    for rel in files:
        p = os.path.join(HERE, rel)
        assert os.path.exists(p), f"missing package file: {rel}"
        lines.append(f"{sha256_file(p)}  {rel}")
    with open(os.path.join(HERE, "SHA256_MANIFEST.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"binding content sha256: {content_sha}")
    print(f"builder sha256:         {builder_sha}")
    print(f"corr4 sha256:           {sha256_file(CORR4)}")
    print(f"stage1 manifest sha256: {sha256_file(MANIFEST)}")
    print("package built")


if __name__ == "__main__":
    main()
