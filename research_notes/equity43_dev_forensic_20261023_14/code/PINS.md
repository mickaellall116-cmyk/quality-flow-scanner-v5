# Code pins — QF-EQUITY43-DEV-FORENSIC-20261023-14 (code-only audit snapshots)

All hashes sha256, recomputed by -14 from the files on disk in the -13 stage
tree and matched against `results.json` P0_pins of package `521980a`.
NO market data is included in this package; snapshots are simulator code only.

## Simulator lineage (the only files that change across the lineage)

| file | engine_orig (-08/-12) | engine_fork09 (-09) | engine_successor (-13) |
|---|---|---|---|
| pine_backtest.py | 447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5 | becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2 | 874d2a9b1d99171a4d3db709ece9ce4719b4d108a70f7e95b4a082692cc0c99d |
| pine_stack/pine_stack.py | 839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa | 30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4 | 8d4a964fd7bb08b4a98a55eb7fae222157ae27f1a768f255e7cbc152c9d15b03 |
| asof_benchmark.py (shared, introduced -09) | — | f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017 | f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017 |

Snapshots included here: engine_fork09/ and engine_successor/ versions of both
simulator files + asof_benchmark.py. engine_orig versions remain pinned and
inspectable in the -09 package (aad5563) lineage.

## Deltas (unified diffs in code/diffs/)

- orig → fork09 (the -09 integrity fork): B2 as-of mark fix in BOTH simulators
  (mark at latest bar COMPLETED at or before t; bar end = start + 4h), and in
  pine_stack the coincident-entry tie-break changes from candidate index to
  the canonical key (-rs, symbol, signal_idx). B1 (benchmark as-of) lives in
  asof_benchmark.py: SPY daily bars stamped at session completion (16:00 ET).
- fork09 → successor (the -13 deltas): (a) right-censored terminal candidates
  (exit/exit_time None) register no exit event and compete at entry under the
  identical rank/cap/sector/risk gates; (b) a terminal accounting step values
  still-open censored positions at the as-of mark of the last bar completed at
  or before `cutoff` and includes the unrealized value in final_equity (no
  exit, cash flow, or trade R fabricated; an assertion requires any post-event
  open position to be censored); (c) both simulators return a per-candidate
  ledger/disposition record for trade-by-trade cross-validation. The canonical
  (symbol, signal_idx) candidate order for the control path is applied by the
  -13 driver (run_study13.py, committed in package 521980a, sha256
  4962e30d8b42124e… — verified identical to the executed stage copy), which
  sorts the candidate list by that total key before BOTH simulator paths;
  the configuration is pinned in -13 results.json (experiment_config_sha256
  87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706).

## Byte-identical across orig / fork09 / successor (strategy sources)

| file | sha256 |
|---|---|
| scanner_rules.py | 62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c |
| pine_ranking/pine_ranking.py | 77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6 |
| pine_signal_quality/pine_signal_quality.py | b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69 |
| pine_exposure/pine_exposure.py | 9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be |

The trading strategy did not change at any step of the lineage. Only
simulator accounting (as-of marking, tie ordering, censoring treatment) and
driver-side candidate ordering changed, each under its own governed task.
