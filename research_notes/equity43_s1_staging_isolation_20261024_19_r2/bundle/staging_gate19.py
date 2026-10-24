"""QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19 — staging gate.

The ONLY entry point of the S1 staging bundle. Stdlib-only. It verifies,
fail-closed and BEFORE any processing:

  * namespace isolation — the bundle's config/state/journal/log/output
    namespace is a dedicated research tree, disjoint (by canonical
    realpath) from the PAUSED production tree and every protected
    production namespace inside it; no write target is a symlink or
    escapes the namespace; production files are read ONLY as identity
    checks;
  * exact pins — every pin of the -17 r2 structured inventory that is a
    bundle input (observer module, 14 source pins, experiment config,
    sector map) recomputed from bundle bytes, plus the -18 calendar
    binding (extended table SHA 86a1d4ea..., 751-row prefix identity,
    generator SHA, repin record); drift STOPs the bundle;
  * PAUSED production evidence — deployed harness SHA, PAUSE_NEW_ENTRIES
    present, RESUME_NEW_ENTRIES absent, checked read-only;
  * journal freshness — a staging namespace whose journal/state is
    pre-populated is refused;
  * launch authority — absent or malformed T0/launch authority, and the
    standing qualification record (G4 UNADOPTED, prospective feed
    UNQUALIFIED), hold the bundle at LAUNCH_HOLD. In this staging bundle
    processing against a feed is structurally unreachable: the only
    observer construction path requires a synthetic-test namespace.

Signal-only is a property of the wired call graph, proven two ways:
static_audit() inventories every bundle module's imports and the
order/broker/network/vendor surface (must be empty), and the battery
traces a synthetic replay to prove no simulator/order function executes
and no network is attempted. The gate itself never imports the engine;
the replay helper imports exactly one engine module (pine_backtest, the
observer's pinned signal-primitive source) inside the bundle.

Verdicts: PREP_READY / LAUNCH_HOLD, or STOP_<reason>. PREP_READY is a
staging verdict only — not launch, not edge evidence.
"""
import ast
import hashlib
import json
import os
import sys

CONTRACT = "QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19"
BUNDLE_ROOT = os.path.dirname(os.path.abspath(__file__))

NETWORK_MODULES = {"socket", "urllib", "http", "http.client", "requests",
                   "httpx", "aiohttp", "ftplib", "smtplib", "telnetlib",
                   "websocket", "websockets", "ssl", "asyncio"}
VENDOR_MODULES = {"yfinance", "alpaca", "tiingo", "twelvedata",
                  "databento", "kraken", "coinbase", "ccxt", "finnhub",
                  "openrouter"}
ORDER_TOKENS = ("place_order", "submit_order", "create_order",
                "cancel_order", "broker", "paper_fill", "execute_order",
                "RESUME_NEW_ENTRIES")
SIMULATOR_FUNCS = {"simulate_portfolio", "simulate_stack", "run_universe",
                   "run_case", "gen_pine_trades", "summarize", "_outcome",
                   "load_bull", "load_2022", "main"}
SIGNAL_KEYS = {"symbol", "signal_time", "entry_time", "entry", "stop",
               "tp1", "kind"}
FORBIDDEN_OUTPUT_KEYS = {"equity", "pnl", "r", "r_multiple", "return",
                         "returns", "cash", "shares", "size", "position",
                         "order", "fill", "profit", "exit", "exit_time",
                         "reason", "hold_bars"}
PROTECTED_PROD_SUBPATHS = ("forward_test", "v54_forward", "v54_forward_1h",
                           "v54_forward_1d", "signal_log", "pine_live",
                           "forward_test/PAUSE_NEW_ENTRIES")
