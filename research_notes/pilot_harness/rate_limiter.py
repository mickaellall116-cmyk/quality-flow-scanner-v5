#!/usr/bin/env python3
"""
rate_limiter.py — Credit-weighted ROLLING-WINDOW rate limiter, v2
(ChatGPT 6037842097, repair item 4).

v1 (token bucket) defect, proven by ChatGPT's probe: CreditLimiter(8,800)
allows eight credits at t=0 and a NINTH at t=7.5s — burst + continuous
refill does not guarantee <=8 credits per rolling 60 seconds.

v2 design:
  - Rolling 60-second window: keep (monotonic_t, weight) of every granted
    request; evict entries older than 60s; grant iff
    window_sum + weight <= credits_per_minute.
  - Oversized requests (weight > credits_per_minute) are refused
    immediately — they can never fit in any window.
  - Daily accounting is PERSISTENT (JSON sidecar): restarts do not reset
    the daily spent total. Grant iff daily_spent + weight <= daily_cap.
  - Fail-closed: refusal (False), never silent queueing past the cap.
  - Clock injection: pass clock=<callable> for deterministic tests
    (fake monotonic clock, no sleep/network).

Endpoint credit weights: named per-endpoint with entitlement evidence at
execution time. No assumed weights are used (blocker 5 standing rule).

Usage:
  python3 rate_limiter.py --demo   # accelerated demo, no network
"""
import argparse
import json
import threading
import time
from collections import deque
from pathlib import Path


class RollingCreditLimiter:
    """Conservative credit-weighted rolling-window limiter."""

    def __init__(self, credits_per_minute: int, daily_cap: int,
                 state_path: str | Path | None = None,
                 clock=None):
        if credits_per_minute <= 0 or daily_cap <= 0:
            raise ValueError("budgets must be positive")
        self._cpm = credits_per_minute
        self._daily_cap = daily_cap
        self._window: deque[tuple[float, int]] = deque()  # (mono_t, weight)
        self._lock = threading.Lock()
        self._clock = clock or time.monotonic
        self._state_path = Path(state_path) if state_path else None
        self._daily_spent = 0
        self._day_key = self._today_key()
        if self._state_path:
            self._load()

    # -- persistence ----------------------------------------------------
    def _today_key(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self._clock()))

    def _load(self):
        try:
            d = json.loads(self._state_path.read_text())
            if d.get("day") == self._today_key():
                self._daily_spent = int(d.get("spent", 0))
                self._day_key = d["day"]
        except (FileNotFoundError, ValueError, KeyError):
            pass

    def _save(self):
        if self._state_path:
            self._state_path.write_text(json.dumps(
                {"day": self._day_key, "spent": self._daily_spent}))

    def _roll_day(self):
        today = self._today_key()
        if today != self._day_key:
            self._day_key = today
            self._daily_spent = 0
            self._window.clear()
            self._save()

    # -- core -----------------------------------------------------------
    def _evict(self, now: float):
        while self._window and self._window[0][0] <= now - 60.0:
            self._window.popleft()

    def window_sum(self) -> int:
        with self._lock:
            self._roll_day()
            self._evict(self._clock())
            return sum(w for _, w in self._window)

    def try_acquire(self, weight: int, label: str = "") -> bool:
        """Grant iff the request fits the rolling 60s window AND the daily
        cap. Returns False on refusal (fail-closed). Never blocks."""
        if weight <= 0:
            raise ValueError("weight must be positive")
        if weight > self._cpm:
            return False  # oversized: can never fit in any window
        with self._lock:
            self._roll_day()
            now = self._clock()
            self._evict(now)
            if sum(w for _, w in self._window) + weight > self._cpm:
                return False
            if self._daily_spent + weight > self._daily_cap:
                return False
            self._window.append((now, weight))
            self._daily_spent += weight
            self._save()
            return True

    def acquire(self, weight: int, label: str = "",
                timeout: float = 600.0) -> bool:
        """Blocking variant: wait until the request fits (or timeout /
        daily-cap refusal). Returns False only on daily-cap refusal."""
        if weight <= 0:
            raise ValueError("weight must be positive")
        if weight > self._cpm:
            return False
        deadline = self._clock() + timeout
        while True:
            if self.try_acquire(weight, label):
                return True
            # Distinguish window-full (retry) from cap-full (refuse).
            with self._lock:
                self._roll_day()
                if self._daily_spent + weight > self._daily_cap:
                    return False
            if self._clock() > deadline:
                raise TimeoutError(f"limiter wait exceeded for {label}")
            time.sleep(0.05)

    @property
    def daily_spent(self) -> int:
        with self._lock:
            self._roll_day()
            return self._daily_spent


class FakeClock:
    """Deterministic monotonic clock for tests (no sleep/network)."""
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float):
        self.t += dt


def demo():
    print("Rolling-window limiter demo (fake clock, 8 cr/min, 800/day).")
    clk = FakeClock()
    lim = RollingCreditLimiter(8, 800, clock=clk)

    # ChatGPT's counterexample: 8 credits at t=0, 9th at t=7.5s → REFUSED.
    results = [lim.try_acquire(1, f"r{i}") for i in range(8)]
    clk.advance(7.5)
    ninth = lim.try_acquire(1, "r9")
    print(f"  8x1-credit at t=0: {results} (all True)")
    print(f"  9th 1-credit at t=7.5s: {ninth} (must be False)")
    assert all(results) and ninth is False

    # Window slides: at t=60.1s the first credits expire.
    clk.advance(52.6)  # t=60.1
    print(f"  window_sum at t=60.1s: {lim.window_sum()} (must be 0)")
    assert lim.window_sum() == 0
    assert lim.try_acquire(2, "after-slide") is True

    # Two-credit saturation: 4x2 = 8 fills the window; 5th refused.
    clk2 = FakeClock()
    lim2 = RollingCreditLimiter(8, 800, clock=clk2)
    r = [lim2.try_acquire(2, f"w{i}") for i in range(5)]
    print(f"  5x2-credit burst: {r} (must be [T,T,T,T,F])")
    assert r == [True, True, True, True, False]

    # Oversized request refused immediately.
    assert lim2.try_acquire(9, "oversized") is False
    print("  oversized 9-credit request: refused (must be False)")

    # Daily cap + persistence across restart.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "spent.json"
        clk3 = FakeClock()
        a = RollingCreditLimiter(8, 5, state_path=sp, clock=clk3)
        assert a.try_acquire(2, "a1") and a.try_acquire(2, "a2")
        assert a.try_acquire(2, "a3") is False  # 6 > 5
        b = RollingCreditLimiter(8, 5, state_path=sp, clock=clk3)  # restart
        print(f"  after restart daily_spent={b.daily_spent} (must be 4)")
        assert b.daily_spent == 4
        assert b.try_acquire(2, "b1") is False  # cap still enforced
    print("\ndemo: all rolling-window properties hold")


def main() -> int:
    ap = argparse.ArgumentParser(description="Rolling-window limiter (v2)")
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
