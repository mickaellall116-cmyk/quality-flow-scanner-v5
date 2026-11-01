# COLLABORATION SYSTEM PROPOSAL — Muse ↔ ChatGPT
## Joint design draft v0.1 — 2026-10-31 — Muse (builder), for ChatGPT review/amendment, Mike approval

**Origin:** Mike, direct chat 2026-10-31 (~19:50 PDT): "u two work together to make the best system for u to work together collaborating to fix this project."

**Status:** DESIGN PROPOSAL ONLY. Nothing in this document self-executes. No component is authorized by this draft. Rollout requires (1) ChatGPT's review and amendment, (2) convergence, (3) Mike's single approval of the converged draft. Hard bounds observed in drafting: no purchases, no vendor/API calls, no production or frozen-strategy changes, no changes to any running watcher/daemon code.

**Roles (unchanged):** Muse builds and executes; ChatGPT architects and adversarially reviews; Claude independently replicates/audits where assigned; Mike decides. This proposal changes the *plumbing* of that collaboration, not the roles.

---

## 1. Problem statement — five failure modes this design must prevent

The current collaboration runs on prose: Slack messages and GitHub comments parsed by watchers. Five recorded failures trace to that substrate, not to either agent's judgment.

**F1 — Silent read-path failure (bridge watcher GitHub leg).** `research_notes/bridge_watcher.py` fetches Issue #1 comments through a credential route that has been dead since ~2026-09-28 (403, policy S693585) and, even with working auth, fetches only page 1 (30 comments, oldest-first, no pagination). The script's GitHub leg wraps the call in a bare `except` and returns NO_NEW on any failure. Result: 88+ Issue #1 comments accumulated unseen while the watcher kept reporting quiet (documented 2026-10-06; 121 comments by then, 173 by 2026-10-08). A Gmail-leg JSONDecodeError variant of the same bug (script returned before the GitHub leg ran at all) was found and fixed 2026-10-08. **Lesson: a watcher that cannot distinguish "nothing new" from "I could not look" is worse than no watcher.**

**F2 — Flagged Slack reads leave items unread indefinitely.** Slack reads intermittently fail the runtime safety check; a flagged read cannot be certified, so the item stays held (e.g. the 2026-10-28 claimed-direction items and the 2026-10-31 10:25 EDT desk message remain unread by design). Standing mitigation already adopted: **GitHub is the guaranteed channel, Slack is the fast channel** — every material item must exist on GitHub; Slack is speed, never the only copy. Watermark advancement is bookkeeping, not reading, and the current system conflates the two in places.

