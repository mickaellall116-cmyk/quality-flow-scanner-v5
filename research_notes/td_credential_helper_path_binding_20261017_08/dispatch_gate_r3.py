#!/usr/bin/env python3
"""QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05 r2 - fail-closed executable
dispatch gate around the accepted -04 integrated driver candidate
(live_driver.py sha256 5fed4524...).

Closes the integration boundary gap named in
FRESH_LIVE_DRIVER_INTEGRATION_PASS_OFFLINE_LIVE_HOLD_DISPATCH_GATE
(Issue #1 comment 6227935189): the -04 Runner accepted caller-supplied
account_mode, a caller-supplied clock, and an already-constructed armed
transport, so the 12-gate live_pre_dispatch_checklist was a document,
not an enforcement. This wrapper is the ONLY arming path it exposes:

- live mode uses the actual UTC system clock; an injected clock (or any
  other test seam) in live mode refuses before any file access;
- it consumes ONE immutable, canonical, hash-bound pre-dispatch
  evidence object and evaluates ALL 12 checklist gates executably,
  each against a recomputed pin or a read-only state probe; any gate
  FAIL or UNKNOWN -> HOLD;
- it writes a canonical gate receipt durably (fsync, exclusive-create)
  BEFORE any transport construction; LiveHttpsTransport(armed=True) is
  constructed only after a PASS receipt exists, only via the wrapper's
  own factory, and only when a --dispatch token bound to (run_id,
  manifest digest, evidence digest, ledger path, dispatch window)
  verifies. Default / dry-run never arms;
- account_mode is DERIVED from the verified receipt ("known" iff the
  account gate passed on timestamped Basic / good-standing / >=51
  capacity evidence); dispatch() accepts no account_mode parameter.

On any failure the wrapper performs zero mutating access: it never
constructs the Runner (so no namespace is created or written), never
constructs a transport, and never writes the shared ledger (gate
evaluation reads ledger bytes only). Offline trials inject the seams
(test_mode) explicitly; the CLI entrypoint never enables them.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

TASK = "QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05"
REVISION = "r3-pathbound-08"

# --- pinned artifact locations (repo-relative) and hashes: the -04
# checklist pin table, recomputed by the gates below ---
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
P_DRIVER = "research_notes/td_fresh_live_driver_integration_evidence_20261016/live_driver.py"
P_MANIFEST = "research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json"
P_SUPPLEMENT = "research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_supplement.json"
P_COLLECTOR_GIT = ("ab254c3458697dd450356146abcf4ad4f75ecef4",
                   "research_notes/td_lifecycle_repair_candidate/td_min_collector.py")
P_PILOT_ACQUIRE = "research_notes/pilot_harness/pilot_acquire.py"
P_RATE_LIMITER = "research_notes/pilot_harness/rate_limiter.py"
P_MECHANISM = "research_notes/pilot_harness/validate_input.py"
P_LOCK = "research_notes/td_nl_env_rebuild_evidence_20261016/lock_copy.txt"
P_ADAPTER = "research_notes/td_p2_spot_v2_execution_preflight_evidence_20261015/adapter_contract.json"
P_PREREQ = "research_notes/td_p2_spot_v2_execution_preflight_evidence_20261015/prerequisites_pinned.json"
P_OLD_SPOT8 = "research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8"
WHEELHOUSE = "/home/hatch/workspace/td_nl_wheelhouse_20261016"

PIN_DRIVER = "5fed45242eb5ec465266c4d4c4258485f01a8c5bfdfdda2fb81295d3cf6d9c00"

# --- -08: the single shared credential-helper resolver. Loaded from
# this package's own directory by exact path; both this gate and the
# armed driver consume ONLY its verified handle (see
# credential_resolver.py). No sys.path route to the helper exists here.
_rspec = importlib.util.spec_from_file_location(
    "qf_credential_resolver",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "credential_resolver.py"))
RESOLVER = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(RESOLVER)
PIN_MANIFEST = "71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db"
PIN_SUPPLEMENT = "3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86"
PIN_COLLECTOR = "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c"
PIN_PILOT_ACQUIRE = "acf39bbd98f7174a4205019e754fc714ca420b4a7df43c815ea158a6fad67c59"
PIN_RATE_LIMITER = "06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64"
PIN_MECHANISM = "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58"
PIN_LOCK = "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068"
PIN_ADAPTER = "ec877a04d12e6b0c69378dba245be07ab60279a15c9eb78cc50e8b0c705e166b"
PIN_PREREQ = "038ccaf33547d6dae1f12ace073726300d92333184a0ba5de0dbab94cc0b5349"
PIN_CALENDAR_PROOF = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"
EXPECTED_RUN_ID = "TD-FRESH-FM-20261016-03-R1"
EXPECTED_ADJUDICATION = "FRESH_LIVE_DRIVER_INTEGRATION_PASS_OFFLINE_LIVE_HOLD_DISPATCH_GATE"
EXPECTED_AUTHORITY_BASIS = "MIKE_STANDING_CAPPED_FREE_SCREEN_AUTHORITY_2026-10-14"
CREDIT_CEILING = 51
DAY_CAP = 800
MINUTE_CAP = 8


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def H(b):
    return hashlib.sha256(b).hexdigest()


def iso(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(ts):
    return iso(ts)[:10]


class GateRefusal(Exception):
    """Raised before any file access when live mode is handed a test seam."""


class SystemUtcClock:
    """The live clock: actual UTC system time. advance() sleeps (the
    Runner's pacing waits); it can never be set by a caller."""

    def now(self):
        return time.time()

    def advance(self, seconds):
        if seconds > 0:
            time.sleep(seconds)


def make_dispatch_token(run_id, manifest_digest, evidence_digest, ledger_path, window):
    return H(canon({
        "dispatch": TASK, "run_id": run_id, "manifest_digest": manifest_digest,
        "evidence_digest": evidence_digest, "ledger_path": ledger_path,
        "window_start": window["start"], "window_end": window["end"],
    }))


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _git_blob(repo, commit, path):
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (commit, path)],
                       capture_output=True, timeout=30)
    if r.returncode != 0:
        return None
    return r.stdout


