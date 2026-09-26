# Decision-Time Availability Audit — Amendment 5

Status: FROZEN GOVERNANCE / FAILURE-MODE CONTROL
Date: 2026-09-25
Builds on original framework + Amendments 1–4.
Purpose: close Claude finding N-11 and fully separate manifest provenance from a single GitHub trust domain.

No V5.4, ERD v0.1, production logic, or killed-family change.

## 1. Dual-domain preregistration anchor (N-11)

Amendment 4 §2 is superseded only where it allowed GitHub Issue #1 to be sufficient by itself.

For every family availability manifest, before the first performance artifact is generated, BOTH anchors below are mandatory:

### Anchor A — GitHub coordination anchor

Post to standing GitHub Issue #1:
- family_id;
- repository + branch;
- manifest path;
- manifest commit SHA;
- manifest content SHA256;
- framework/amendment version.

Record the GitHub issue-comment ID and server timestamp.

GitHub Issue #1 remains the project coordination ledger, but is not sufficient provenance by itself.

### Anchor B — external email anchor

Send an external email record through the project research mailbox infrastructure, outside GitHub, containing the exact same:
- family_id;
- manifest commit SHA;
- manifest content SHA256;
- framework/amendment version;
- GitHub issue-comment ID from Anchor A.

The email record must be server-timestamped and immutable in message body after send. Deletion is permitted by the mail system only in the ordinary operational sense; deletion does not preserve confirmatory status because the validator requires the original message to remain independently retrievable.

Record:
- mailbox/provider identity;
- immutable message ID;
- thread ID if applicable;
- server timestamp.

The external email message ID and its exact anchored fields must be independently retrievable at validation time.

A self-authored local file, repository artifact, draft email, unsent message, screenshot, or copied timestamp is not an external anchor.

## 2. Replay provenance requirements

Every confirmatory replay artifact must embed:
- manifest content SHA256;
- manifest commit SHA;
- GitHub Anchor A comment ID;
- external Anchor B message ID;
- both anchor timestamps.

Before performance is loaded or displayed, validation must verify:

1. the manifest bytes hash to the anchored SHA256;
2. the anchored Git commit resolves to those manifest bytes;
3. GitHub Anchor A exists and contains the exact family_id, commit SHA, and manifest SHA256;
4. external Anchor B exists and contains the exact same family_id, commit SHA, and manifest SHA256 plus the Anchor A comment ID;
5. both anchors predate the first performance artifact for that manifest version.

Failure of any check = provenance FAIL. Missing/deleted/unresolvable anchor = FAIL, not REVIEW.

## 3. Manifest-version granularity

Dual anchoring is required for EACH frozen manifest version.

A dated amendment producing manifest version M2 requires a new:
- commit SHA;
- manifest SHA256;
- GitHub anchor;
- external email anchor.

M2 does not replace or erase M1. Prior anchors and inspected results remain in the family ledger and multiple-testing history.

No anchor may be reused across different manifest hashes.

## 4. Anchor tamper test — T16

Create M1 and valid Anchors A1/B1.

Run these deterministic cases:

### T16a — GitHub anchor edited or deleted
Simulate A1 becoming unavailable or changing any anchored field while B1 remains intact.
Expected: provenance FAIL.

### T16b — external email anchor unavailable
Simulate B1 being deleted/unresolvable while A1 remains intact.
Expected: provenance FAIL.

### T16c — GitHub history rewritten
Alter repository history/manifest while A1 and B1 retain original H1/S1.
Expected: provenance FAIL under T15/T16.

### T16d — replacement anchors created after inspection
Create A2/B2 after a performance artifact already exists and point them to altered M2.
Expected: M2 cannot retroactively validate the earlier result. It is a new dated manifest version and any confirmatory replay must occur after both new anchors.

### T16e — cross-anchor mismatch
A1 and B1 contain different manifest hashes, commit SHAs, family_ids, or B1 references the wrong A1 comment ID.
Expected: provenance FAIL.

### T16f — valid dual anchor
A1 and B1 exist, agree exactly, predate performance, and manifest/commit bytes resolve correctly.
Expected: provenance check PASS.

## 5. Trust boundary and limitation

The control does not claim mathematical immutability of GitHub or email infrastructure.

Its purpose is to require two independently timestamped records in separate service domains and to fail closed if either record disappears, changes, or disagrees.

An attacker who compromises both independent service domains may still defeat the control. That residual infrastructure risk is explicitly accepted as outside the research framework's reasonable threat model.

A stronger third-party cryptographic timestamping service may be added later as defense-in-depth, but it is not required to establish specification READY under this threat model.

## 6. Current READY gate

The latest required deterministic suite is now:
- T1 through T16;
- T2C;
with superseded tests evaluated under their latest amendment semantics.

Specification READY still requires independent audit confirming no unresolved CRITICAL or MATERIAL specification finding.

Implementation PASS additionally requires successful dual-anchor validation and the complete current deterministic test suite before candidate performance may receive confirmatory interpretation.

Specification READY is not implementation PASS and is not economic/trading PASS.