NS_SUBDIRS = ("config", "state", "journal", "anchors", "logs", "outputs")
AUDIT_EXEMPT_MODULES = {"staging_gate19.py"}  # holds the token list itself


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_hash(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class GateStop(Exception):
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# ------------------------------------------------------------------ audit
def static_audit(bundle_root=BUNDLE_ROOT):
    """Inventory every bundle .py module: imports, defined functions,
    and the order/broker/network/vendor surface. Returns a dict; an
    empty 'violations' list means the wired surface is signal-only.
    staging_gate19.py itself is exempt from the token scan (it carries
    the token list as data) but not from the import scan."""
    modules = {}
    violations = []
    for dirpath, _dirs, files in os.walk(bundle_root):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, bundle_root)
            text = open(path).read()
            tree = ast.parse(text, filename=rel)
            imports, funcs = set(), set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                elif isinstance(node, ast.FunctionDef):
                    funcs.add(node.name)
            roots = {i.split(".")[0] for i in imports}
            bad_net = roots & NETWORK_MODULES
            bad_ven = roots & VENDOR_MODULES
            if bad_net:
                violations.append(f"{rel}: network imports {sorted(bad_net)}")
            if bad_ven:
                violations.append(f"{rel}: vendor imports {sorted(bad_ven)}")
            if fn not in AUDIT_EXEMPT_MODULES:
                toks = [t for t in ORDER_TOKENS if t in text]
                if toks:
                    violations.append(f"{rel}: order-surface tokens {toks}")
            modules[rel] = {"imports": sorted(imports),
                            "functions": sorted(funcs),
                            "sha256": sha256_file(path)}
    gate_mods = modules.get("staging_gate19.py", {})
    obs_mods = modules.get(os.path.join("observer", "fwd_observer17.py"),
                           {})
    return {"modules": modules, "violations": violations,
            "gate_imports": gate_mods.get("imports", []),
            "observer_imports": obs_mods.get("imports", []),
            "simulator_functions_present_in_pinned_sources":
                sorted({f for m in modules.values() for f in m["functions"]}
                       & SIMULATOR_FUNCS),
            "note": "simulator functions exist inside the pinned engine "
                    "sources (byte-identical, uneditable under the pins) "
                    "but no bundle entry point imports pine_stack or "
                    "calls them; the battery's execution trace proves "
                    "they never run in the staging call graph."}