_DERIVE_MEMO = {}


def derive_calendar(wheelhouse, mechanism_path):
    """Re-derive the XNYS closed expectation in the pinned environment:
    the 11 hash-verified wheels are extracted to a throwaway temp dir
    (no pip, no site-packages mutation, nothing persisted) and the
    pinned mechanism's xnys_schedule is executed there for the proof
    date and a known-open control date. Memoized per wheelhouse
    manifest hash within this process."""
    manifest_bytes = _read(os.path.join(wheelhouse, "SHA256_MANIFEST.txt"))
    import re
    import shutil
    import tempfile
    import zipfile
    wheels = {}
    for line in manifest_bytes.decode().splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+(.+)$", line.strip())
        if m:
            wheels[os.path.basename(m.group(2))] = m.group(1)
    if len(wheels) != 11:
        raise GateRefusal("WHEELHOUSE_MANIFEST_SHAPE")
    # verify every wheel against the manifest BEFORE any use, and key
    # the memo on the actual wheel bytes + mechanism bytes, so a
    # tampered wheelhouse can never be served a cached good derivation.
    wheel_bytes = {}
    for name, pin in sorted(wheels.items()):
        data = _read(os.path.join(wheelhouse, "wheels", name))
        if H(data) != pin:
            raise GateRefusal("WHEEL_HASH_MISMATCH")
        wheel_bytes[name] = data
    key = H(manifest_bytes + H(_read(mechanism_path)).encode()
            + "".join(H(wheel_bytes[n]) for n in sorted(wheel_bytes)).encode())
    if key in _DERIVE_MEMO:
        return _DERIVE_MEMO[key]
    tmp = tempfile.mkdtemp(prefix="qf_nl_env_")
    try:
        for name in sorted(wheel_bytes):
            with zipfile.ZipFile(__import__("io").BytesIO(wheel_bytes[name])) as z:
                z.extractall(tmp)
        script = (
            "import importlib.util, json, sys\n"
            "spec = importlib.util.spec_from_file_location('validate_input', sys.argv[1])\n"
            "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
            "import pandas as pd\n"
            "from importlib.metadata import version\n"
            "out = {'closed_2026_07_03': mod.xnys_schedule(pd.Timestamp('2026-07-03')) is None,\n"
            "       'closed_2026_07_02': mod.xnys_schedule(pd.Timestamp('2026-07-02')) is None,\n"
            "       'pmc_version': version('pandas_market_calendars'),\n"
            "       'pandas_version': version('pandas')}\n"
            "print(json.dumps(out, sort_keys=True))\n"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = tmp
        r = subprocess.run([sys.executable, "-c", script, mechanism_path],
                           capture_output=True, timeout=120, env=env)
        if r.returncode != 0:
            raise GateRefusal("CALENDAR_DERIVATION_FAILED")
        out = json.loads(r.stdout.decode().strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _DERIVE_MEMO[key] = out
    return out


class GateContext:
    def __init__(self, evidence_bytes, clock, test_mode, paths_override, pinned_env_dir):
        self.test_mode = test_mode
        self.clock = clock
        self.now = clock.now()
        self.ov = paths_override or {}
        try:
            self.evidence = json.loads(evidence_bytes)
        except Exception:
            raise GateRefusal("EVIDENCE_UNPARSEABLE")
        if canon(self.evidence) != evidence_bytes:
            raise GateRefusal("EVIDENCE_NOT_CANONICAL")
        self.evidence_digest = H(evidence_bytes)
        self.packet = self.evidence.get("packet") or {}
        # recomputed pins (read-only)
        self.b_driver = self._bytes("driver", os.path.join(REPO, P_DRIVER))
        self.b_manifest = self._bytes("manifest", os.path.join(REPO, P_MANIFEST))
        self.b_supplement = self._bytes("supplement", os.path.join(REPO, P_SUPPLEMENT))
        self.driver = None
        if self.b_driver is not None and H(self.b_driver) == PIN_DRIVER:
            spec = importlib.util.spec_from_file_location("qf_live_driver", self._path("driver", os.path.join(REPO, P_DRIVER)))
            self.driver = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.driver)
            if "driver_module" in self.ov:
                # test-only seam (paths_override is refused in live mode):
                # a spy-instrumented copy of the pinned module, used by
                # the offline suite to prove construction ordering.
                self.driver = self.ov["driver_module"]
        try:
            self.manifest = json.loads(self.b_manifest) if self.b_manifest else None
        except Exception:
            self.manifest = None
        self.lease_fd = None
        self.lease_path = None
        self.lease_binding = None
        self.helper_handle = None

    def _path(self, key, default):
        return self.ov.get(key, default)

    def _bytes(self, key, default):
        try:
            return _read(self._path(key, default))
        except Exception:
            return None

    def gate(self, results, gid, name, result, code, evidence=None):
        results.append({"gate": gid, "name": name, "result": result,
                        "code": code, "evidence": evidence})


def lease_path_for(state_dir):
    """The owner-lease artifact for a namespace identity: a sibling file
    of the namespace directory (never inside it, so the pinned Runner's
    namespace census never sees it). Deterministic in the namespace
    absolute path, so every gate flow for the same namespace contends
    on the same file."""
    return os.path.abspath(state_dir) + ".dispatch_lease"


def acquire_lease(state_dir, run_id, manifest_digest, evidence_digest):
    """Nonblocking exclusive flock on the lease artifact. Returns
    (fd, path, binding) on success; (None, path, code) on contention or
    a foreign binding. Creates ONLY the lease artifact itself; the
    namespace and the ledger are never touched here."""
    import fcntl
    path = lease_path_for(state_dir)
    binding = {"lease": TASK + "/" + REVISION, "run_id": run_id,
               "manifest_digest": manifest_digest,
               "evidence_digest": evidence_digest,
               "namespace": os.path.abspath(state_dir)}
    fd = os.open(path, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None, path, "OWNER_LEASE_HELD"
    try:
        existing = b""
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            existing += chunk
        if existing:
            try:
                old = json.loads(existing)
            except Exception:
                old = None
            core = {k: old.get(k) for k in ("run_id", "manifest_digest", "namespace")} \
                if isinstance(old, dict) else None
            want = {"run_id": run_id, "manifest_digest": manifest_digest,
                    "namespace": os.path.abspath(state_dir)}
            if core != want:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                return None, path, "OWNER_LEASE_BINDING_MISMATCH"
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, canon(binding))
        os.fsync(fd)
    except Exception:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)
        raise
    return fd, path, binding


