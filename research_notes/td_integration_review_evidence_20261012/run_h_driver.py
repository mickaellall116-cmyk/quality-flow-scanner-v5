import json, sys
from pathlib import Path
BASE = Path('/tmp/tdreview/run_h/research_notes')
sys.path.insert(0, str(BASE / 'td_lifecycle_repair_candidate'))
sys.path.insert(0, str(BASE / 'pilot_harness'))
sys.path.insert(0, '/tmp/tdreview')
import td_min_collector as C
from rate_limiter import RollingCreditLimiter
from run_integration import manifest, req, payload  # reuse builders (module run skipped: __main__ guard absent -> it WILL run)
