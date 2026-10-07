# Research Loop — Failure Memory (v1)

Queryable index of failed/killed experiments. Per addendum 6044453166 §3.
Seeded from `registry.json`. Failed records remain searchable permanently.

## Index

| Experiment ID | Failure reason | Market | Timeframe | Data source | Strategy family | Verdict | Ref |
|---|---|---|---|---|---|---|---|
| EXP-20261007-ORB-15M | null_mismatch | QQQ, SPY | 15m | Tiingo IEX | orb | HOLD | 6046384583 |

## Query patterns

The registry is JSON — query with `jq`:

```bash
# All failures in a strategy family
jq '.experiments[] | select(.verdict=="FAIL" or .verdict=="KILL" or .state=="HOLD") | select(.failure_strategy_family=="orb")' registry.json

# All failures by reason
jq '.experiments[] | select(.failure_reason=="costs_dominate") | .experiment_id' registry.json

# All failures on a data source
jq '.experiments[] | select(.failure_data_source=="Yahoo") | {id: .experiment_id, reason: .failure_reason}' registry.json
```

## Failure reason taxonomy

- `null_mismatch` — baseline/randomization does not match the estimand
- `costs_dominate` — genuine signal smaller than friction
- `overfit` — fails on held-out / forward data
- `data_quality` — vendor revisions, missing bars, PIT violations
- `repair_exhausted` — repair budget spent without clearance
- `decay` — worked historically, degrades out-of-sample
- `leakage` — lookahead or survivorship bias found

## Revival rule

A `FAIL`/`KILL` record cannot be revived. New evidence requires a NEW
experiment ID linked to the killed record via `dependencies`.