def release_lease(ctx):
    if ctx.lease_fd is not None:
        import fcntl
        try:
            fcntl.flock(ctx.lease_fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(ctx.lease_fd)
        except Exception:
            pass
        ctx.lease_fd = None


def _ns_probe(ns):
    """Compact re-probe of the gate-8 invariant (clean namespace, zero
    prior attempts, own identity only), used again after the lease is
    held, immediately before the PASS receipt is written."""
    old = os.path.join(REPO, P_OLD_SPOT8)
    if os.path.abspath(ns) == os.path.abspath(old):
        return "NAMESPACE_IS_OLD_SPOT8"
    if not os.path.exists(ns):
        return "NAMESPACE_NEW"
    entries = set(os.listdir(ns))
    known = {"manifest_binding.json", "owner.lock", "lifecycle.jsonl",
             "pilot_state.json", "receipts"}
    if not entries.issubset(known):
        return "NAMESPACE_FOREIGN_FILES"
    if os.path.exists(os.path.join(ns, "pilot_state.json")):
        st = json.loads(_read(os.path.join(ns, "pilot_state.json")))
        if len(st.get("requests") or {}) not in (0,):
            return "PRIOR_ATTEMPTS_PRESENT"
    if "manifest_binding.json" in entries:
        binding = json.loads(_read(os.path.join(ns, "manifest_binding.json")))
        if binding.get("run_id") != EXPECTED_RUN_ID \
                or binding.get("manifest_digest") != PIN_MANIFEST:
            return "NAMESPACE_BOUND_TO_OTHER_IDENTITY"
    return "NAMESPACE_OWN_STATE_ZERO_ATTEMPTS"


def preflight_credential_helper(ctx):
    """Gate 9 (r3, -08): resolve the credential helper through the ONE
    shared origin-verified resolver (credential_resolver) and verify
    origin + pinned hash + callable + allowed-host binding WITHOUT
    invoking it, without resolving/reading/logging any credential
    material, and without network. Live route: the exact sanctioned
    platform path + pinned SHA-256. Test seam (paths_override is
    refused wholesale in live mode): 'helper_path' + 'helper_sha256'
    relocate the exact path AND its pin together; a path relocation
    without its seam pin refuses as an origin mismatch - an unpinned
    path is never trusted. The legacy r2 'helper_module' object seam
    no longer exists. Returns (ok, code); on success the verified
    handle is stored on ctx for the pre-arm reverify + driver handoff."""
    ov = ctx.ov
    if "helper_path" in ov and "helper_sha256" not in ov:
        return False, "CREDENTIAL_HELPER_ORIGIN_MISMATCH"
    path = ov.get("helper_path", RESOLVER.SANCTIONED_PATH)
    sha = ov.get("helper_sha256", RESOLVER.PIN_SHA256)
    try:
        handle = RESOLVER.resolve(path, sha)
    except RESOLVER.HelperRefusal as e:
        return False, e.code
    ctx.helper_handle = handle
    return True, "HELPER_ORIGIN_VERIFIED"


def evaluate_gates(ctx):
    """All 12 checklist gates, evaluated independently (no short-circuit),
    read-only. Returns the per-gate verdict list."""
    g = []
    ev, pk, now = ctx.evidence, ctx.packet, ctx.now
    man = ctx.manifest or {}

    # Gate 1 - adjudicated execution packet: present, current, internally
    # consistent with the pinned identity and this evaluation instant.
    try:
        win = pk["dispatch_window"]
        ok = (pk.get("run_id") == EXPECTED_RUN_ID == man.get("run_id")
              and pk.get("manifest_digest") == PIN_MANIFEST
              and pk.get("supplement_sha256") == PIN_SUPPLEMENT
              and pk.get("entrypoint_sha256") == PIN_DRIVER
              and pk.get("credit_ceiling") == CREDIT_CEILING
              and man.get("budget", {}).get("max_credits") == CREDIT_CEILING
              and isinstance(pk.get("state_dir"), str) and pk.get("state_dir")
              and isinstance(pk.get("ledger_path"), str) and pk.get("ledger_path")
              and isinstance(pk.get("receipt_path"), str) and pk.get("receipt_path")
              and isinstance(pk.get("packet_id"), str) and pk.get("packet_id"))
        if not ok:
            ctx.gate(g, 1, "adjudicated_execution_packet", "FAIL", "PACKET_INCONSISTENT")
        elif not (win["start"] <= now <= win["end"]):
            ctx.gate(g, 1, "adjudicated_execution_packet", "FAIL", "DISPATCH_WINDOW_NOT_CURRENT",
                     H(canon(win))[:12])
        else:
            ctx.gate(g, 1, "adjudicated_execution_packet", "PASS", "PACKET_BOUND",
                     H(canon(pk))[:12])
    except Exception:
        ctx.gate(g, 1, "adjudicated_execution_packet", "UNKNOWN", "PACKET_MISSING_FIELDS")

    # Gate 2 - authority basis recorded (standing authority; not a request).
    au = ev.get("authority") or {}
    if au.get("basis") == EXPECTED_AUTHORITY_BASIS and au.get("re_requested") is False \
            and au.get("task_ceiling_credits") == CREDIT_CEILING and au.get("spend_usd") == 0:
        ctx.gate(g, 2, "authority_recorded", "PASS", "AUTHORITY_STANDING", H(canon(au))[:12])
    elif not au:
        ctx.gate(g, 2, "authority_recorded", "UNKNOWN", "AUTHORITY_MISSING")
    else:
        ctx.gate(g, 2, "authority_recorded", "FAIL", "AUTHORITY_INCONSISTENT")

    # Gate 3 - account plan/status/capacity from timestamped evidence.
    ac = ev.get("account") or {}
    try:
        age = now - ac["observed_at"]
        max_age = pk.get("account_evidence_max_age_s", 3600)
        if ac.get("plan") != "Basic":
            ctx.gate(g, 3, "account_plan_status_capacity", "FAIL", "ACCOUNT_PLAN_NOT_BASIC")
        elif ac.get("standing") != "good":
            ctx.gate(g, 3, "account_plan_status_capacity", "FAIL", "ACCOUNT_NOT_GOOD_STANDING")
        elif age < -60 or age > max_age:
            ctx.gate(g, 3, "account_plan_status_capacity", "FAIL", "ACCOUNT_EVIDENCE_STALE")
        elif ac.get("remaining_daily_credits", 0) < CREDIT_CEILING:
            ctx.gate(g, 3, "account_plan_status_capacity", "FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT")
        elif ac.get("minute_cap") != MINUTE_CAP:
            ctx.gate(g, 3, "account_plan_status_capacity", "FAIL", "ACCOUNT_MINUTE_CAP_MISMATCH")
        else:
            ctx.gate(g, 3, "account_plan_status_capacity", "PASS", "ACCOUNT_VERIFIED",
                     H(canon(ac))[:12])
    except Exception:
        ctx.gate(g, 3, "account_plan_status_capacity", "UNKNOWN", "ACCOUNT_EVIDENCE_MISSING")

    # Gate 4 - shared limiter state at the exact packet path, outside the
    # namespace; read-only probe; the day's prior reservations + ceiling
    # must fit the 800/day cap; corrupt/absent never resets.
    try:
        ledger_path = os.path.abspath(pk["ledger_path"])
        ns_abs = os.path.abspath(pk["state_dir"])
        if ledger_path == ns_abs or ledger_path.startswith(ns_abs + os.sep):
            ctx.gate(g, 4, "shared_limiter_state", "FAIL", "LEDGER_INSIDE_NAMESPACE")
        elif not os.path.exists(ledger_path):
            ctx.gate(g, 4, "shared_limiter_state", "UNKNOWN", "LEDGER_ABSENT")
        else:
            raw = _read(ledger_path)
            ledger = json.loads(raw)
            assert isinstance(ledger.get("reservations"), list)
            for r in ledger["reservations"]:
                assert isinstance(r["rid"], str) and isinstance(r["ts"], (int, float)) \
                    and isinstance(r["day"], str) and isinstance(r["weight"], (int, float))
            used = sum(r["weight"] for r in ledger["reservations"] if r["day"] == day_of(now))
            if used + CREDIT_CEILING > DAY_CAP:
                ctx.gate(g, 4, "shared_limiter_state", "FAIL", "DAY_CAPACITY_INSUFFICIENT",
                         H(raw)[:12])
            else:
                ctx.gate(g, 4, "shared_limiter_state", "PASS", "LEDGER_STATE_VERIFIED",
                         H(raw)[:12])
    except GateRefusal:
        raise
    except Exception:
        ctx.gate(g, 4, "shared_limiter_state", "FAIL", "LEDGER_CORRUPT_OR_UNREADABLE")

    # Gate 5 - environment reproduction: lock + mechanism pins recomputed,
    # all 11 wheelhouse wheels hash-verified, evidence env record bound to
    # the recomputed lock bytes.
    try:
        b_lock = ctx._bytes("lock", os.path.join(REPO, P_LOCK))
        b_mech = ctx._bytes("mechanism", os.path.join(REPO, P_MECHANISM))
        wh = ctx._path("wheelhouse", WHEELHOUSE)
        manifest_bytes = _read(os.path.join(wh, "SHA256_MANIFEST.txt"))
        import re
        wheels = [l for l in manifest_bytes.decode().splitlines()
                  if re.match(r"^[0-9a-f]{64}\s+", l.strip())]
        wheels_ok = len(wheels) == 11 and all(
            H(_read(os.path.join(wh, "wheels", os.path.basename(l.split(None, 1)[1]))))
            == l.split(None, 1)[0] for l in wheels)
        env_rec = ev.get("environment") or {}
        lock_lines = (b_lock or b"").decode().splitlines()
        pmc_line = [l for l in lock_lines if l.startswith("pandas_market_calendars==")]
        if b_lock is None or H(b_lock) != PIN_LOCK:
            ctx.gate(g, 5, "environment_reproduction", "FAIL", "ENV_LOCK_PIN_MISMATCH")
        elif b_mech is None or H(b_mech) != PIN_MECHANISM:
            ctx.gate(g, 5, "environment_reproduction", "FAIL", "ENV_MECHANISM_PIN_MISMATCH")
        elif not wheels_ok:
            ctx.gate(g, 5, "environment_reproduction", "FAIL", "WHEELHOUSE_HASH_MISMATCH")
        elif env_rec.get("freeze_sha256") != H(b_lock):
            ctx.gate(g, 5, "environment_reproduction", "FAIL", "ENV_FREEZE_RECORD_MISMATCH")
        elif env_rec.get("interpreter") != "CPython 3.12.3" \
                or pmc_line != ["pandas_market_calendars==4.5.1"] \
                or env_rec.get("pandas_market_calendars") != "4.5.1":
            ctx.gate(g, 5, "environment_reproduction", "FAIL", "ENV_VERSION_MISMATCH")
        else:
            ctx.gate(g, 5, "environment_reproduction", "PASS", "ENV_PINS_VERIFIED",
                     PIN_LOCK[:12])
    except GateRefusal:
        raise
    except Exception:
        ctx.gate(g, 5, "environment_reproduction", "UNKNOWN", "ENV_EVIDENCE_UNREADABLE")

    # Gate 6 - manifest / supplement / source hashes recomputed.
    try:
        checks = {
            "manifest": ctx.b_manifest is not None and H(ctx.b_manifest) == PIN_MANIFEST,
            "supplement": ctx.b_supplement is not None and H(ctx.b_supplement) == PIN_SUPPLEMENT,
            "driver": ctx.b_driver is not None and H(ctx.b_driver) == PIN_DRIVER,
            "pilot_acquire": (ctx._bytes("pilot_acquire", os.path.join(REPO, P_PILOT_ACQUIRE)) or b"") != b""
                and H(ctx._bytes("pilot_acquire", os.path.join(REPO, P_PILOT_ACQUIRE))) == PIN_PILOT_ACQUIRE,
            "rate_limiter": (ctx._bytes("rate_limiter", os.path.join(REPO, P_RATE_LIMITER)) or b"") != b""
                and H(ctx._bytes("rate_limiter", os.path.join(REPO, P_RATE_LIMITER))) == PIN_RATE_LIMITER,
            "prerequisites": (ctx._bytes("prereq", os.path.join(REPO, P_PREREQ)) or b"") != b""
                and H(ctx._bytes("prereq", os.path.join(REPO, P_PREREQ))) == PIN_PREREQ,
        }
        blob = _git_blob(REPO, *P_COLLECTOR_GIT)
        checks["collector"] = blob is not None and H(blob) == PIN_COLLECTOR
        bad = [k for k, v in checks.items() if not v]
        if bad:
            ctx.gate(g, 6, "source_hashes", "FAIL", "PIN_MISMATCH:" + ",".join(sorted(bad)))
        else:
            ctx.gate(g, 6, "source_hashes", "PASS", "ALL_PINS_RECOMPUTED", PIN_MANIFEST[:12])
    except Exception:
        ctx.gate(g, 6, "source_hashes", "UNKNOWN", "PIN_RECOMPUTE_FAILED")

    # Gate 7 - calendar proof re-derived in the pinned environment and
    # matched against the supplement's pinned proof record.
    try:
        supp = json.loads(ctx.b_supplement) if ctx.b_supplement else {}
        proof = (supp.get("calendar_proofs") or {}).get(PIN_CALENDAR_PROOF)
        derived = derive_calendar(ctx._path("wheelhouse", WHEELHOUSE),
                                  ctx._path("mechanism", os.path.join(REPO, P_MECHANISM)))
        if proof is None or H(canon(proof)) != PIN_CALENDAR_PROOF:
            ctx.gate(g, 7, "calendar_rederivation", "FAIL", "PINNED_PROOF_MISSING_OR_MUTATED")
        elif derived["closed_2026_07_03"] is not True or derived["closed_2026_07_02"] is not False:
            ctx.gate(g, 7, "calendar_rederivation", "FAIL", "DERIVATION_DISAGREES")
        elif derived["pmc_version"] != "4.5.1" or proof.get("closed") is not True \
                or proof.get("date") != "2026-07-03" or proof.get("library_version") != "4.5.1" \
                or proof.get("mechanism_module_sha256") != PIN_MECHANISM:
            ctx.gate(g, 7, "calendar_rederivation", "FAIL", "PROOF_FACTS_MISMATCH")
        else:
            ctx.gate(g, 7, "calendar_rederivation", "PASS", "CLOSED_DATE_REDERIVED",
                     PIN_CALENDAR_PROOF[:12])
    except GateRefusal as e:
        ctx.gate(g, 7, "calendar_rederivation", "FAIL", "DERIVATION_" + str(e))
    except Exception:
        ctx.gate(g, 7, "calendar_rederivation", "UNKNOWN", "DERIVATION_UNAVAILABLE")

    # Gate 8 - clean namespace, zero prior attempts, sole owner (probe is
    # read-only: existence + contents + recorded attempts; the Runner's
    # own flock arbitrates a live second owner at construction, which
    # never happens unless every gate passes).
    try:
        ns = pk["state_dir"]
        old = os.path.join(REPO, P_OLD_SPOT8)
        if os.path.abspath(ns) == os.path.abspath(old):
            ctx.gate(g, 8, "clean_namespace_zero_attempts", "FAIL", "NAMESPACE_IS_OLD_SPOT8")
        elif not os.path.exists(ns):
            ctx.gate(g, 8, "clean_namespace_zero_attempts", "PASS", "NAMESPACE_NEW")
        else:
            entries = set(os.listdir(ns))
            known = {"manifest_binding.json", "owner.lock", "lifecycle.jsonl",
                     "pilot_state.json", "receipts"}
            attempts = None
            if os.path.exists(os.path.join(ns, "pilot_state.json")):
                st = json.loads(_read(os.path.join(ns, "pilot_state.json")))
                attempts = len(st.get("requests") or {})
            if not entries.issubset(known):
                ctx.gate(g, 8, "clean_namespace_zero_attempts", "FAIL", "NAMESPACE_FOREIGN_FILES")
            elif attempts not in (None, 0):
                ctx.gate(g, 8, "clean_namespace_zero_attempts", "FAIL", "PRIOR_ATTEMPTS_PRESENT")
            elif "manifest_binding.json" in entries:
                binding = json.loads(_read(os.path.join(ns, "manifest_binding.json")))
                if binding.get("run_id") != EXPECTED_RUN_ID \
                        or binding.get("manifest_digest") != PIN_MANIFEST:
                    ctx.gate(g, 8, "clean_namespace_zero_attempts", "FAIL",
                             "NAMESPACE_BOUND_TO_OTHER_IDENTITY")
                else:
                    ctx.gate(g, 8, "clean_namespace_zero_attempts", "PASS",
                             "NAMESPACE_OWN_STATE_ZERO_ATTEMPTS")
            else:
                ctx.gate(g, 8, "clean_namespace_zero_attempts", "PASS",
                         "NAMESPACE_OWN_STATE_ZERO_ATTEMPTS")
    except Exception:
        ctx.gate(g, 8, "clean_namespace_zero_attempts", "UNKNOWN", "NAMESPACE_UNREADABLE")

    # Gate 9 - credential / proxy boundary: binding constants recomputed
    # from the pinned driver module + evidence declaration consistent.
    # (Helper presence in the live platform process is attested by the
    # evidence record; the sandbox interpreter cannot import it, which
    # is recorded in the memo - the binding itself is fully recomputed.)
    try:
        cr = ev.get("credential") or {}
        D = ctx.driver
        if D is None:
            ctx.gate(g, 9, "credential_proxy_boundary", "UNKNOWN", "DRIVER_NOT_LOADED")
        elif D.LIVE_ENDPOINT != "https://api.twelvedata.com/time_series" \
                or D.LIVE_CREDENTIAL_REF != "custom.twelvedata" \
                or D.LIVE_ALLOWED_HOSTS != ["api.twelvedata.com"]:
            ctx.gate(g, 9, "credential_proxy_boundary", "FAIL", "TRANSPORT_BINDING_MISMATCH")
        elif cr.get("ref") != "custom.twelvedata" \
                or cr.get("helper") != "dynamic_credentials.url_with_surrogate_query_param" \
                or cr.get("allowed_hosts") != ["api.twelvedata.com"] \
                or cr.get("material_read_by_entrypoint") is not False:
            ctx.gate(g, 9, "credential_proxy_boundary", "FAIL", "CREDENTIAL_EVIDENCE_INCONSISTENT")
        elif b"apikey=" in (ctx.b_driver or b""):
            ctx.gate(g, 9, "credential_proxy_boundary", "FAIL", "KEY_MATERIAL_IN_DRIVER_SOURCE")
        else:
            ok_h, code_h = preflight_credential_helper(ctx)
            if ok_h:
                ctx.gate(g, 9, "credential_proxy_boundary", "PASS",
                         "CREDENTIAL_BOUNDARY_AND_HELPER_VERIFIED", PIN_PILOT_ACQUIRE[:12])
            else:
                ctx.gate(g, 9, "credential_proxy_boundary", "FAIL", code_h)
    except Exception:
        ctx.gate(g, 9, "credential_proxy_boundary", "UNKNOWN", "CREDENTIAL_CHECK_FAILED")

    # Gate 10 - adapter contract: pin recomputed + the driver's build_url
    # emits the contract's fixed parameter order (pre-apikey prefix).
    try:
        b_adapter = ctx._bytes("adapter", os.path.join(REPO, P_ADAPTER))
        if b_adapter is None or H(b_adapter) != PIN_ADAPTER:
            ctx.gate(g, 10, "adapter_contract", "FAIL", "ADAPTER_PIN_MISMATCH")
        elif ctx.driver is None:
            ctx.gate(g, 10, "adapter_contract", "UNKNOWN", "DRIVER_NOT_LOADED")
        else:
            contract = json.loads(b_adapter)
            order = contract["request_construction"]["parameters_fixed_order"]
            req0 = man["requests"][0]
            url = ctx.driver.build_url(req0)
            keys = [p.split("=", 1)[0] for p in url.split("?", 1)[1].split("&")]
            if keys != order[:len(keys)] or not url.startswith(ctx.driver.LIVE_ENDPOINT + "?") \
                    or contract["request_construction"].get("method") != "GET":
                ctx.gate(g, 10, "adapter_contract", "FAIL", "URL_ORDER_MISMATCH")
            else:
                ctx.gate(g, 10, "adapter_contract", "PASS", "ADAPTER_CONTRACT_BOUND",
                         PIN_ADAPTER[:12])
    except Exception:
        ctx.gate(g, 10, "adapter_contract", "UNKNOWN", "ADAPTER_CHECK_FAILED")

    # Gate 11 - stop rules armed: the pinned driver module (hash-verified
    # in gate 6, loaded from the pinned path) is the only Runner the
    # wrapper will construct; evidence declaration must match.
    sr = ev.get("stop_rules") or {}
    if ctx.driver is None:
        ctx.gate(g, 11, "stop_rules_armed", "UNKNOWN", "DRIVER_NOT_LOADED")
    elif sr.get("armed") is True and sr.get("first_error_stops_batch") is True \
            and sr.get("ambiguous_never_redispatched") is True \
            and sr.get("unknown_credit_hold") is True:
        ctx.gate(g, 11, "stop_rules_armed", "PASS", "STOP_RULES_BOUND", PIN_DRIVER[:12])
    elif not sr:
        ctx.gate(g, 11, "stop_rules_armed", "UNKNOWN", "STOP_RULES_MISSING")
    else:
        ctx.gate(g, 11, "stop_rules_armed", "FAIL", "STOP_RULES_NOT_ARMED")

    # Gate 12 - retention limits acknowledged.
    rt = ev.get("retention") or {}
    if rt.get("acknowledged") is True and rt.get("scope") == "private_screen_evidence_only" \
            and rt.get("indefinite_retention_claimed") is False \
            and rt.get("redistribution") is False:
        ctx.gate(g, 12, "retention_acknowledged", "PASS", "RETENTION_BOUND", H(canon(rt))[:12])
    elif not rt:
        ctx.gate(g, 12, "retention_acknowledged", "UNKNOWN", "RETENTION_MISSING")
    else:
        ctx.gate(g, 12, "retention_acknowledged", "FAIL", "RETENTION_NOT_ACKNOWLEDGED")

    return g


def _write_receipt(receipt, receipt_path):
    """Durable exclusive-create write. Returns True if written, False if
    a receipt already exists for this path (replay guard)."""
    parent = os.path.dirname(os.path.abspath(receipt_path))
    os.makedirs(parent, exist_ok=True)
    try:
        fd = os.open(receipt_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "wb") as f:
        f.write(canon(receipt))
        f.flush()
        os.fsync(f.fileno())
    return True


def dispatch(evidence_bytes, dispatch_token=None, mode="live",
             clock=None, transport_factory=None, paths_override=None,
             pinned_env_dir=None):
    """The wrapper's single entry. No account_mode parameter exists:
    the mode is derived from the verified receipt. Test seams (clock,
    transport_factory, paths_override, pinned_env_dir) are accepted
    only with mode='test'; in live mode any seam refuses BEFORE any
    file access."""
    if mode == "live":
        if clock is not None or transport_factory is not None \
                or paths_override or pinned_env_dir is not None:
            raise GateRefusal("TEST_SEAM_IN_LIVE_MODE")
        clock = SystemUtcClock()
        test_mode = False
    elif mode == "test":
        test_mode = True
        if clock is None:
            raise GateRefusal("TEST_MODE_REQUIRES_INJECTED_CLOCK")
    else:
        raise GateRefusal("UNKNOWN_MODE")

    ctx = GateContext(evidence_bytes, clock, test_mode, paths_override, pinned_env_dir)
    gates = evaluate_gates(ctx)
    all_pass = all(x["result"] == "PASS" for x in gates)
    pk = ctx.packet
    win = pk.get("dispatch_window") or {}

    # --- r2 phase 2: sole ownership PROVEN before PASS is written or
    # any transport exists. The nonblocking owner lease for the exact
    # namespace identity is acquired now and held continuously through
    # receipt, transport construction and the Runner's whole lifetime
    # (the pinned Runner's own owner flock is acquired inside that
    # window, so there is no unlocked interval). Contention or a
    # foreign lease binding amends gate 8 to FAIL on the receipt. ---
    lease_held = False
    if all_pass:
        fd, lpath, lres = acquire_lease(pk["state_dir"], pk.get("run_id"),
                                        pk.get("manifest_digest"),
                                        ctx.evidence_digest)
        if fd is None:
            for x in gates:
                if x["gate"] == 8:
                    x["result"] = "FAIL"
                    x["code"] = lres
            all_pass = False
        else:
            ctx.lease_fd, ctx.lease_path, ctx.lease_binding = fd, lpath, lres
            lease_held = True
            try:
                probe = _ns_probe(pk["state_dir"])
            except Exception:
                probe = "NAMESPACE_UNREADABLE"
            if probe not in ("NAMESPACE_NEW", "NAMESPACE_OWN_STATE_ZERO_ATTEMPTS"):
                for x in gates:
                    if x["gate"] == 8:
                        x["result"] = "FAIL"
                        x["code"] = probe
                all_pass = False

    # --- -08 phase 2b: the verified helper must STILL be the verified
    # helper at the moment of arming. Re-hash the exact file (a post-gate
    # swap/tamper amends gate 9 to FAIL) and refuse if a foreign module
    # already occupies the helper's import name (the pinned driver's
    # by-name import must never land on a shadow). Both checks run
    # before the receipt is written and before any construction. ---
    if all_pass and ctx.helper_handle is not None:
        try:
            ctx.helper_handle.reverify()
            if dispatch_token is not None:
                # the slot matters only when the driver's by-name
                # import will actually run (the arming path)
                RESOLVER.check_handoff_slot(ctx.helper_handle)
        except RESOLVER.HelperRefusal as e:
            for x in gates:
                if x["gate"] == 9:
                    x["result"] = "FAIL"
                    x["code"] = e.code
            all_pass = False

    token_check = "not_requested"
    if all_pass and dispatch_token is not None:
        expected = make_dispatch_token(pk.get("run_id"), pk.get("manifest_digest"),
                                       ctx.evidence_digest, pk.get("ledger_path"), win)
        token_check = "valid" if dispatch_token == expected else "invalid"

    decision = "HOLD"
    if all_pass and dispatch_token is None:
        decision = "PASS_DRY_RUN"
    elif all_pass and token_check == "valid":
        decision = "PASS"

    receipt = {
        "gate_revision": REVISION,
        "owner_lease": {"acquired": lease_held,
                        "artifact": os.path.basename(ctx.lease_path) if lease_held else None,
                        "held_until": "after_runner_close" if lease_held else None},
        "receipt_id": TASK + "/RECEIPT",
        "run_id": pk.get("run_id"),
        "manifest_digest": pk.get("manifest_digest"),
        "evidence_digest": ctx.evidence_digest,
        "evaluated_at": iso(ctx.now),
        "clock_mode": "injected_test" if test_mode else "system_utc",
        "account_mode_derived": "known" if all_pass else None,
        "token_check": token_check,
        "gates": gates,
        "decision": decision,
        "armed": False,
    }
    receipt_path = pk.get("receipt_path")
    written = False
    if isinstance(receipt_path, str) and receipt_path:
        written = _write_receipt(receipt, receipt_path)
        if not written:
            # a receipt already exists for this evidence: replay guard
            receipt["decision"] = "HOLD"
            receipt["replay_guard"] = "RECEIPT_ALREADY_ISSUED"
            release_lease(ctx)
            return {"receipt": receipt, "receipt_written": False,
                    "outcome": None, "transport_constructed": False,
                    "lease_acquired": lease_held}

    result = {"receipt": receipt, "receipt_written": written,
              "outcome": None, "transport_constructed": False,
              "lease_acquired": lease_held}
    if decision != "PASS":
        release_lease(ctx)
        return result

    # --- the only arming path: PASS receipt durably written, token
    # verified; construct transport via the factory, derive the Runner
    # configuration from the receipt, never from the caller. ---
    factory = transport_factory
    if factory is None:
        D = ctx.driver
        factory = lambda: D.LiveHttpsTransport(armed=True)  # noqa: E731
    # --- -08 handoff: install the gate-verified module under the
    # helper's import name, so the armed driver's by-name import can
    # only land on the verified origin (slot checked above). ---
    if ctx.helper_handle is not None:
        RESOLVER.install_handoff(ctx.helper_handle)
    try:
        transport = factory()
        result["transport_constructed"] = True
        runner = ctx.driver.Runner(
            pk["state_dir"], ctx.b_manifest, ctx.b_supplement, transport, clock,
            shared_ledger_path=pk["ledger_path"],
            account_mode=receipt["account_mode_derived"])
    except BaseException:
        release_lease(ctx)
        raise
    try:
        result["outcome"] = runner.run()
    finally:
        runner.close()
        release_lease(ctx)
    return result


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="dispatch_gate")
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--dispatch", default=None,
                    help="dispatch token bound to run/manifest/evidence/ledger/window")
    args = ap.parse_args(argv)
    evidence_bytes = _read(args.evidence)
    res = dispatch(evidence_bytes, dispatch_token=args.dispatch, mode="live")
    print(json.dumps(res["receipt"], indent=1, sort_keys=True))
    if res["outcome"] is not None:
        print(json.dumps({"run_outcome": res["outcome"]["outcome"],
                          "transport_calls": len(res["outcome"]["transport_calls"])},
                         sort_keys=True))
    return 0 if res["receipt"]["decision"] in ("PASS", "PASS_DRY_RUN") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
