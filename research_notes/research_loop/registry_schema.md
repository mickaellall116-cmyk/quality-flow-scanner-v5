# Research Loop — Experiment Registry Schema (v1)

Implements Issue #1 comments 6044381696 + addendum 6044453166. Research-only.
No production, spending, acquisition, frozen-system changes, or holdout access.

## Experiment record fields

Every experiment in `registry.json` carries these fields. Unavailable fields are
recorded as `"UNKNOWN"` — never inferred.

### Identity & ownership
| Field | Type | Description |
|---|---|---|
| `experiment_id` | string | Stable, unique ID (e.g. `EXP-20261007-ORB-15M`). Never reused. |
| `title` | string | Short human-readable title. |
| `owner` | string | Implementing agent (`Muse`, `ChatGPT`, `Claude`, `Mike`). |
| `created_at` | string | ISO-8601 creation timestamp (UTC). |
| `state` | string | One of the state-machine states (see `state_machine.md`). |

### Hypothesis & sources
| Field | Type | Description |
|---|---|---|
| `hypothesis` | string | Falsifiable claim under test. |
| `primary_sources` | array | Primary sources (papers, data, prior experiments). `"UNKNOWN"` if none. |
| `literature_intake` | object | `{source, finding, hypothesis_derived}` for literature-fed ideas (addendum §2). |

### Specification & pins
| Field | Type | Description |
|---|---|---|
| `rule_spec_version` | string | Exact rule/spec version tested. |
| `code_pin` | string | Commit SHA of code used. `"UNKNOWN"` if not pinned. |
| `dataset_pin` | string | Dataset identifier + hash/manifest ref. |
| `output_pin` | string | Output/report blob hash or commit. |

### Execution tracking
| Field | Type | Description |
|---|---|---|
| `dependencies` | array | Experiment IDs or external prerequisites. |
| `next_action` | string | Single concrete next step, or `"NONE"` if terminal. |
| `attempted_variations` | array | EVERY variation tried, INCLUDING failures. Each: `{variation_id, description, result, verdict_ref}`. |
| `trial_budget` | object | `{allocated, used, unit}` — e.g. `{allocated: 1000, used: 1000, unit: "random_variants"}`. |
| `repair_budget` | object | `{allocated_rounds, used_rounds}` — stop at exhaustion → HOLD. |

### Design (required before READY)
| Field | Type | Description |
|---|---|---|
| `baseline_design` | string | Baseline / randomization design (e.g. "1000 synchronized random-entry variants"). |
| `costs` | string | Cost assumptions with provenance (scenario vs measured). |
| `validation_split` | string | In-sample / out-of-sample / holdout description. Sealed holdouts never touched. |
| `acceptance_criteria` | string | Pre-registered pass/fail criteria. |
| `robustness_diagnostics` | array | Preregistered robustness checks: markets, timeframes, cost scenarios (addendum §1). |

### Assessment
| Field | Type | Description |
|---|---|---|
| `limitations` | array | Known limitations (null mismatch, data coverage, etc.). |
| `verdict` | string | `PASS` / `FAIL` / `HOLD` / `KILL` / `"PENDING"` with scope note. |
| `decision_refs` | array | Issue #1 comment IDs, Slack timestamps, commits supporting the verdict. |

### Failure memory (addendum §3)
| Field | Type | Description |
|---|---|---|
| `failure_reason` | string | Indexed: why it failed (null_mismatch, costs_dominate, overfit, data_quality, ...). |
| `failure_market` | string | Market(s) tested. |
| `failure_timeframe` | string | Timeframe(s) tested. |
| `failure_data_source` | string | Data vendor/source. |
| `failure_strategy_family` | string | Strategy family (orb, ma_crossover, trend_4h, ...). |

Failed/killed experiments remain in the registry permanently and stay searchable.
They cannot be revived without explicitly new evidence (new experiment ID, linked
to the killed record).

## Message/acknowledgment ledger

Separate from experiments. Each bridge/Slack message tracked with:
- `message_id` (Issue comment ID or Slack ts)
- `status`: `SENT` → `DELIVERED/VERIFIED` → `ACKNOWLEDGED` → `WORK_RESULT`
- A successful post is NOT acknowledgment. Each status requires its own evidence.

## Idempotency key

`experiment_id + task_revision + evidence_pin` — a cycle MUST NOT create a
duplicate task when this key already exists in the task log.
