#!/usr/bin/env python3
"""Issue #9 OFFLINE enforcement-harness candidate (QF-ISSUE9-OFFLINE-HARNESS-20261014-03 r1).

ISOLATED, OFFLINE-ONLY candidate. Dependency-injected FAKE transport only; this
module imports no HTTP client and the fixture runner patches the socket layer to
raise before any dispatch. It never edits or imports the live bin/or_chat.py or
the production scanner. It exists to prove, synthetically, the runtime
enforcement the route-readiness memo (-02 r1) found missing:

  * empty content is a FAILED call (EMPTY_CONTENT) and STOPS the run;
    reasoning tokens are counted in the ledger but NEVER substituted as content
    (repairs the defect adjudicated against bin/or_chat.py's `content or
    reasoning` substitution, D-R2-02, in this isolated candidate only);
  * immutable per-call ledger, hash-chained, each record fsync-persisted BEFORE
    the run advances; a write-ahead dispatch-intent record makes a crash
    between response and ledger append detectable (orphan) instead of a blind
    resend / double count;
  * frozen protocol v1.0.0 caps enforced per arm-seed: A<=8 / B<=16 calls,
    <=120,000 billed tokens (input+output+reasoning), <=45 min wall, $0.00
    incremental cost, provider free-quota headroom per day;
  * pre-call conservative output reservation, post-call actual-usage check,
    hard stop on any reported overrun;
  * model-pin verification: requested model == response model, provider
    model/version metadata retained; alias swap, silent fallback, or
    unverifiable version metadata stops the run fail-closed;
  * zero retries: a timeout is recorded once and stops the run (no silent
    re-dispatch, no double counting);
  * the -02 preflight guard (D-R2-01 repair) runs BEFORE any dispatch;
  * per-day quota resets ONLY when a verified quota-evidence record is
    supplied at resume; frozen seed order enforced by the run manifest.

A PASS here establishes synthetic harness behavior only. It does NOT authorize
a first live model call or the Arm A/B comparison.
"""
import hashlib
import json
import os

