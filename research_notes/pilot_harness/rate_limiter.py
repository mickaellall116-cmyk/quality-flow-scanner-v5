#!/usr/bin/env python3
"""
rate_limiter.py — Credit-weighted ROLLING-WINDOW rate limiter, v3
(ChatGPT 6039806101, finding 2).

v2 defects, proven by ChatGPT's source review:
  (a) Only `daily_spent` was persisted; `_window` was memory-only. After 8
      credits at t=0, restarting at t=7.5s permitted another burst,
      violating <=8 credits per rolling 60 seconds.
  (b) `_today_key()` converted `time.monotonic()` through `gmtime`;
      monotonic time has no calendar epoch, so this was not a valid
      daily-boundary clock.
  (c) JSON writes were neither locked across processes nor atomic.

v3 design:
  - The rolling 60s WINDOW LEDGER is persisted: every granted request is
    recorded as (epoch_wall_seconds, weight) in the state file.
  - Clock is EPOCH WALL TIME, injectable for tests (default: time.time).
    Daily boundaries use UTC calendar days via gmtime(wall_time) — valid
    because wall time has a real epoch.
  - Every acquire does: interprocess lock → fresh read → evict entries
    older than 60s → UTC day-rollover check → window+cap check → append →
    ATOMIC write (temp file + os.replace) → unlock.
  - Oversized requests (weight > credits_per_minute) refused immediately.
  - Fail-closed: refusal (False), never silent queueing past a cap.
  - Without state_path the limiter is process-local (thread lock only);
    restart-safety requires state_path.

Endpoint credit weights: named per-endpoint with entitlement evidence at
execution time. No assumed weights are used (standing rule).

Usage:
  python3 rate_limiter.py --demo   # fake wall clock, no network
"""
import argparse
import calendar
import fcntl
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path

WINDOW_SECONDS = 60.0


class RollingCreditLimiter:
    """Conservative credit-weighted rolling-window limiter, restart-safe."""

    def __init__(self, credits_per_minute: int, daily_cap: int,
                 state_path: str | Path | None = None,
                 clock=None):
        """clock: callable returning EPOCH WALL SECONDS (default time.time).
        For tests, inject a FakeWallClock. Monotonic clocks are NOT valid
        here — daily boundaries need a calendar epoch."""
        if credits_per_minute <= 0 or daily_cap <= 0:
            raise ValueError("budgets must be positive")
        self._cpm = credits_per_minute
        self._daily_cap = daily_cap
        self._wall = clock or time.time
        self._state_path = Path(state_path) if state_path else None
        self._lock_path = (self._state_path.with_name(
            self._state_path.name + ".lock") if self._state_path else None)
        self._thread_lock = threading.Lock()
        # In-memory fallback when no state_path (not restart-safe by design).
        self._mem = {"day": None, "spent": 0, "window": []}

    # -- wall-clock helpers -------------------------------------------
    @staticmethod
    def _today_key(wall_t: float) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(wall_t))

    # -- interprocess locking ------------------------------------------
    @contextmanager
    def _locked(self):
        if self._lock_path is None:
            with self._thread_lock:
                yield
            return
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self._lock_path, "w")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()

    # -- state load/save (call only under _locked) ----------------------
    def _load(self) -> dict:
        if self._state_path is None:
            return self._mem
        try:
            d = json.loads(self._state_path.read_text())
            return {"day": str(d.get("day")),
                    "spent": int(d.get("spent", 0)),
                    "window": [(float(t), int(w))
                               for t, w in d.get("window", [])]}
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            return {"day": None, "spent": 0, "window": []}

    def _save(self, state: dict):
        if self._state_path is None:
            self._mem = state
            return
        # Atomic: write temp in same directory, then os.replace.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._state_path.parent),
            prefix=self._state_path.name + ".tmp.")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"day": state["day"], "spent": state["spent"],
                           "window": state["window"]}, f)
            os.replace(tmp_name, self._state_path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # -- core -----------------------------------------------------------
    @staticmethod
    def _evict(window: list, now: float) -> list:
        return [(t, w) for t, w in window if t > now - WINDOW_SECONDS]

    def _check_and_grant(self, state: dict, weight: int,
                         now: float) -> tuple[bool, dict]:
        """Pure check; returns (granted, new_state)."""
        today = self._today_key(now)
        if state["day"] != today:
            state = {"day": today, "spent": 0, "window": []}
        window = self._evict(state["window"], now)
        if sum(w for _, w in window) + weight > self._cpm:
            return False, state
        if state["spent"] + weight > self._daily_cap:
            return False, state
        window.append((now, weight))
        return True, {"day": today, "spent": state["spent"] + weight,
                      "window": window}

    def try_acquire(self, weight: int, label: str = "") -> bool:
        """Grant iff the request fits the rolling 60s window AND the daily
        cap. Returns False on refusal (fail-closed). Never blocks."""
        if weight <= 0:
            raise ValueError("weight must be positive")
        if weight > self._cpm:
            return False  # oversized: can never fit in any window
        with self._locked():
            state = self._load()
            granted, new_state = self._check_and_grant(
                state, weight, self._wall())
            if granted:
                self._save(new_state)
            return granted

    def acquire(self, weight: int, label: str = "",
                timeout: float = 600.0) -> bool:
        """Blocking variant: wait until the request fits (or timeout /
        daily-cap refusal). Returns False only on daily-cap refusal."""
        if weight <= 0:
            raise ValueError("weight must be positive")
        if weight > self._cpm:
            return False
        deadline = self._wall() + timeout
        while True:
            if self.try_acquire(weight, label):
                return True
            with self._locked():
                state = self._load()
                today = self._today_key(self._wall())
                spent = 0 if state["day"] != today else state["spent"]
                if spent + weight > self._daily_cap:
                    return False
            if self._wall() > deadline:
                raise TimeoutError(f"limiter wait exceeded for {label}")
            time.sleep(0.05)

    def window_sum(self) -> int:
        with self._locked():
            state = self._load()
            now = self._wall()
            if state["day"] != self._today_key(now):
                return 0
            return sum(w for _, w in self._evict(state["window"], now))

    @property
    def daily_spent(self) -> int:
        with self._locked():
            state = self._load()
            if state["day"] != self._today_key(self._wall()):
                return 0
            return state["spent"]


class FakeWallClock:
    """Deterministic EPOCH WALL clock for tests (no sleep/network).

    Returns epoch seconds; advance() moves wall time forward. Day
    boundaries are real UTC calendar days via gmtime, so day-rollover
    tests are deterministic.
    """
    def __init__(self, t: float | None = None):
        # Default: 2026-10-07 12:00:00 UTC.
        self.t = t if t is not None else float(calendar.timegm(
            (2026, 10, 7, 12, 0, 0, 0, 0, 0)))

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float):
        self.t += dt


