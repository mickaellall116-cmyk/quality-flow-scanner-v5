# GRADER PACKET — Issue #9 blinded scoring design (frozen at prep)

## Purpose
Score candidate hypothesis cards from Arm A and Arm B without the grader knowing which
arm produced which card, under the rubric frozen in `comparison_protocol.json`.

## Roles and separation
- **Producer** (executor): runs the arms, collects raw card sets, fills the resource ledger.
- **Anonymizer** (may be the producer, script-assisted): strips `origin_arm` and arm-specific
  ids, assigns anonymous ids `CAND-###`, shuffles packet order under a recorded shuffle
  seed, and writes the blinding key to a sealed file. The anonymizer does NOT grade.
- **Auditor/grader**: receives ONLY the anonymized packet + fact sheet + registry export.
  Scores every card against the five gates. The grader does not see the blinding key,
  raw arm outputs, or the resource ledger until scores are locked.
- **Key holder**: whoever holds the blinding key does not grade. In this two-agent setup
  the key file is hashed at anonymization time and opened only after the score sheet's
  hash is recorded — the hash ordering is the blinding evidence.

## Packet contents (exactly)
1. Anonymized candidate cards (schema-validated first; SCHEMA_INVALID cards are recorded
   and excluded from gate scoring, with the validation errors listed).
2. `fact_sheet.md` and `killed_family_registry_export.json` (same frozen hashes as the arms used).
3. The scoring worksheet (below). Nothing else: no arm sizes, no call counts, no costs.

## Scoring worksheet (per candidate)
| field | content |
|---|---|
| anon_id | CAND-### |
| G1_testable | pass / fail + reason |
| G2_no_leakage | pass / fail + reason (name the violating input/timing) |
| G3_data_available | pass / DATA_BLOCKED + missing data named |
| G4_not_killed_family | pass / DEDUPE_REJECT (registry entry id) / ADJACENCY_FLAGGED (needs human confirmation) |
| G5_execution_realistic | pass / fail + reason |
| duplicate_of | anon_id or none (family_id + rule-signature match; synonyms count once) |
| provenance_errors | count + notes (factual claims not supported by the fact sheet) |
| verdict | PASS only if all gates pass and not a duplicate |
| review_minutes | auditor time on this card |

## Procedure (frozen)
1. Validate all cards against `hypothesis_schema.json`; log SCHEMA_INVALID set.
2. Machine pre-screen (deterministic assists, never final verdicts): family-string match
   against the registry export; declaration flags (same-bar timing, unavailable-at-decision
   data); cross-candidate family_id + rule-signature duplicate candidates.
3. Auditor reviews every card including the machine flags; the auditor may override a
   machine flag only with a written reason on the worksheet (overrides are counted and
   reported — they are a known disagreement surface).
4. Lock scores: hash the completed worksheet. Only then open the blinding key.
5. Unblind, join with the resource ledger, compute the primary/secondary metrics exactly
   as frozen in the protocol, and record adjudicator disagreements (if a second grader
   is used, disagreements are resolved by a named adjudicator BEFORE unblinding, or the
   affected candidates are marked not-passed).

## Fail-closed controls
- Packet hash mismatch vs the run manifest → scoring does not start.
- Any card whose provenance lacks IDEA_ONLY tagging → excluded and logged.
- Blinding key opened early (hash-order evidence broken) → the seed pair is reported
  inconclusive, never silently re-blinded.
- The grader never sees costs/tokens before locking scores (prevents budget-anchored grading).
