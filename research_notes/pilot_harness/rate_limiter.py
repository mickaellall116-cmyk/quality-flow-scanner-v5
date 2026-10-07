#!/usr/bin/env python3
"""
rate_limiter.py — Credit-weighted rate limiter design (ChatGPT 6037625281, blocker 5).

Free tier: 8 credits/minute, 800 credits/day.

ChatGPT's finding: "Eight-second spacing is insufficient by itself for
repeated 2-credit requests under an 8-credit/min budget."

Math: at 8-second spacing, a 1-credit request consumes 7.5 credits/min —
within budget. But a 2-credit request every 8 seconds consumes 15 credits/min —
nearly 2x over budget. Spacing alone cannot enforce a credit-weighted budget.

Design: token-bucket limiter where each request declares its credit weight
BEFORE execution. The bucket refills at 8 credits per 60 seconds. A request
blocks until its full weight is available. A hard daily cap (800) is enforced
independently; the limiter refuses (not queues) once the cap is reached.

Endpoint credit weights (Twelve Data, free tier — weights verified against
https://twelvedata.com/docs at pilot time; assumed weights are NOT used):
  /time_series (1h or 4h, outputsize<=5000) : weight TBD at execution
  /symbol_search, /earnings, /dividends    : weight TBD at execution
  corporate-action endpoint                : weight TBD at execution

The pilot plan v2 assumed 2 credits per action call WITHOUT verification.
Per blocker 5, exact endpoint weights must be named with entitlement evidence
BEFORE execution; the limiter below takes weights as explicit parameters so
an unverified assumption cannot silently pass.

Usage (design demonstration — no network calls):
  python3 rate_limiter.py --demo
"""
import argparse
import threading
import time


class CreditLimiter:
    """Thread-safe token-bucket limiter weighted by API credits."""

    def __init__(self, credits_per_minute: float, daily_cap: int):
        self._rate = credits_per_minute / 60.0          # credits per second
        self._capacity = credits_per_minute             # burst = 1 minute
        self._tokens = float(credits_per_minute)        # start full
        self._daily_cap = daily_cap
        self._daily_spent = 0
        self._lock = threading.Lock()
        self._last = time.monotonic()
        self.log: list[tuple[float, int, str]] = []     # (t, weight, label)

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)

    def acquire(self, weight: int, label: str = "") -> bool:
        """Block until `weight` credits are available. Returns False if the
        daily cap would be exceeded (fail-closed: refuse, do not queue)."""
        if weight <= 0:
            raise ValueError("weight must be positive")
        deadline = time.monotonic() + 600  # 10-min max wait per request
        while True:
            with self._lock:
                self._refill()
                if self._daily_spent + weight > self._daily_cap:
                    return False
                if self._tokens >= weight:
                    self._tokens -= weight
                    self._daily_spent += weight
                    self.log.append((time.monotonic(), weight, label))
                    return True
            if time.monotonic() > deadline:
                raise TimeoutError(f"limiter wait exceeded for {label}")
            time.sleep(0.05)

    @property
    def daily_spent(self) -> int:
        with self._lock:
            return self._daily_spent


def demo():
    print("Credit-weighted limiter demo (accelerated clock: 480 credits/min "
          "standing in for 8/min so the demo finishes quickly).")
    print("Real pilot: CreditLimiter(credits_per_minute=8, daily_cap=800).")
    print()
    lim = CreditLimiter(credits_per_minute=480, daily_cap=800)

    # Naive 8-second spacing with 2-credit requests would need
    # 15 credits/min — over budget. The limiter serializes correctly.
    t0 = time.monotonic()
    for i in range(6):
        ok = lim.acquire(2, label=f"time_series_1h #{i+1}")
        dt = time.monotonic() - t0
        print(f"  [{dt:5.2f}s] 2-credit request #{i+1}: "
              f"{'acquired' if ok else 'REFUSED (daily cap)'}")
    print(f"\nDaily spent: {lim.daily_spent} (cap 800)")

    # Daily-cap refusal demonstration
    lim2 = CreditLimiter(credits_per_minute=480, daily_cap=5)
    r1 = lim2.acquire(2, label="a")
    r2 = lim2.acquire(2, label="b")
    r3 = lim2.acquire(2, label="c")   # 2+2+2=6 > 5 → refused
    print(f"\nCap-5 limiter: req1={r1}, req2={r2}, req3={r3} "
          f"(req3 refused: 6 > 5)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Credit-weighted limiter design")
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