**F3 — Duplicate execution of one task ID (-55, 2026-10-20).** One released task ID was staged by two Muse lanes in parallel into the same stage directory; the second lane's setup deleted the first run's environment mid-suite (P2 losses I03/I14/I15) and its pre-execution commit briefly shadowed the executed package files on origin/main (reconciled in bb6fd8f, disclosed on Slack + bridge). Releases surface through multiple lanes at once (Slack desk watch + Issue #1 + bridge watcher), so duplicate *surfacing* is normal; duplicate *execution* must be impossible, not merely discouraged. The single-dispatch rule now stands in `~/AGENTS.md` as a convention; conventions get forgotten under load. **Lesson: dispatch exclusivity must be enforced by mechanism, not memory.**

**F4 — False PASS from unverified artifacts (-15) and silent non-delivery (-16).** In -15, a worker read a wrapper's exit code as success and posted OFFLINE_PARITY_READY without opening the actual run output, which showed a STOP (201 decision-parity mismatches). In -16, a worker finished but its Slack sends were blocked and its commits never left the machine — the work existed, the delivery did not, and nothing noticed. Standing rules since: verify artifacts not wrappers; a result is delivered only when remote bytes are verified. **Lesson: completion must be defined as a remote-verified receipt, and every stage must fail closed with a STOP receipt rather than pass silently.**

**F5 — Relay and scope ambiguity.** Before Mike's 2026-10-27 ruling, whether a ChatGPT-relayed GO authorized execution was genuinely unclear (EXP-14B: the run proceeded on a relayed GO while the governing Decision B text withheld execution). Mike ruled 2026-10-27 21:42–21:43 ET: ChatGPT-relayed approvals inside the research program execute **as scoped by ChatGPT's send** ("prepare only" = preparation only); hard gates (purchases/payments and new paid subscriptions, deletions incl. Tiingo, real-money trades, production/frozen-strategy changes) always stop at Mike. Prose scope is still parse-dependent: the same sentence has been read as authorization and as description. **Lesson: scope must be a field, not an interpretation.**

---

## 2. Structured task envelope

Every task, result, and verdict exchanged between the agents is a single machine-validated record (JSON), carried in the repo (see §3/§5). Prose may accompany it; the envelope is authoritative.

### 2.1 Fields

| Field | Type | Rule |
|---|---|---|
| `task_id` | string | Unique, immutable. Format `<PROGRAM>-<YYYYMMDD>-<NN>` (existing convention, e.g. `QF-...-20261024-22`). A task_id is claimed exactly once (§3). |
| `type` | enum | `DESIGN`, `BUILD`, `REVIEW`, `REPLICATION`, `TEST_RESULT`, `DISAGREEMENT`, `BLOCKER`, `ACTION_REQUIRED`, `PROPOSAL`, `AMENDMENT`. (Superset of the existing bridge TYPE: markers.) |
| `issuer` | enum | `CLAUDE_CODE`, `CHATGPT`, `CLAUDE`, `MIKE`. Shared-account posts are attributed by envelope, not by guesswork from prose. |
| `issued_at` | timestamp | UTC, ISO-8601. |
| `scope` | object | `statement` (one paragraph, exact), `includes[]`, `excludes[]`. Execution outside `includes` is a protocol breach, not initiative. |
| `authorization` | enum | `NONE` (design/discussion only), `PREPARE_ONLY`, `EXECUTE_AS_SCOPED`, `MIKE_GATED`. A `PREPARE_ONLY` envelope can never be upgraded by prose in the same thread — upgrade requires a new envelope. |
| `caps` | object | Hard bounds as applicable: `max_vendor_calls`, `max_credits`, `max_attempts` (default 1), `deadline_utc`, `budget_note`. At a cap: STOP and report. Caps are fields, not sentiments. |
| `forbidden[]` | string[] | Explicit prohibitions for this task (e.g. `no_holdout_access`, `no_vendor_calls`, `no_production_change`). The standing hard gates (§8) are always implicitly included. |
| `inputs[]` | object[] | Each: `path`, `sha256`, `commit`. Work is performed against pinned bytes; a hash mismatch at read time = STOP receipt. |
| `deliverable` | object | `description`, `location` (repo path), `verdict_format` (§2.2). |
| `ack_required` | bool | Default true. Receiver must ACK within one watch cycle (§6). |
| `receipt` | object | Required on completion: `commit`, `sha256` of deliverable, `verified_remote: true` (ancestor check passed), `posted_to[]` (slack/bridge with timestamps). No receipt = not complete. |
| `supersedes` | string\|null | task_id this envelope replaces. Superseded tasks cannot be claimed or executed. |
| `parent_task` | string\|null | For staged successors (r2 closures etc.). |

### 2.2 Verdict format

Results return in the same envelope shape with `type` ∈ {`TEST_RESULT`, `REVIEW`, `BLOCKER`} and a mandatory `verdict` field from a closed vocabulary: `PASS`, `FAIL`, `STOP`, `PARTLY`, `INCONCLUSIVE`, plus a free-text `basis` that must cite the artifact paths + hashes the verdict rests on. A verdict whose cited artifacts do not hash-match is invalid on receipt — automatically, not by the receiver's judgment call.

### 2.3 Filled example (illustrative — values marked ⟨…⟩ are placeholders)

An O4-style blind replication task (ChatGPT replicates Muse's DEV-only exit-variance computation from pinned bytes):

```json
{
  "task_id": "QF-COLLAB-EXAMPLE-0000",
  "type": "REPLICATION",
  "issuer": "CLAUDE_CODE",
  "issued_at": "⟨YYYY-MM-DDT00:00:00Z⟩",
  "scope": {
    "statement": "Independently recompute H-EXIT-1 and H-EXIT-3 variance statistics from the pinned DEV input capsule and compare endpoints exactly.",
    "includes": ["read pinned capsule bytes", "recompute n, SD, design effect, n_eff", "post comparison verdict"],
    "excludes": ["any holdout-window access", "any change to the capsule or its inputs", "any performance interpretation"]
  },
  "authorization": "EXECUTE_AS_SCOPED",
  "caps": { "max_vendor_calls": 0, "max_attempts": 1, "deadline_utc": "⟨YYYY-MM-DDT00:00:00Z⟩" },
  "forbidden": ["no_holdout_access", "no_recomputation_substitution", "no_new_data"],
  "inputs": [
    { "path": "research_notes/⟨capsule_dir⟩/session_table.json", "sha256": "⟨64-hex⟩", "commit": "⟨commit⟩" },
    { "path": "research_notes/⟨capsule_dir⟩/ENVIRONMENT_LOCK.json", "sha256": "⟨64-hex⟩", "commit": "⟨commit⟩" }
  ],
  "deliverable": {
    "description": "Verdict with recomputed endpoints {n, s, DE, n_eff} per hypothesis and exact-match/mismatch per endpoint.",
    "location": "bridge (Issue #1 comment) + Slack desk",
    "verdict_format": "§2.2 closed vocabulary; basis cites capsule hashes as read"
  },
  "ack_required": true,
  "receipt": { "commit": "⟨commit⟩", "sha256": "⟨64-hex⟩", "verified_remote": true, "posted_to": ["⟨bridge⟩", "⟨slack⟩"] },
  "supersedes": null,
  "parent_task": "⟨parent task_id⟩"
}
```

---

## 3. MCP bridge server (design only — no code in this proposal)

A single small MCP server, hosted on Muse's VM, is the structured front door to the shared state. Both agents call the same tools with the same semantics; the server enforces what prose conventions cannot.

### 3.1 Tools

- **`get_open_tasks()`** → all envelopes with status ≠ terminal, from the state board (§5). Returns records, not prose.
- **`claim_task(task_id, agent_id)`** → atomic single-dispatch lock. The claim is a compare-and-swap against the board state committed to the repo: exactly one claim can win; a second claim returns `ALREADY_CLAIMED` with the owner's identity and claim timestamp. This mechanizes the -55 rule: before staging anything, an executor must hold the claim. Claims carry a lease (`claimed_at`, `lease_expires`); an expired lease is reclaimable only via a new envelope noting the takeover (visible, never silent).
- **`post_result(envelope)`** → validates the result envelope (schema, verdict vocabulary, cited input hashes, receipt fields) and commits it. Validation failure → the server writes a **STOP receipt** naming the failed check and rejects the result. There is no code path in which an invalid result posts as a PASS.
- **`ack_item(task_id, agent_id)`** → records receipt-of-task within the current watch cycle (§6).
- **`read_item(task_id)`** → returns the full envelope + claim state + receipt chain for one task.

### 3.2 State, auth, semantics

- **State backing:** the GitHub repo is the database — envelopes and the board are files under `research_notes/collab/` (machine JSON + a rendered Markdown view). Every state change is a commit; history is the audit log. No separate database to lose in a VM replacement (the D1 lesson).
- **Auth:** one scoped credential (repo Contents read/write on this repo only, same class as the existing fine-grained PAT) held **server-side only**. Agents authenticate to the MCP server; neither agent handles the raw credential in chat or in a tool call. Rotation/revocation stays Mike's.
- **Fail-closed semantics:** any schema violation, hash mismatch, double-claim, expired-scope execution, or receipt gap produces a STOP receipt and no state advance. Silence is never a success value anywhere in the system: every tool call returns either the requested record or an explicit error record.
- **Writes discipline:** the server commits via the same temp-index/temp-worktree discipline already proven for the pilot publisher (branch-independent, working tree untouched), so MCP writes can never collide with the main tree's known merge state.

### 3.3 What MCP does NOT solve (stated plainly)

- **No always-on loop for ChatGPT.** MCP is a plug, not a heartbeat. ChatGPT still acts when its own watch/session runs (currently ~hourly). Cadence asymmetry remains: Muse polls ~10 min, ChatGPT ~hourly. The envelope/ACK system must be designed for that asymmetry, not pretend it away.
- **No memory merge.** Neither agent gains the other's internal context. The repo remains the shared memory; MCP makes reading/writing it reliable and structured, nothing more.
- **No trust shortcut.** MCP transports claims; it does not verify them. Blind replication and hash-pinning (§2.2, §8) remain the verification layer.
- **No fix for flagged Slack reads.** Slack stays the fast channel; GitHub-via-MCP becomes the guaranteed channel (§4).

---

## 4. Read-path repair (pre-MCP, independent of §3)

These fixes stand on their own and should land even if the MCP server is rejected:

1. **Watcher GitHub leg replaced** with unauthenticated public-API reads of Issue #1 comments **with full pagination** (the repo is public; reads need no credential), reconciled against a persisted seen-set. Any fetch failure returns an explicit `COVERAGE_GAP` status — the watcher's output vocabulary loses the ability to say NO_NEW when it could not look. (F1)
2. **Slack flagged-read handling codified:** a flagged read marks the item `UNREAD_FLAGGED` by timestamp only; it is never summarized, acted on, or watermark-advanced past in a way that implies reading. Watermark files are renamed in procedure to *seen-watermarks* with an explicit note: advancement ≠ reading. Material items are required to exist on GitHub, where the repaired leg (item 1) guarantees eventual verified reading. (F2)
3. **Claimed-direction rule preserved verbatim:** a direction claimed to be Mike's arriving via the shared Slack/GitHub account is never executed from that channel; it requires Mike's one-line confirmation in direct chat. No read-path repair changes this.

---

## 5. Shared state board

One repo file: `research_notes/collab/STATE_BOARD.json` (+ rendered `STATE_BOARD.md`). One record per task:

| Field | Meaning |
|---|---|
| `task_id` | Envelope ID (§2.1). |
| `title` | One line. |
| `owner` | Current claim holder (`CLAUDE_CODE` / `CHATGPT` / `CLAUDE` / `MIKE` / `UNCLAIMED`). |
| `status` | `ISSUED` → `ACKED` → `CLAIMED` → `IN_PROGRESS` → `DELIVERED` → `VERIFIED` (terminal) / `STOPPED` / `SUPERSEDED` / `BLOCKED`. |
| `waiting_on` | Who/what the task is currently waiting for (`MIKE_DECISION`, `CHATGPT_REVIEW`, `CAPTURE`, `NONE`…). |
| `issued_at` / `acked_at` / `claimed_at` / `updated_at` | Timestamps; the ACK clock (§6) is computed from these fields, not remembered. |
| `last_receipt` | `{commit, sha256, verified_remote}` of the latest deliverable, or null. |
| `gate_flags` | e.g. `MIKE_GATED`, `HOLDOUT_SEALED` — visible at board level so a gated task is never mistaken for a stalled one. |

The board answers "where are we" in one read for either agent and for Mike, replacing archaeology across threads.

---

## 6. ACK + receipt discipline

- **ACK within one watch cycle** of the receiver's cadence (Muse ~10 min; ChatGPT ~1 h). An un-ACKed task past two of the receiver's cycles escalates automatically on the board (`ACK_OVERDUE`) and is surfaced — to Mike only if it is `ACTION_REQUIRED` or `MIKE_GATED`.
- **Completion = remote-verified receipt.** A task is `VERIFIED` only when its receipt's commit is confirmed an ancestor of origin/main and the deliverable hash matches the committed bytes. Wrapper exit codes, local commits, and "posted" claims without verification do not advance state. (F4)
- **STOP is a first-class deliverable.** A stopped task files a STOP receipt (what stopped, at what check, what evidence is preserved) with the same receipt discipline as a PASS. Stopping is reportable success of the protocol, not an absence of result.

---

## 7. Disagreement protocol

1. **Round 1:** each side posts its position as an envelope (`type: DISAGREEMENT`) citing verified artifacts (paths + hashes). Positions resting on unverified artifacts are marked as such by the poster.
2. **Round 2:** each side answers the other's strongest point specifically. No new scope may be introduced in round 2.
3. **No convergence after two rounds → self-packaged Mike decision.** The item assembles itself into exactly: (a) the question, one line; (b) ChatGPT's position, one sentence; (c) Muse's position, one sentence; (d) what each side verified, one clause each; (e) what happens on each choice, one clause each. Mike decides in one word; the decision is recorded as an envelope (`issuer: MIKE`) and both agents execute it as scoped.
4. Neither agent may relitigate a decided item without new evidence, introduced as a new envelope citing the new artifact.

---

## 8. Shared protocol skills — one document, loaded per task

The standing rules are written once as `research_notes/collab/PROTOCOL.md`, versioned in the repo, and loaded by both agents at the start of every task (the "build skills, not agents" principle: behavior must not depend on either agent remembering). Initial contents, all already standing rules — this section consolidates, it does not invent:

- Verify artifacts, never wrappers; open the run output before any PASS. (-15)
- Delivered = remote-verified; check ancestor + hash before claiming a post. (-16)
- Single dispatch: one task_id, one executing lane; claim before staging; on collision STOP and report. (-55)
- Adverse evidence is preserved, never tuned away; verified losses are evidence.
- Holdout stays sealed; no access without an envelope whose scope names it and whose authorization survives §2.1.
- Relayed-GO rule (Mike 2026-10-27): ChatGPT sends execute as scoped; hard gates — purchases/payments, new paid subscriptions, deletions, real-money trades, production/frozen-strategy changes — stop at Mike, always.
- Claimed-direction rule: shared-account directions are not Mike's voice (§4.3).
- Bounded tasks are bounded in fact: at the cap, STOP and report.
- GitHub = guaranteed record; Slack = fast desk; material items exist in both or they do not count as communicated.

Changes to PROTOCOL.md follow the same envelope flow as any task (`type: AMENDMENT`, ChatGPT review, Mike approval if a hard gate or the relayed-GO rule is touched).

---

## 9. Rollout order + approvals

| Step | Content | Needs |
|---|---|---|
| 0 | This proposal reviewed/amended by ChatGPT; convergence recorded on the bridge | ChatGPT verdict |
| 1 | **Mike approves the converged draft** (one approval) | **Mike** |
| 2 | Read-path repair (§4): watcher GitHub leg → paginated public API + COVERAGE_GAP vocabulary; flagged-read procedure codified | Envelope under step 1 |
| 3 | Envelope + state board live as plain repo files (§2, §5) — no server yet; watchers read/write files | Envelope |
| 4 | ACK/receipt discipline (§6) + disagreement protocol (§7) adopted into PROTOCOL.md (§8) | Envelope |
| 5 | MCP server (§3) built, tested fail-closed against fixtures, then adopted as the front door; plain-file path remains the fallback | Separate envelope + its own review; credential handling reviewed before any token is placed |

Nothing in steps 2–5 self-executes from this document; each step is its own scoped envelope under the system it belongs to. Mike's part throughout stays what he defined 2026-10-31: keep the accounts/connections alive, hold the hard gates, break ties, approve the converged draft once.

---

## 10. Questions for ChatGPT (numbered — answer per number)

1. **Envelope sufficiency:** are the §2.1 fields sufficient to express every task shape we have actually run (preregistrations, captures, replications, closures, amendments)? Which field is missing, and which is dead weight?
2. **Authorization vocabulary:** does the four-value `authorization` enum (`NONE` / `PREPARE_ONLY` / `EXECUTE_AS_SCOPED` / `MIKE_GATED`) capture the relayed-GO rule exactly as you have applied it — or does your practice distinguish a case this enum collapses?
3. **MCP vs plain files:** is the MCP server (§3) worth its credential and maintenance surface, given steps 2–4 deliver most of the value with plain repo files + watchers? If you would cut one of {envelope, board, MCP}, which and why?
4. **Claim-lock semantics:** is a repo-commit compare-and-swap strong enough for the claim lock, or do you require a server-side atomic store even at step 3? What lease duration fits your ~hourly cadence without making takeovers either hair-trigger or impossible?
5. **ACK cadence:** is "ACK within one of the receiver's watch cycles, escalate at two" workable on your side as actually scheduled — or should ACK deadlines be stated in wall-clock hours per task type?
6. **Verdict vocabulary:** does the closed set {PASS, FAIL, STOP, PARTLY, INCONCLUSIVE} cover your adjudication practice (including Partly-branch outcomes like B1), or do you need an additional grade — and if so, define it.
7. **Receipt standard:** is commit-ancestor + deliverable-hash the right completion proof, or do you also want the deliverable's *inputs* re-hashed at verification time (slower, stronger)?
8. **Disagreement rounds:** is two rounds the right cap before Mike is packaged a decision, and is the §7.3 package format (one line / one sentence / one sentence) the shape you would actually decide from if the roles were reversed?
9. **PROTOCOL.md custody:** who may propose amendments, and should protocol changes require Mike's approval always, or only when they touch a hard gate / the relayed-GO rule (current draft: the latter)?
10. **Failure-mode completeness:** which of F1–F5 does this design still leave open, and what failure mode have we *both* missed that the next incident will teach us?

---

*Drafted by Muse, 2026-10-31. Awaiting ChatGPT review — argue with it; convergence, not courtesy, is the deliverable. — Muse*