# Backwards-compat alias (v2 name; semantics are now wall time).
FakeClock = FakeWallClock


def demo():
    print("Rolling-window limiter v3 demo (fake wall clock, 8 cr/min, 800/day).")
    clk = FakeWallClock()
    lim = RollingCreditLimiter(8, 800, clock=clk)

    # ChatGPT's v3 counterexample: 8 credits at t=0, restart at t=7.5s,
    # 9th must be REFUSED via the persisted window ledger.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "ledger.json"
        a = RollingCreditLimiter(8, 800, state_path=sp, clock=clk)
        got = [a.try_acquire(1, f"r{i}") for i in range(8)]
        assert all(got)
        clk.advance(7.5)
        b = RollingCreditLimiter(8, 800, state_path=sp, clock=clk)  # restart
        ninth = b.try_acquire(1, "r9")
        print(f"  8x1-credit at t=0, restart, 9th at t=7.5s: {ninth} "
              f"(must be False)")
        assert ninth is False
        assert b.window_sum() == 8

        # Window slides: at t=60.1s the first credits expire.
        clk.advance(52.6)  # t=60.1
        assert b.window_sum() == 0
        assert b.try_acquire(2, "after-slide") is True
        print("  window slide at t=60.1s: evicted, 2-credit granted")

    # Two-credit saturation.
    lim2 = RollingCreditLimiter(8, 800, clock=FakeWallClock())
    r = [lim2.try_acquire(2, f"w{i}") for i in range(5)]
    assert r == [True, True, True, True, False]
    print(f"  5x2-credit burst: {r} (must be [T,T,T,T,F])")

    # Oversized request refused immediately.
    assert lim2.try_acquire(9, "oversized") is False
    print("  oversized 9-credit request: refused")

    # UTC day rollover: spent resets, window evicted.
    rollover_t = float(calendar.timegm((2026, 10, 7, 23, 59, 50, 0, 0, 0)))
    clk3 = FakeWallClock(rollover_t)
    lim3 = RollingCreditLimiter(8, 800, clock=clk3)
    assert lim3.try_acquire(3, "late") is True
    assert lim3.daily_spent == 3
    clk3.advance(20)  # 2026-10-08 00:00:10 UTC
    assert lim3.daily_spent == 0
    assert lim3.window_sum() == 0
    assert lim3.try_acquire(3, "next-day") is True
    print("  UTC day rollover: spent reset, window evicted, next-day granted")

    print("\ndemo: all v3 rolling-window properties hold")


def main() -> int:
    ap = argparse.ArgumentParser(description="Rolling-window limiter (v3)")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
