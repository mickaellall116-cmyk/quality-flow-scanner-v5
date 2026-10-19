#!/usr/bin/env python3
"""r2 staging check: the 8 installed-member pins of the -35 r1 receipt §5
must be present, hash-exact, inside the fresh venv's site-packages.
Any missing member = nonzero exit = material failure (STOP)."""
import hashlib
import sys
from pathlib import Path

EXPECTED = {
    "f5e70a904464ced8b055a39756c59f51c12f693e7f4b0c290f955a5002614756": "PMC calendar_registry.py",
    "135ba9dc683eb6797fba014d8e5979d0dc12537fa23fcabd7f2302c94712f4e3": "PMC calendars/nyse.py",
    "e85f5edb348f4b6455ac92b97e10b81a70975bab7c7e97cf7a616c82c56ac4b3": "PMC holidays/nyse.py",
    "1d40c845ac4b7db1d0d9fe46cfdd8b881732977208fdd376c00b1f7ce9e71525": "PMC METADATA",
    "7d12d53482fe295bd5a9b272a635df2292528b8dc19538c93649fa4ee84b40e6": "EC calendar_utils.py",
    "baa39f07163abafcf2800b69edc5d920c3db0a64f8bbb30dc7d522883d0b5bd7": "EC exchange_calendar_xnys.py",
    "a2444bd7aef3ff651faff3f9117c47a0d41e9e7c312f38ecf42403e4d996830e": "EC us_holidays.py",
    "b0d856a2f790e0d645d5847880ccd21de2771921a7ed78464184da4cd73289ec": "EC METADATA",
}

sp = Path(sys.prefix) / "lib" / "python3.12" / "site-packages"
found = {}
for p in sp.rglob("*"):
    if p.is_file():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h in EXPECTED:
            found[h] = str(p.relative_to(sp))
missing = [label for h, label in EXPECTED.items() if h not in found]
for h, label in EXPECTED.items():
    print(("PASS" if h in found else "FAIL"), label, found.get(h, "MISSING"))
print(f"members {len(found)}/{len(EXPECTED)}")
sys.exit(1 if missing else 0)