# --- Frozen protocol v1.0.0 constants (prep package, comparison_protocol.json)
TOKEN_CAP_PER_ARM_SEED = 120000
CALL_CAPS = {"A": 8, "B": 16}
WALL_CAP_S = 45 * 60
DAILY_QUOTA_CAP_DEFAULT = 50          # documented free-tier cap (readiness -02)
BUDGET_REF = "ISSUE9-SINGLE-VS-SWARM-PROTOCOL v1.0.0"
SEED_ORDER = ["S1", "S2", "S3"]
ROLES = {"A": {"propose", "self_critique"},
         "B": {"proposer", "skeptic", "feasibility", "synthesis"}}


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class HarnessStop(Exception):
    """Fail-closed stop with a stable reason code."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class SimulatedCrash(Exception):
    """Raised by fixture hooks to simulate process death mid-call."""


class FakeClock:
    """Deterministic injected clock (seconds since run start + ISO day)."""

    def __init__(self, day="2026-11-02", start_s=0.0):
        self.day = day
        self.t = float(start_s)

    def now_s(self):
        return self.t

    def advance(self, s):
        self.t += float(s)

    def iso(self):
        return f"{self.day}T00:00:{int(self.t % 60):02d}Z+{int(self.t // 60)}m"


# --------------------------------------------------------------------------
# Immutable hash-chained ledger (JSONL, fsync before advancing)
# --------------------------------------------------------------------------
class Ledger:
    def __init__(self, path):
        self.path = path
        self.records = []
        self.last_hash = "GENESIS"
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self.records.append(json.loads(line))
            if self.records:
                self.last_hash = self.records[-1]["record_hash"]
        self._fh = open(path, "a", encoding="utf-8")

    def append(self, rtype, **fields):
        rec = {"seq": len(self.records), "type": rtype,
               "prev_hash": self.last_hash}
        rec.update(fields)
        rec["record_hash"] = sha256_text(canonical(rec))
        self._fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())          # persist BEFORE advancing
        self.records.append(rec)
        self.last_hash = rec["record_hash"]
        return rec

    def close(self):
        self._fh.close()

    # -- verification / derived state --------------------------------------
    def verify_chain(self):
        prev = "GENESIS"
        for i, rec in enumerate(self.records):
            if rec.get("seq") != i or rec.get("prev_hash") != prev:
                return False, f"chain break at seq {i}"
            body = {k: v for k, v in rec.items() if k != "record_hash"}
            if sha256_text(canonical(body)) != rec.get("record_hash"):
                return False, f"hash mismatch at seq {i}"
            prev = rec["record_hash"]
        return True, "ok"

    def dangling_intents(self):
        """dispatch_intent records with no call_outcome for the same call."""
        done = {(r["arm"], r["seed"], r["call_index"])
                for r in self.records if r["type"] == "call_outcome"}
        return [r for r in self.records
                if r["type"] == "dispatch_intent"
                and (r["arm"], r["seed"], r["call_index"]) not in done]

    def outcomes(self, arm=None, seed=None):
        return [r for r in self.records if r["type"] == "call_outcome"
                and (arm is None or r["arm"] == arm)
                and (seed is None or r["seed"] == seed)]

    def recorded_calls(self, arm, seed):
        return [r for r in self.outcomes(arm, seed)
                if r["status"] == "RECORDED"]

    def billed_total(self, arm, seed):
        # Every outcome whose usage is known counts toward the cap, including
        # failed calls (the provider really consumed those tokens).
        return sum(r["billed_tokens"] for r in self.outcomes(arm, seed)
                   if "billed_tokens" in r)

    def quota_reset_days(self):
        return {r["day"] for r in self.records if r["type"] == "quota_reset"}

    def quota_used(self, day):
        return sum(1 for r in self.records
                   if r["type"] == "dispatch_intent" and r.get("quota_day") == day)


# --------------------------------------------------------------------------
# Seed-order guard (frozen order S1 -> S2 -> S3 per run manifest)
# --------------------------------------------------------------------------
class SeedOrderGuard:
    def __init__(self):
        self.started = []

    def begin(self, seed):
        expect = SEED_ORDER[len(self.started)] if len(self.started) < 3 else None
        if seed != expect:
            raise HarnessStop("SEED_ORDER_VIOLATION",
                              f"expected {expect}, got {seed}")
        self.started.append(seed)


# --------------------------------------------------------------------------
# Arm-seed runner
# --------------------------------------------------------------------------
class ArmSeedRunner:
    def __init__(self, ledger, clock, transport, *, run_id, arm, seed, pin,
                 price_evidence, registered_prompt_hashes,
                 daily_quota_cap=DAILY_QUOTA_CAP_DEFAULT,
                 crash_after_response=False):
        self.ledger = ledger
        self.clock = clock
        self.transport = transport          # injected fake transport only
        self.run_id = run_id
        self.arm = arm
        self.seed = seed
        self.pin = pin                      # {provider, model, model_version}
        self.price_evidence = price_evidence
        self.registered = set(registered_prompt_hashes)
        self.daily_quota_cap = daily_quota_cap
        self.crash_after_response = crash_after_response
        self.accepted = []                  # accepted candidate contents only
        self.started_s = clock.now_s()
        self.stopped = None                 # (code, detail) once stopped
        prior = [r["quota_day"] for r in ledger.records
                 if r["type"] == "dispatch_intent"]
        self.run_start_day = prior[0] if prior else clock.day

    # -- price evidence -----------------------------------------------------
    def _check_price_evidence(self):
        ev = self.price_evidence or {}
        if not ev.get("evidence_ref"):
            raise HarnessStop("PRICE_EVIDENCE_MISSING", "no evidence_ref")
        pricing = ev.get("catalog_pricing") or {}
        for leg in ("prompt", "completion"):
            val = pricing.get(leg)
            if val is None:
                raise HarnessStop("PRICE_UNKNOWN", f"{leg} price unknown")
            if str(val) not in ("0", "0.0"):
                raise HarnessStop("PRICE_NONZERO", f"{leg} price {val}")
        exp = ev.get("expires_day")
        if exp and self.clock.day > exp:
            raise HarnessStop("PRICE_EVIDENCE_EXPIRED",
                              f"expired {exp}, today {self.clock.day}")
        if ev.get("verified_zero_incremental") is not True:
            raise HarnessStop("COST_NOT_VERIFIED", "zero-incremental unproven")

    # -- main loop ------------------------------------------------------------
    def run(self, calls, start_index=0):
        """calls: [{role, prompt, est_input_tokens, max_output_tokens}].
        Returns (status, code): ('COMPLETE', None) or ('STOPPED', code)."""
        try:
            if self.ledger.dangling_intents():
                raise HarnessStop(
                    "ORPHANED_LEDGER",
                    "a prior dispatch has no outcome; blind resend forbidden")
            self._check_price_evidence()
            for i, call in enumerate(calls):
                self._dispatch(start_index + i, call)
        except HarnessStop as stop:
            self.stopped = (stop.code, stop.detail)
            self.ledger.append("run_stop", run_id=self.run_id, arm=self.arm,
                               seed=self.seed, code=stop.code,
                               detail=stop.detail)
            return "STOPPED", stop.code
        self.ledger.append("run_complete", run_id=self.run_id, arm=self.arm,
                           seed=self.seed,
                           calls_recorded=len(self.accepted))
        return "COMPLETE", None

    def _dispatch(self, idx, call):
        arm, seed, led = self.arm, self.seed, self.ledger
        done = len(led.recorded_calls(arm, seed)) + \
            len([r for r in led.outcomes(arm, seed)
                 if r["status"].startswith("FAILED")])
        if idx != done:
            raise HarnessStop("LEDGER_DISCONTINUITY",
                              f"call_index {idx} != completed {done}")
        # ---- pre-dispatch ceilings (fail closed BEFORE any transport use)
        if idx + 1 > CALL_CAPS[arm]:
            raise HarnessStop("CEILING_CALLS",
                              f"call {idx + 1} > cap {CALL_CAPS[arm]}")
        if self.clock.now_s() - self.started_s > WALL_CAP_S:
            raise HarnessStop("CEILING_WALL", "45 min wall cap exceeded")
        self._check_price_evidence()
        if self.clock.day != self.run_start_day and \
                self.clock.day not in led.quota_reset_days():
            raise HarnessStop(
                "QUOTA_RESET_UNVERIFIED",
                f"day {self.clock.day} has no evidence-backed quota reset")
        if led.quota_used(self.clock.day) >= self.daily_quota_cap:
            raise HarnessStop("QUOTA_EXHAUSTED",
                              f"day {self.clock.day} cap {self.daily_quota_cap}")
        prompt_hash = sha256_text(call["prompt"])
        if prompt_hash not in self.registered or \
                call.get("contains_cross_arm_material"):
            raise HarnessStop("PROMPT_CONTAMINATION",
                              "unregistered prompt or cross-arm material")
        if call["role"] not in ROLES[arm]:
            raise HarnessStop("ROLE_INVALID", call["role"])
        reserved = int(call["est_input_tokens"]) + int(call["max_output_tokens"])
        billed_so_far = led.billed_total(arm, seed)
        if billed_so_far + reserved > TOKEN_CAP_PER_ARM_SEED:
            raise HarnessStop(
                "CEILING_TOKENS",
                f"{billed_so_far} + reserved {reserved} > {TOKEN_CAP_PER_ARM_SEED}")
        # ---- write-ahead records, fsync-persisted before dispatch
        led.append("reserve", run_id=self.run_id, arm=arm, seed=seed,
                   call_index=idx, reserved_tokens=reserved,
                   billed_before=billed_so_far)
        led.append("dispatch_intent", run_id=self.run_id, arm=arm, seed=seed,
                   call_index=idx, role=call["role"],
                   prompt_sha256=prompt_hash,
                   requested_model=self.pin["model"],
                   quota_day=self.clock.day, started_at=self.clock.iso())
        # ---- fake transport (dependency-injected; network is denied)
        t0 = self.clock.now_s()
        try:
            resp = self.transport(call, idx)
        except TimeoutError:
            led.append("call_outcome", run_id=self.run_id, arm=arm, seed=seed,
                       call_index=idx, status="FAILED_TIMEOUT",
                       error="TIMEOUT", billed_tokens=0,
                       wall_time_s=self.clock.now_s() - t0,
                       started_at=self.clock.iso())
            raise HarnessStop("TIMEOUT", "no retry; fail-closed stop")
        if self.crash_after_response:
            raise SimulatedCrash("process died after response, before append")
        wall = self.clock.now_s() - t0
        self._validate_and_record(idx, call, resp, reserved, wall)

    # -- response validation: fail closed, reasoning NEVER used as content --
    def _validate_and_record(self, idx, call, resp, reserved, wall):
        arm, seed, led = self.arm, self.seed, self.ledger
        base = dict(run_id=self.run_id, arm=arm, seed=seed, call_index=idx,
                    started_at=self.clock.iso(), wall_time_s=wall)

        def fail(status, code, **extra):
            led.append("call_outcome", status=status, error=code, **base, **extra)
            raise HarnessStop(code, status)

        if not isinstance(resp, dict) or resp.get("http_status") != 200:
            fail("FAILED_HTTP", "HTTP_NOT_200")
        if resp.get("fallback_used"):
            fail("FAILED_FALLBACK", "FALLBACK_DETECTED")
        if resp.get("model") != self.pin["model"]:
            fail("FAILED_MODEL", "MODEL_MISMATCH",
                 response_model=resp.get("model"))
        if not resp.get("model_version"):
            fail("FAILED_MODEL", "MODEL_VERSION_UNVERIFIABLE",
                 response_model=resp.get("model"))
        usage = resp.get("usage")
        if not isinstance(usage, dict):
            fail("FAILED_USAGE", "MISSING_USAGE")
        if "reasoning_tokens" not in usage:
            fail("FAILED_USAGE", "UNMETERED_REASONING")
        vals = {}
        for k in ("input_tokens", "output_tokens", "reasoning_tokens"):
            v = usage.get(k)
            if not isinstance(v, int) or isinstance(v, bool):
                fail("FAILED_USAGE", "MISSING_USAGE", field=k)
            if v < 0:
                fail("FAILED_USAGE", "NEGATIVE_USAGE", field=k)
            vals[k] = v
        billed = vals["input_tokens"] + vals["output_tokens"] \
            + vals["reasoning_tokens"]
        if "billed_tokens" in usage and usage["billed_tokens"] != billed:
            fail("FAILED_USAGE", "INCONSISTENT_USAGE",
                 reported=usage["billed_tokens"], computed=billed)
        cost = resp.get("cost_usd")
        if cost is not None and cost != 0:
            fail("FAILED_COST", "NONZERO_COST", cost_usd=cost)
        content = resp.get("content")
        if content is None or not str(content).strip():
            # EMPTY_CONTENT: reasoning tokens are COUNTED, never substituted.
            led.append("call_outcome", status="FAILED_EMPTY_CONTENT",
                       error="EMPTY_CONTENT",
                       input_tokens=vals["input_tokens"],
                       output_tokens=vals["output_tokens"],
                       reasoning_tokens=vals["reasoning_tokens"],
                       billed_tokens=billed, cost_usd=0,
                       response_model=resp.get("model"),
                       model_version=resp.get("model_version"),
                       content_sha256=None, **base)
            raise HarnessStop("EMPTY_CONTENT",
                              "content empty; reasoning counted, not used")
        if vals["output_tokens"] > int(call["max_output_tokens"]) or \
                led.billed_total(arm, seed) + billed > TOKEN_CAP_PER_ARM_SEED:
            led.append("call_outcome", status="FAILED_OVERRUN",
                       error="OVERRUN",
                       input_tokens=vals["input_tokens"],
                       output_tokens=vals["output_tokens"],
                       reasoning_tokens=vals["reasoning_tokens"],
                       billed_tokens=billed, cost_usd=0,
                       response_model=resp.get("model"),
                       model_version=resp.get("model_version"),
                       content_sha256=sha256_text(str(content)),
                       content_quarantined=True, **base)
            raise HarnessStop("OVERRUN",
                              "actual usage exceeded reservation; quarantined")
        led.append("call_outcome", status="RECORDED", error=None,
                   input_tokens=vals["input_tokens"],
                   output_tokens=vals["output_tokens"],
                   reasoning_tokens=vals["reasoning_tokens"],
                   billed_tokens=billed, cost_usd=0,
                   response_model=resp.get("model"),
                   model_version=resp.get("model_version"),
                   content_sha256=sha256_text(str(content)), **base)
        self.accepted.append(str(content))

    # -- summaries ------------------------------------------------------------
    def ledger_summary(self):
        """Arm-seed summary in the frozen resource-ledger schema shape."""
        recs = self.ledger.recorded_calls(self.arm, self.seed)
        calls = [{"call_index": r["call_index"], "role": None,
                  "prompt_sha256": None,
                  "input_tokens": r["input_tokens"],
                  "output_tokens": r["output_tokens"],
                  "reasoning_tokens": r["reasoning_tokens"],
                  "billed_tokens": r["billed_tokens"],
                  "wall_time_s": r["wall_time_s"], "cost_usd": 0,
                  "started_at_utc": r["started_at"]} for r in recs]
        return {"run_id": self.run_id, "arm": self.arm, "seed": self.seed,
                "provider": self.pin["provider"], "model": self.pin["model"],
                "model_version": self.pin["model_version"], "calls": calls,
                "totals": {"calls": len(calls),
                           "billed_tokens": sum(c["billed_tokens"]
                                                for c in calls),
                           "wall_time_s": sum(c["wall_time_s"] for c in calls),
                           "cost_usd": 0, "candidate_cards_emitted": 0,
                           "auditor_review_minutes": 0},
                "budget_ref": BUDGET_REF,
                "cost_verified_zero_incremental": True}


# --------------------------------------------------------------------------
# Resume / multi-day continuation
# --------------------------------------------------------------------------
def resume_state(ledger):
    """Classify a persisted ledger for restart. Fail closed on orphans."""
    ok, why = ledger.verify_chain()
    if not ok:
        return "CORRUPT", why
    dangling = ledger.dangling_intents()
    if dangling:
        return "ORPHANED", f"{len(dangling)} dispatch(es) without outcome"
    return "CLEAN", "chain verified, no dangling dispatch"


def apply_quota_reset(ledger, *, day, evidence_ref):
    """Per-day quota reset ONLY on verified evidence. The reset is itself a
    ledger record; without this record the old day's usage still governs."""
    if not evidence_ref:
        raise HarnessStop("QUOTA_RESET_UNVERIFIED", "no evidence_ref")
    ledger.append("quota_reset", day=day, evidence_ref=evidence_ref)
    return True
