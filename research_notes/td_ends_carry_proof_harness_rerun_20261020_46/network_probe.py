#!/usr/bin/env python3
"""Network-denial probe: exits 0 only if ALL probes FAIL (no network)."""
import socket
import sys

ok = True

try:
    s = socket.create_connection(("1.1.1.1", 443), timeout=3)
    s.close()
    print("PROBE connect 1.1.1.1:443 -> UNEXPECTED SUCCESS")
    ok = False
except OSError as e:
    print(f"PROBE connect 1.1.1.1:443 -> failed as required: {e}")

try:
    socket.getaddrinfo("pypi.org", 443)
    print("PROBE dns pypi.org -> UNEXPECTED SUCCESS")
    ok = False
except OSError as e:
    print(f"PROBE dns pypi.org -> failed as required: {e}")

print("NETWORK_DENIED" if ok else "NETWORK_AVAILABLE")
sys.exit(0 if ok else 1)
