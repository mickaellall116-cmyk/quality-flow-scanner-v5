# Quality Flow — direct work handoff and readback protocol (2026-11-03)

Owner: ChatGPT / Muse. Purpose: avoid routing routine research tasks through Mike.

1. **GitHub Issue #1 is the primary durable work queue** for Quality Flow. Slack #qualityflowscaner is a notification and discussion channel, not the only copy of an assignment.
2. New research assignments must contain: owner, precise source commit or artifact, bounded work requested, acceptance tests, output path, and known gates. Put the full text in Issue #1 or an immutable repo document and link it from the issue.
3. After posting, the sender fetches its own post/file and confirms it is accessible and accurate. Only then mark the handoff DELIVERED; an API response or Slack send alone does not prove Muse has read it.
4. Muse explicitly acknowledges on Issue #1 with the post ID and says whether it can act. Completion requires a committed result, immutable artifact/hash and verifiable evidence; acknowledgment is not completion.
5. A blocked write or inaccessible Slack read is a tooling failure. Do not silently wait, mark the work delivered, or ask Mike to relay routine tasks. Use the available authorized GitHub issue/file path, verify it, and report any unresolved blocker honestly.
6. Claude is a **manual external reviewer** operated by Mike, not a background agent. Muse prepares the standalone download and instructions; ChatGPT independently reviews existing evidence. Neither assistant should claim Claude has run without a user-returned artifact.
7. Preserve existing hard gates (purchases, deletions, real trades, production changes, and any other explicit governing research/test restrictions). Communication fixes do not expand permission for new data pulls, tests, or strategy changes.
8. On every research-watch check: read Issue #1 first, identify new tasks/ACKs, compare immutable artifacts, work a permitted independent task, and provide source-backed status. No duplicate requests without new evidence.

**Existing work order:** Issue #1 comment 6617593066 (Stage A audit and new-sample validation).  
**Independent receipt check:** Issue #1 comment 6617637071.  
**Priority handoff still requiring evidence delivery:** Muse's sanitized offline Stage-A derived-ledger and runner ZIP for Mike to manually upload to Claude. Required derived files: `results.json`, `ledger_7a.json`, `ledger_hbuy.json`, `ledger_7b.json`, `stage_run.py`, `RUN_SPEC_EXTRACTED.md`, `parity_report.json`, `derive_and_parity.py`, frozen engine/config, `SHA256SUMS`, offline README/test. Keep market-data and credentials out of the Claude ZIP. Deliver via an access-controlled download with SHA-256; state any missing evidence rather than inventing it.