# ------------------------------------------------------------------- gate
class StagingGate:
    def __init__(self, namespace_root, production_root,
                 bundle_root=BUNDLE_ROOT, namespace_class="staging"):
        self.bundle_root = os.path.abspath(bundle_root)
        self.namespace_root = namespace_root
        self.production_root = production_root
        self.namespace_class = namespace_class
        self.pins = json.load(open(os.path.join(
            self.bundle_root, "pins", "PINS19.json")))
        self._lock_path = None

    # ---------------------------------------------------------- namespace
    def ns(self, sub=""):
        return os.path.join(self.namespace_root, sub) if sub \
            else self.namespace_root

    def check_namespace(self):
        ns_real = os.path.realpath(self.namespace_root)
        prod_real = os.path.realpath(self.production_root)
        if ns_real == prod_real or ns_real.startswith(prod_real + os.sep) \
                or prod_real.startswith(ns_real + os.sep):
            raise GateStop("STOP_NAMESPACE_OVERLAP",
                           f"namespace {ns_real} overlaps production "
                           f"{prod_real}")
        for sub in PROTECTED_PROD_SUBPATHS:
            p = os.path.realpath(os.path.join(prod_real, sub))
            if ns_real == p or ns_real.startswith(p + os.sep):
                raise GateStop("STOP_NAMESPACE_OVERLAP",
                               f"namespace inside protected {sub}")
        # symlink components of the namespace root itself
        cur = os.path.abspath(self.namespace_root)
        chain = []
        while True:
            chain.append(cur)
            nxt = os.path.dirname(cur)
            if nxt == cur:
                break
            cur = nxt
        for comp in chain:
            if os.path.islink(comp):
                raise GateStop("STOP_NAMESPACE_ESCAPE",
                               f"namespace path component is a symlink: "
                               f"{comp}")
        # write-target containment for existing tree
        for dirpath, dirnames, filenames in os.walk(self.namespace_root):
            for name in dirnames + filenames:
                p = os.path.join(dirpath, name)
                if os.path.islink(p):
                    tgt = os.path.realpath(p)
                    if not (tgt == ns_real
                            or tgt.startswith(ns_real + os.sep)):
                        raise GateStop(
                            "STOP_NAMESPACE_ESCAPE",
                            f"symlink inside namespace escapes: {p} "
                            f"-> {tgt}")
        return {"namespace_realpath": ns_real,
                "production_realpath": prod_real, "overlap": False}

    def check_kill(self):
        if os.path.exists(self.ns("KILL")):
            raise GateStop("STOP_KILLED", "namespace KILL switch present")

    # --------------------------------------------------------------- lock
    def acquire_lock(self):
        os.makedirs(self.namespace_root, exist_ok=True)
        self._lock_path = self.ns(".staging.lock")
        try:
            fd = os.open(self._lock_path,
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise GateStop("STOP_LOCK_HELD",
                           f"lock already held: {self._lock_path}")
        os.write(fd, json.dumps(
            {"contract": CONTRACT, "pid": os.getpid()}).encode())
        os.close(fd)

    def release_lock(self):
        if self._lock_path and os.path.exists(self._lock_path):
            os.remove(self._lock_path)
        self._lock_path = None

    # --------------------------------------------------------------- pins
    def _bundle_path(self, rel):
        return os.path.join(self.bundle_root, rel)

    def check_pins(self):
        checked = {}
        obs = self.pins["observer"]
        got = sha256_file(self._bundle_path(obs["bundle_path"]))
        if got != obs["sha256"]:
            raise GateStop("STOP_PIN_DRIFT",
                           f"observer {got} != {obs['sha256']}")
        checked["observer_module_sha256"] = got
        n_src = 0
        for name, rec in self.pins["source_pins"].items():
            got = sha256_file(self._bundle_path(rec["bundle_path"]))
            if got != rec["sha256"]:
                raise GateStop("STOP_PIN_DRIFT",
                               f"source pin {name}: {got} != "
                               f"{rec['sha256']}")
            n_src += 1
        checked["source_pins"] = n_src
        cfg = json.load(open(self._bundle_path(
            "config/experiment_config.json")))
        got = canon_hash(cfg)
        if got != self.pins["experiment_config_sha256"]:
            raise GateStop("STOP_PIN_DRIFT",
                           f"experiment_config {got} != "
                           f"{self.pins['experiment_config_sha256']}")
        checked["experiment_config_sha256"] = got
        cal = self.pins["calendar_binding_18"]
        for key, pathkey in (("adopted_prefix_table_sha256",
                              "prefix_table_bundle_path"),
                             ("extended_table_sha256",
                              "extended_table_bundle_path"),
                             ("generator_sha256", "generator_bundle_path")):
            got = sha256_file(self._bundle_path(cal[pathkey]))
            if got != cal[key]:
                raise GateStop("STOP_PIN_DRIFT",
                               f"calendar {key}: {got} != {cal[key]}")
            checked[key] = got
        ext = json.load(open(self._bundle_path(
            cal["extended_table_bundle_path"])))
        base = json.load(open(self._bundle_path(
            cal["prefix_table_bundle_path"])))
        if len(ext["sessions"]) != cal["sessions_total"] \
                or len(base["sessions"]) != cal["sessions_prefix"] \
                or ext["sessions"][:cal["sessions_prefix"]] \
                != base["sessions"]:
            raise GateStop("STOP_PIN_DRIFT",
                           "extended table prefix/count identity failed")
        checked["calendar_prefix_rows"] = cal["sessions_prefix"]
        repin = json.load(open(self._bundle_path(
            cal["repin_record_bundle_path"])))
        if repin["table_sha256"] != cal["extended_table_sha256"] \
                or repin["supersedes_table_sha256"] \
                != cal["adopted_prefix_table_sha256"] \
                or repin["session_count"] != cal["sessions_total"]:
            raise GateStop("STOP_PIN_DRIFT", "repin record cross-check "
                                             "failed")
        checked["repin_record"] = "ok"
        return checked

    def check_universe_and_sector(self):
        uni = json.load(open(self._bundle_path("config/universe43.json")))
        symbols = uni["symbols"]
        if len(symbols) != 43 or len(set(symbols)) != 43:
            raise GateStop("STOP_UNIVERSE",
                           f"universe count/distinct = {len(symbols)}/"
                           f"{len(set(symbols))}")
        sys.path.insert(0, self._bundle_path(
            os.path.join("engine", "pine_exposure")))
        try:
            from pine_exposure import SECTOR
        finally:
            sys.path.pop(0)
        sector = {s: SECTOR[s] for s in symbols}
        # exactly the -17 r2 emitter's construction (default separators)
        got = hashlib.sha256(json.dumps(
            sector, sort_keys=True).encode()).hexdigest()
        if got != self.pins["sector_map_sha256"]:
            raise GateStop("STOP_PIN_DRIFT",
                           f"sector_map {got} != "
                           f"{self.pins['sector_map_sha256']}")
        return {"universe_count": 43, "sector_map_sha256": got}

    def check_paused(self, production_root=None):
        root = production_root or self.production_root
        pp = self.pins["paused_production_pins"]
        harness = os.path.join(root, "v54_forward_harness.py")
        got = sha256_file(harness) if os.path.exists(harness) else None
        pause = os.path.exists(os.path.join(
            root, "forward_test", "PAUSE_NEW_ENTRIES"))
        resume = os.path.exists(os.path.join(
            root, "forward_test", "RESUME_NEW_ENTRIES"))
        if got != pp["harness_sha256"]:
            raise GateStop("STOP_PAUSED_PIN_DRIFT",
                           f"harness {got} != {pp['harness_sha256']}")
        if pause != pp["pause_new_entries_present"]:
            raise GateStop("STOP_PAUSED_PIN_DRIFT",
                           "PAUSE_NEW_ENTRIES presence differs from pin")
        if resume != pp["resume_new_entries_present"]:
            raise GateStop("STOP_PAUSED_PIN_DRIFT",
                           "RESUME_NEW_ENTRIES presence differs from "
                           "pin")
        return {"harness_sha256": got, "pause_new_entries_present": pause,
                "resume_new_entries_present": resume}

    # ------------------------------------------------------- journal etc.
    def check_journal_fresh(self):
        for sub in ("journal", "state", "anchors"):
            d = self.ns(sub)
            if os.path.isdir(d) and os.listdir(d):
                raise GateStop("STOP_JOURNAL_PREPOPULATED",
                               f"{sub}/ is pre-populated: "
                               f"{sorted(os.listdir(d))}")

    def launch_hold_reasons(self):
        reasons = []
        q = self.pins["qualification_record"]
        if q["g4_vbasis"] != "ADOPTED":
            reasons.append("G4_VBASIS_UNADOPTED")
        if not q["prospective_feed_rights"].startswith("QUALIFIED"):
            reasons.append("FEED_RIGHTS_UNQUALIFIED")
        auth_path = self.ns(os.path.join("config", "LAUNCH_AUTHORITY.json"))
        if not os.path.exists(auth_path):
            reasons.append("T0_AUTHORITY_ABSENT")
        else:
            try:
                auth = json.load(open(auth_path))
                need = {"t0", "mike_go_ref", "feed_qualification",
                        "g4_adoption"}
                if not need.issubset(set(auth)) or not auth.get("t0"):
                    reasons.append("T0_AUTHORITY_MALFORMED")
            except Exception:
                reasons.append("T0_AUTHORITY_MALFORMED")
        return reasons

    # ------------------------------------------------------------ preflight
    def preflight(self):
        """Full fail-closed preflight. Returns the staging report:
        PREP_READY / LAUNCH_HOLD, or raises GateStop."""
        self.check_namespace()
        self.check_kill()
        self.acquire_lock()
        try:
            pins = self.check_pins()
            uni = self.check_universe_and_sector()
            paused = self.check_paused()
            self.check_journal_fresh()
        finally:
            self.release_lock()
        audit = static_audit(self.bundle_root)
        if audit["violations"]:
            raise GateStop("STOP_AUDIT_SURFACE",
                           "; ".join(audit["violations"]))
        return {"contract": CONTRACT,
                "verdict": "PREP_READY", "launch": "LAUNCH_HOLD",
                "launch_hold_reasons": self.launch_hold_reasons(),
                "namespace": self.check_namespace(),
                "pins_checked": pins, "universe_sector": uni,
                "paused_production": paused,
                "audit_violations": audit["violations"],
                "labels": ["STAGING ONLY — NOT LAUNCHED",
                           "NOT EDGE EVIDENCE"]}


    # ------------------------------------------------- observer (synthetic)
    def build_observer(self, symbols):
        """Construct the pinned observer inside THIS namespace.
        Reachable ONLY for synthetic-test namespaces: in a staging
        namespace the launch hold makes processing structurally
        unreachable. The observer is the byte-pinned -17/-18 module;
        it is constructed armed=False (offline evidence mode) with the
        production PAUSE sentinel wired as its gate input."""
        if self.namespace_class != "synthetic_test":
            raise GateStop("STOP_LAUNCH_HOLD",
                           "processing is unreachable in a staging "
                           "namespace (LAUNCH_HOLD)")
        self.check_kill()
        for sub in NS_SUBDIRS:
            os.makedirs(self.ns(sub), exist_ok=True)
        eng = self._bundle_path("engine")
        for p in (self._bundle_path("observer"), eng,
                  os.path.join(eng, "pine_stack"),
                  os.path.join(eng, "pine_ranking"),
                  os.path.join(eng, "pine_exposure"),
                  os.path.join(eng, "pine_signal_quality")):
            if p not in sys.path:
                sys.path.insert(0, p)
        import fwd_observer17 as fo
        import pine_backtest as pb
        table = fo.SessionTable(json.load(open(self._bundle_path(
            self.pins["calendar_binding_18"]
            ["extended_table_bundle_path"]))))
        journal = fo.Journal(
            self.ns(os.path.join("journal", "observer_journal.jsonl")),
            self.ns(os.path.join("anchors", "journal_anchor.json")))
        sentinel = os.path.join(self.production_root, "forward_test",
                                "PAUSE_NEW_ENTRIES")
        obs = fo.ForwardObserver(table, journal, pb, symbols,
                                 sentinel_path=sentinel, armed=False)
        return fo, obs, journal


def signal_record(candidate_record):
    """Map one frozen candidate record to the S1 signal-only output
    record. Exactly SIGNAL_KEYS — observation fields only; no exit,
    no R, no equity, no sizing."""
    rec = {"symbol": candidate_record["symbol"],
           "signal_time": candidate_record["signal_time"],
           "entry_time": str(candidate_record["entry_time"]),
           "entry": candidate_record["entry"],
           "stop": candidate_record["stop"],
           "tp1": candidate_record["tp1"],
           "kind": "SIGNAL"}
    assert set(rec) == SIGNAL_KEYS
    assert not (set(rec) & FORBIDDEN_OUTPUT_KEYS)
    return rec


def replay_synthetic(gate, symbols, rows_by_symbol):
    """Replay a synthetic in-memory row stream through the gated
    observer. Test/battery use only: rows are fabricated fixtures, not
    market data.

    r2 kill-boundary correction (governing comment 6383355565): the
    KILL switch is checked immediately before EVERY raw-row ingest,
    before flush, before candidate/signal extraction, and before the
    final anchor/seal — a KILL raised at any of those points stops the
    run at that point (STOP_KILLED), before any later INPUT/BAR/signal
    record or the completion anchor is written. (r1 checked once per
    symbol, before that symbol's rows; a KILL created mid-symbol was
    not noticed until the next symbol.) On a kill stop the wrapper
    seals the journal prefix to the external anchor
    ("STOP_KILLED - prefix seal") and closes the journal before
    re-raising, so the partial journal still verifies. Returns
    (signal_records, observer, journal)."""
    fo, obs, journal = gate.build_observer(symbols)
    signals = []
    seen_candidates = set()
    try:
        for sym in symbols:
            for row in rows_by_symbol[sym]:
                gate.check_kill()
                obs.ingest(sym, row)
            gate.check_kill()
            obs.flush()
            gate.check_kill()
            for rec in obs.candidates():
                key = (rec["symbol"], rec["signal_idx"])
                if key not in seen_candidates:
                    seen_candidates.add(key)
                    signals.append(signal_record(rec))
        gate.check_kill()
    except GateStop as e:
        if e.code == "STOP_KILLED":
            try:
                journal.anchor("STOP_KILLED - prefix seal")
            except Exception:
                pass  # never mask the kill stop with a seal failure
            journal.close()
        raise
    journal.anchor("synthetic replay complete")
    journal.close()
    return signals, obs, journal


if __name__ == "__main__":
    # CLI: preflight only. Never processes a feed.
    #   staging_gate19.py preflight <namespace> <production_root>
    if len(sys.argv) == 4 and sys.argv[1] == "preflight":
        gate = StagingGate(sys.argv[2], sys.argv[3])
        try:
            rep = gate.preflight()
        except GateStop as e:
            print(json.dumps({"verdict": e.code, "detail": e.detail}))
            sys.exit(2)
        print(json.dumps(rep, indent=1))
        sys.exit(3 if rep["launch"] == "LAUNCH_HOLD" else 0)
    print(__doc__)
    sys.exit(64)
